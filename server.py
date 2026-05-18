import asyncio
import json
import logging
import os
import pathlib
import secrets
import sys
import time
from collections import deque

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from auth import (
    AuthConfig,
    GoogleVerifier,
    SessionData,
    build_auth_router,
    build_verify_session,
    parse_allowed_emails,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("voxgate")

app = FastAPI()

# VoxGate is a pure forwarding proxy: every authenticated /chat request is
# enriched with the verified user e-mail and POSTed to TARGET_URL. The backend
# at TARGET_URL owns all LLM logic, system prompts, history and routing. See
# docs/integration.md for the request/response schema.
TARGET_URL = os.environ.get("TARGET_URL", "").strip()
TARGET_TOKEN = os.environ.get("TARGET_TOKEN", "")
INSTANCE_NAME = os.environ.get("INSTANCE_NAME", "VoxGate")
INSTANCE_DISPLAY_NAME = os.environ.get("INSTANCE_DISPLAY_NAME", "").strip() or INSTANCE_NAME
INSTANCE_COLOR = os.environ.get("INSTANCE_COLOR", "#c8ff00")
SPEECH_LANG = os.environ.get("SPEECH_LANG", "de-CH")
SPEECH_LANGS = [
    lang.strip()
    for lang in os.environ.get(
        "SPEECH_LANGS", "de-CH,fr-CH,it-CH,en-US,es-ES"
    ).split(",")
    if lang.strip()
]
if SPEECH_LANG not in SPEECH_LANGS:
    SPEECH_LANGS.insert(0, SPEECH_LANG)
MAX_PROMPT_LENGTH = int(os.environ.get("MAX_PROMPT_LENGTH", "4000"))
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "")
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "120"))
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "30"))
AUTH_LOGIN_RATE_LIMIT_PER_MINUTE = int(
    os.environ.get("AUTH_LOGIN_RATE_LIMIT_PER_MINUTE", "10")
)
# Per-attachment cap on the base64 string. 4 MiB ≈ 3 MiB of binary payload —
# generous for a phone photo downscaled to 1600px on the longest side
# (~500 KiB JPEG at quality 0.85). Operators can raise it via env if needed.
MAX_ATTACHMENT_BASE64_BYTES = int(
    os.environ.get("MAX_ATTACHMENT_BASE64_BYTES", str(4 * 1024 * 1024))
)
MAX_ATTACHMENTS_PER_REQUEST = int(
    os.environ.get("MAX_ATTACHMENTS_PER_REQUEST", "4")
)
TRUST_PROXY_HEADERS = os.environ.get("TRUST_PROXY_HEADERS", "0") == "1"

# Streaming sub-contract (see docs/integration.md). Default on — the PWA
# falls back to /chat for backends that reply with plain JSON, so flipping
# this off is only useful for operators who explicitly want to disable
# the new endpoint entirely.
STREAMING_ENABLED = os.environ.get("STREAMING_ENABLED", "1") == "1"
# Optional cancel-hook: if set, /chat/cancel additionally fires
# DELETE <BACKEND_CANCEL_URL> after dropping the outbound stream.
# The literal token {session_id} is substituted. Most backends only need
# the TCP close, so this is opt-in.
BACKEND_CANCEL_URL = os.environ.get("BACKEND_CANCEL_URL", "").strip()
# Per-byte idle timeout for the streaming proxy. Total /chat/stream
# duration is unbounded (LLM answers can take minutes); we time out only
# when the backend goes silent for this many seconds.
STREAM_IDLE_TIMEOUT = int(os.environ.get("STREAM_IDLE_TIMEOUT", "60"))

# Auth config
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
ALLOWED_EMAILS_RAW = os.environ.get("ALLOWED_EMAILS", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "").strip()
SESSION_COOKIE_TTL_SECONDS = int(
    os.environ.get("SESSION_COOKIE_TTL_SECONDS", str(7 * 24 * 3600))
)
# Set COOKIE_SECURE=1 in production (HTTPS). Defaults to 0 so local http works.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"

DEBUG_ENABLED = os.environ.get("DEBUG_ENABLED", "0") == "1"
DEBUG_TOKEN = os.environ.get("DEBUG_TOKEN", "").strip()
DEBUG_MAX_BODY_BYTES = 8 * 1024
DEBUG_RATE_LIMIT_PER_SEC = 20
_debug_buckets: dict = {}

if not SESSION_SECRET:
    SESSION_SECRET = secrets.token_hex(32)
    print(
        "\n" + "=" * 60 + "\n"
        "No SESSION_SECRET set. Generated for this run.\n"
        "Set SESSION_SECRET in your .env to keep sessions valid across restarts.\n"
        + "=" * 60,
        file=sys.stderr,
    )

ALLOWED_EMAILS = parse_allowed_emails(ALLOWED_EMAILS_RAW)
PROVIDERS = {}
if GOOGLE_CLIENT_ID:
    PROVIDERS["google"] = GoogleVerifier(client_id=GOOGLE_CLIENT_ID)

if not PROVIDERS:
    print(
        "WARNING: No auth provider configured. Set GOOGLE_CLIENT_ID to enable login. "
        "/chat will reject every request.",
        file=sys.stderr,
    )
if not ALLOWED_EMAILS:
    print(
        "WARNING: ALLOWED_EMAILS is empty. No user can log in. "
        "Set ALLOWED_EMAILS in your .env (comma-separated, optional :provider suffix).",
        file=sys.stderr,
    )

if not TARGET_URL:
    print(
        "WARNING: TARGET_URL is not set. /chat will return 503 for every request. "
        "Set TARGET_URL in your .env to point at the backend that handles chat.",
        file=sys.stderr,
    )

_rate_buckets: dict[str, deque] = {}
_auth_login_buckets: dict[str, deque] = {}
# session_id → asyncio.Task of the in-flight /chat/stream forward. Used
# by /chat/cancel to abort the outbound httpx connection. Single-worker
# Uvicorn assumed (see Dockerfile); multi-worker deployments would need
# external state (Redis/etc.) — see docs/setup.md.
_active_streams: dict[str, "asyncio.Task[None]"] = {}


def _client_ip(request: Request) -> str:
    if TRUST_PROXY_HEADERS:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _login_rate_limit(request: Request) -> None:
    ip = _client_ip(request)
    now = time.time()
    bucket = _auth_login_buckets.setdefault(ip, deque())
    while bucket and bucket[0] < now - 60:
        bucket.popleft()
    if len(bucket) >= AUTH_LOGIN_RATE_LIMIT_PER_MINUTE:
        logger.warning("[%s] auth_login_rate_limit ip=%s", INSTANCE_NAME, ip)
        raise HTTPException(status_code=429, detail="Too many login attempts")
    bucket.append(now)
    if len(_auth_login_buckets) > 10000:
        for stale_ip in [k for k, v in _auth_login_buckets.items() if not v]:
            _auth_login_buckets.pop(stale_ip, None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(self), camera=(), geolocation=()"
    # PWA cache policy: tell browsers to revalidate on every load via ETag.
    # Without this, app.js / index.html can stick in the cache after a deploy
    # and family devices keep running the old code. ETag-based 304s keep the
    # bandwidth cost negligible.
    if request.url.path != "/sw.js":
        response.headers.setdefault("Cache-Control", "no-cache")
    # CSP notes:
    # - script-src is strict ('self' + GIS client only). No inline scripts.
    # - style-src includes 'unsafe-inline' because Google Identity Services
    #   injects inline styles into the rendered button. Tightening this would
    #   require a per-request nonce, which is overkill for a no-build PWA. The
    #   residual risk (CSS-only XSS) is very narrow given the rest of the CSP.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://accounts.google.com/gsi/client; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com "
        "https://accounts.google.com/gsi/style; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://*.googleusercontent.com; "
        "connect-src 'self' https://accounts.google.com/gsi/; "
        "frame-src https://accounts.google.com/gsi/; "
        "manifest-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'"
    )
    return response


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path in (
        "/chat", "/chat/stream", "/chat/cancel", "/selftest",
    ) and request.method == "POST":
        ip = _client_ip(request)
        now = time.time()
        bucket = _rate_buckets.setdefault(ip, deque())
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_PER_MINUTE:
            logger.warning("rate_limit_exceeded ip=%s path=%s", ip, request.url.path)
            return JSONResponse(
                status_code=429, content={"detail": "Rate limit exceeded"}
            )
        bucket.append(now)
        if len(_rate_buckets) > 10000:
            for stale_ip in [k for k, v in _rate_buckets.items() if not v]:
                _rate_buckets.pop(stale_ip, None)
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN] if ALLOWED_ORIGIN else [],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)


# Origins permitted to initiate /auth/login + /auth/logout. Without a value,
# the AuthConfig skips the cross-origin check (dev convenience). Behind a
# reverse proxy this should always be configured via ALLOWED_ORIGIN.
_expected_origins = frozenset({ALLOWED_ORIGIN}) if ALLOWED_ORIGIN else frozenset()

_auth_config = AuthConfig(
    providers=PROVIDERS,
    allowed_emails=ALLOWED_EMAILS,
    session_secret=SESSION_SECRET,
    session_ttl_seconds=SESSION_COOKIE_TTL_SECONDS,
    cookies_secure=COOKIE_SECURE,
    instance_name=INSTANCE_NAME,
    expected_origins=_expected_origins,
    rate_limit_check=_login_rate_limit,
)
app.include_router(build_auth_router(_auth_config))
verify_session = build_verify_session(_auth_config)


_ALLOWED_ATTACHMENT_MIMES = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
})


class Attachment(BaseModel):
    """One inline attachment forwarded as base64 inside the chat payload.

    Initial scope: images only (one-way, client → backend). The `kind`
    field future-proofs for audio/file/etc.; backends may ignore unknown
    kinds.
    """
    kind: str = Field("image", max_length=16)
    mime: str = Field(..., max_length=64)
    name: str = Field("", max_length=255)
    data: str = Field(..., min_length=4)

    @field_validator("mime")
    @classmethod
    def _mime_allowed(cls, v: str) -> str:
        if v not in _ALLOWED_ATTACHMENT_MIMES:
            allowed = sorted(_ALLOWED_ATTACHMENT_MIMES)
            raise ValueError(f"mime {v!r} not allowed; expected one of {allowed}")
        return v

    @field_validator("data")
    @classmethod
    def _data_within_limit(cls, v: str) -> str:
        if len(v) > MAX_ATTACHMENT_BASE64_BYTES:
            raise ValueError(
                f"attachment base64 length {len(v)} exceeds limit {MAX_ATTACHMENT_BASE64_BYTES}"
            )
        return v


class ChatRequest(BaseModel):
    # text becomes optional when an attachment is present (e.g. just a
    # photo). The endpoint enforces "at least one of text/attachments".
    text: str = Field("", max_length=MAX_PROMPT_LENGTH)
    session_id: str = Field(..., pattern=r"^[A-Za-z0-9_-]{8,128}$")
    lang: str = Field("", max_length=16)
    attachments: list[Attachment] = Field(default_factory=list)

    @field_validator("attachments")
    @classmethod
    def _attachments_count(cls, v: list) -> list:
        if len(v) > MAX_ATTACHMENTS_PER_REQUEST:
            raise ValueError(
                f"too many attachments: {len(v)} > {MAX_ATTACHMENTS_PER_REQUEST}"
            )
        return v


@app.post("/debug-log")
async def debug_log(request: Request):
    if not DEBUG_ENABLED or not DEBUG_TOKEN:
        raise HTTPException(status_code=404)
    presented = request.headers.get("x-debug-token", "")
    if not presented or not secrets.compare_digest(presented, DEBUG_TOKEN):
        raise HTTPException(status_code=401)
    body = await request.body()
    if len(body) > DEBUG_MAX_BODY_BYTES:
        raise HTTPException(status_code=413)
    ip = _client_ip(request)
    now = time.time()
    bucket = _debug_buckets.setdefault(ip, deque())
    while bucket and bucket[0] < now - 1:
        bucket.popleft()
    if len(bucket) >= DEBUG_RATE_LIMIT_PER_SEC:
        raise HTTPException(status_code=429)
    bucket.append(now)
    if len(_debug_buckets) > 1000:
        for stale_ip in [k for k, v in _debug_buckets.items() if not v]:
            _debug_buckets.pop(stale_ip, None)
    print(f"DEBUG ip={ip} {body.decode('utf-8', errors='replace')}", file=sys.stderr, flush=True)
    return JSONResponse(status_code=204, content=None)


@app.get("/integration")
async def integration():
    """Serve docs/integration.md live so integrators have one URL that
    lists every endpoint and pins the backend contract for TARGET_URL.
    Public, no auth — none of this is secret. The Dockerfile copies the
    file to /app/integration.md at build time so doc changes ship with
    the image; in a checkout `make run` falls back to docs/integration.md.
    """
    candidates = [
        pathlib.Path(__file__).resolve().parent / "integration.md",
        pathlib.Path(__file__).resolve().parent / "docs" / "integration.md",
    ]
    for path in candidates:
        if path.is_file():
            return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown")
    raise HTTPException(status_code=404, detail="Integration document not bundled")


@app.get("/config")
async def get_config():
    # GOOGLE_CLIENT_ID is intentionally public: Google Identity Services puts it
    # in the page source anyway. Reviewers, do not flag this as a leak.
    return {
        "name": INSTANCE_DISPLAY_NAME,
        "color": INSTANCE_COLOR,
        "lang": SPEECH_LANG,
        "langs": SPEECH_LANGS,
        "maxLength": MAX_PROMPT_LENGTH,
        "googleClientId": GOOGLE_CLIENT_ID,
        "providers": sorted(PROVIDERS.keys()),
        "streaming": STREAMING_ENABLED,
    }


class CancelRequest(BaseModel):
    session_id: str = Field(..., pattern=r"^[A-Za-z0-9_-]{8,128}$")


@app.post("/chat")
async def chat(
    req: ChatRequest,
    request: Request,
    session: SessionData = Depends(verify_session),
):
    """Forward an authenticated chat turn to the configured backend.

    Contract — see docs/integration.md for the full version.
        Outbound (VoxGate → TARGET_URL):
            { "user": str, "user_email": str, "session_id": str,
              "metadata": { "lang": str, "instance": str } }
        Inbound (TARGET_URL → VoxGate):
            { "response": str }   — strict; anything else yields 502.
    """
    if not TARGET_URL:
        raise HTTPException(status_code=503, detail="No backend configured")

    if not req.text and not req.attachments:
        # Caught by Pydantic only collectively, not per-field. A bare empty
        # request (no text, no images) makes no sense — reject loudly.
        raise HTTPException(
            status_code=422, detail="Either text or at least one attachment is required",
        )

    ip = _client_ip(request)
    sid_short = req.session_id[:8]
    logger.info(
        "[%s] chat ip=%s user=%s session=%s text_len=%d attachments=%d",
        INSTANCE_NAME, ip, session.email, sid_short, len(req.text), len(req.attachments),
    )

    payload = {
        "user": req.text,
        "user_email": session.email,
        "session_id": req.session_id,
        "metadata": {
            "lang": req.lang or SPEECH_LANG,
            "instance": INSTANCE_NAME,
        },
    }
    if req.attachments:
        payload["attachments"] = [a.model_dump() for a in req.attachments]
    headers = {"Content-Type": "application/json"}
    if TARGET_TOKEN:
        headers["Authorization"] = f"Bearer {TARGET_TOKEN}"

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        # Bracket the backend call with explicit perf_counter timestamps
        # so the access log reveals how much of the /chat latency is
        # spent waiting on TARGET_URL vs. on VoxGate itself. ms is enough
        # resolution for human-scale debugging.
        t0 = time.perf_counter()
        try:
            res = await client.post(TARGET_URL, json=payload, headers=headers)
        except httpx.RequestError:
            logger.warning(
                "backend_unreachable ip=%s after_ms=%d",
                ip, int((time.perf_counter() - t0) * 1000),
            )
            raise HTTPException(status_code=502, detail="Backend unreachable")
        backend_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "[%s] backend_roundtrip session=%s status=%d ms=%d",
            INSTANCE_NAME, sid_short, res.status_code, backend_ms,
        )

    if res.status_code >= 400:
        logger.warning("backend_error ip=%s status=%d", ip, res.status_code)
        raise HTTPException(status_code=502, detail="Backend returned an error")

    try:
        data = res.json()
    except ValueError:
        logger.warning("backend_non_json ip=%s", ip)
        raise HTTPException(status_code=502, detail="Backend response was not JSON")

    if not isinstance(data, dict) or not isinstance(data.get("response"), str):
        # Strict contract: backends must return {"response": "<text>"}. Anything
        # else is treated as a contract violation, not silently passed through.
        shape = list(data) if isinstance(data, dict) else type(data).__name__
        logger.warning("backend_bad_shape ip=%s shape=%s", ip, shape)
        raise HTTPException(status_code=502, detail="Backend response did not match contract")

    out: dict = {"response": data["response"]}
    # Optional follow-up-hint fields (additive contract extension). Pass
    # through only when shape-correct; ignore everything else silently —
    # backends are free to attach diagnostic keys that the PWA shouldn't see.
    if isinstance(data.get("awaiting_user_input"), bool):
        out["awaiting_user_input"] = data["awaiting_user_input"]
    if isinstance(data.get("suggestion"), str):
        out["suggestion"] = data["suggestion"]
    return out


def _sse_event(event: str, data: dict) -> bytes:
    """Encode a single SSE frame. Keep payload on one line — multi-line
    `data:` is valid SSE but the PWA parser expects one JSON object per
    event for simplicity."""
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


async def _stream_from_backend(
    payload: dict, headers: dict, session_id: str, ip: str,
):
    """Async generator yielding SSE bytes for /chat/stream.

    Two backend modes:
      1) text/event-stream — bytes are forwarded line-buffered, then a
         terminal `final` event is synthesised if the backend forgot one
         (defensive; spec says backends should send it).
      2) application/json — legacy `{"response": ...}` is adapted to a
         single chunk + final event so the PWA codepath stays uniform.
    """
    sid_short = session_id[:8]
    delta_count = 0
    sent_final = False
    accumulated = ""
    t0 = time.perf_counter()

    timeout = httpx.Timeout(connect=10.0, read=STREAM_IDLE_TIMEOUT, write=10.0, pool=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", TARGET_URL, json=payload, headers=headers) as res:
                if res.status_code >= 400:
                    logger.warning(
                        "stream_backend_error ip=%s session=%s status=%d",
                        ip, sid_short, res.status_code,
                    )
                    yield _sse_event("error", {
                        "code": "backend_error",
                        "message": f"Backend returned HTTP {res.status_code}",
                    })
                    return

                ctype = res.headers.get("content-type", "").lower()

                if ctype.startswith("text/event-stream"):
                    # Pass-through SSE. We re-frame line-buffered so the
                    # PWA sees boundary-aligned events even if the backend
                    # writes mid-line, and parse final/chunk to know when
                    # to terminate.
                    buffer = b""
                    async for chunk in res.aiter_bytes():
                        buffer += chunk
                        while b"\n\n" in buffer:
                            frame, _, buffer = buffer.partition(b"\n\n")
                            if not frame.strip():
                                continue
                            # Inspect the event name to count deltas /
                            # detect the terminal final without parsing
                            # the JSON payload defensively.
                            evt_name = ""
                            for line in frame.split(b"\n"):
                                if line.startswith(b"event:"):
                                    evt_name = line[6:].strip().decode("ascii", "replace")
                                    break
                            if evt_name == "chunk":
                                delta_count += 1
                            elif evt_name == "final":
                                sent_final = True
                            yield frame + b"\n\n"
                            if sent_final:
                                return
                    # Connection ended without a `final`. Emit one so the
                    # PWA reliably transitions out of "streaming" state.
                    if not sent_final:
                        logger.warning(
                            "stream_no_final ip=%s session=%s deltas=%d",
                            ip, sid_short, delta_count,
                        )
                        yield _sse_event("error", {
                            "code": "stream_truncated",
                            "message": "Backend closed the stream without a final event",
                        })
                    return

                # Legacy JSON backend — read the full body and adapt.
                body = await res.aread()
                try:
                    data = json.loads(body.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    logger.warning("stream_backend_non_json ip=%s session=%s", ip, sid_short)
                    yield _sse_event("error", {
                        "code": "backend_non_json",
                        "message": "Backend response was not JSON",
                    })
                    return
                if not isinstance(data, dict) or not isinstance(data.get("response"), str):
                    shape = list(data) if isinstance(data, dict) else type(data).__name__
                    logger.warning(
                        "stream_backend_bad_shape ip=%s session=%s shape=%s",
                        ip, sid_short, shape,
                    )
                    yield _sse_event("error", {
                        "code": "backend_bad_shape",
                        "message": "Backend response did not match contract",
                    })
                    return
                text = data["response"]
                accumulated = text
                yield _sse_event("chunk", {"delta": text})
                final_payload: dict = {"response": text}
                if isinstance(data.get("awaiting_user_input"), bool):
                    final_payload["awaiting_user_input"] = data["awaiting_user_input"]
                if isinstance(data.get("suggestion"), str):
                    final_payload["suggestion"] = data["suggestion"]
                yield _sse_event("final", final_payload)
                sent_final = True
    except asyncio.CancelledError:
        logger.info(
            "[%s] stream_cancelled session=%s deltas=%d ms=%d",
            INSTANCE_NAME, sid_short, delta_count,
            int((time.perf_counter() - t0) * 1000),
        )
        # Best-effort terminal frame — the client may have already gone
        # away (that's typically why we got cancelled), but if it hasn't,
        # this lets the PWA finalise its state machine.
        try:
            yield _sse_event("error", {"code": "cancelled", "message": "Cancelled by user"})
        except Exception:
            pass
        raise
    except httpx.RequestError as exc:
        logger.warning(
            "stream_backend_unreachable ip=%s session=%s err=%s",
            ip, sid_short, type(exc).__name__,
        )
        yield _sse_event("error", {
            "code": "backend_unreachable",
            "message": "Backend unreachable",
        })
    finally:
        elapsed = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "[%s] stream_done session=%s deltas=%d final=%s ms=%d",
            INSTANCE_NAME, sid_short, delta_count, sent_final, elapsed,
        )
        _active_streams.pop(session_id, None)
        # Avoid a "unused" warning when accumulated stays empty in the SSE path.
        _ = accumulated


@app.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    request: Request,
    session: SessionData = Depends(verify_session),
):
    """Streaming variant of /chat. Same auth, same request body, but the
    response is `text/event-stream` (see docs/integration.md).

    Backend negotiation: VoxGate adds `Accept: text/event-stream` to the
    outbound POST. Backends that reply with that content-type are proxied
    through verbatim (line-buffered); backends that still reply with the
    legacy `{"response": "..."}` JSON are adapted to a single chunk+final
    SSE event so the PWA codepath stays uniform.
    """
    if not STREAMING_ENABLED:
        raise HTTPException(status_code=404, detail="Streaming disabled on this instance")
    if not TARGET_URL:
        raise HTTPException(status_code=503, detail="No backend configured")
    if not req.text and not req.attachments:
        raise HTTPException(
            status_code=422, detail="Either text or at least one attachment is required",
        )

    ip = _client_ip(request)
    sid_short = req.session_id[:8]
    logger.info(
        "[%s] chat_stream ip=%s user=%s session=%s text_len=%d attachments=%d",
        INSTANCE_NAME, ip, session.email, sid_short, len(req.text), len(req.attachments),
    )

    payload = {
        "user": req.text,
        "user_email": session.email,
        "session_id": req.session_id,
        "metadata": {"lang": req.lang or SPEECH_LANG, "instance": INSTANCE_NAME},
    }
    if req.attachments:
        payload["attachments"] = [a.model_dump() for a in req.attachments]
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    if TARGET_TOKEN:
        headers["Authorization"] = f"Bearer {TARGET_TOKEN}"

    # If the same session already has an in-flight stream, cancel it
    # before starting the new one. This mirrors the PWA's "auto-cancel
    # on new prompt" UX and keeps the registry's invariant (one stream
    # per session at most).
    prev = _active_streams.pop(req.session_id, None)
    if prev and not prev.done():
        prev.cancel()

    # Producer task owns the outbound httpx stream and is the cancel
    # target. It pushes frames into a queue; the StreamingResponse body
    # iterator drains the queue. This indirection is necessary because
    # the request handler returns *before* Starlette starts iterating
    # the response body — so we cannot track "the streaming task" via
    # asyncio.current_task() here.
    queue: asyncio.Queue = asyncio.Queue()
    _SENTINEL = object()

    async def _producer():
        try:
            async for frame in _stream_from_backend(payload, headers, req.session_id, ip):
                await queue.put(frame)
        except asyncio.CancelledError:
            try:
                queue.put_nowait(_sse_event("error", {
                    "code": "cancelled", "message": "Cancelled by user",
                }))
            except asyncio.QueueFull:
                pass
            raise
        finally:
            try:
                queue.put_nowait(_SENTINEL)
            except asyncio.QueueFull:
                pass

    producer_task = asyncio.create_task(_producer())
    _active_streams[req.session_id] = producer_task

    async def _drain():
        try:
            while True:
                frame = await queue.get()
                if frame is _SENTINEL:
                    return
                yield frame
        finally:
            # Client disconnect lands here. Cancel the producer so the
            # outbound httpx stream is torn down and the registry slot
            # is freed for the next turn.
            if not producer_task.done():
                producer_task.cancel()
            _active_streams.pop(req.session_id, None)

    return StreamingResponse(
        _drain(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # disable nginx/proxy buffering
        },
    )


@app.post("/chat/cancel")
async def chat_cancel(
    req: CancelRequest,
    request: Request,
    session: SessionData = Depends(verify_session),
):
    """Cancel an in-flight /chat/stream for the given session.

    Primary mechanism: cancel the asyncio task carrying the outbound
    httpx stream — the backend then sees a clean TCP close. Optional
    secondary: if `BACKEND_CANCEL_URL` is configured, fire a fire-and-
    forget `DELETE` against it so backends with explicit cancel routes
    can clean up. Idempotent: cancelling an unknown session returns
    `{"cancelled": false}` with HTTP 200.
    """
    ip = _client_ip(request)
    sid_short = req.session_id[:8]
    task = _active_streams.get(req.session_id)
    cancelled = False
    if task is not None and not task.done():
        task.cancel()
        cancelled = True
    _active_streams.pop(req.session_id, None)

    if cancelled and BACKEND_CANCEL_URL:
        url = BACKEND_CANCEL_URL.replace("{session_id}", req.session_id)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                hdrs = {}
                if TARGET_TOKEN:
                    hdrs["Authorization"] = f"Bearer {TARGET_TOKEN}"
                await client.delete(url, headers=hdrs)
        except httpx.RequestError as exc:
            # Best-effort; the TCP close is already enough for the
            # primary cancel path. Log so operators see hook breakage.
            logger.warning(
                "backend_cancel_hook_failed ip=%s session=%s err=%s",
                ip, sid_short, type(exc).__name__,
            )

    logger.info(
        "[%s] chat_cancel ip=%s user=%s session=%s cancelled=%s",
        INSTANCE_NAME, ip, session.email, sid_short, cancelled,
    )
    return {"cancelled": cancelled}


@app.post("/selftest")
async def selftest(
    request: Request,
    session: SessionData = Depends(verify_session),
):
    """Authenticated end-to-end probe of the VoxGate ↔ TARGET_URL wiring.

    Runs the same forward path as /chat (same payload shape, same headers,
    same timeout) and reports per-clause: TARGET_URL configured, backend
    reachable, 2xx status, valid JSON, object root, `response` is a string.
    Returns a structured JSON diagnostic — operators and backend integrators
    can `curl -b cookies.txt -H "X-CSRF-Token: …" -X POST /selftest` to
    pinpoint exactly which contract clause a misbehaving backend violates,
    without grepping container logs.

    The probe payload sets `metadata.test=true`. Backends that respect this
    flag are expected to no-op (no real side effects) and return an echoed
    response. Backends that ignore it process the request normally — be
    aware that running /selftest then triggers whatever side effects a real
    /chat call would.
    """
    diag: dict = {"ok": True, "checks": [], "request": None, "response": None}

    def passed(name: str, detail: str = "") -> None:
        diag["checks"].append({"name": name, "ok": True, "detail": detail})

    def fail(name: str, detail: str) -> dict:
        diag["ok"] = False
        diag["checks"].append({"name": name, "ok": False, "detail": detail})
        return diag

    if not TARGET_URL:
        return fail("target_url_configured", "TARGET_URL is empty in this VoxGate instance")
    passed("target_url_configured", TARGET_URL)

    sid = "selftest-" + secrets.token_hex(8)
    payload = {
        "user": "VoxGate self-test ping",
        "user_email": session.email,
        "session_id": sid,
        "metadata": {
            "lang": SPEECH_LANG,
            "instance": INSTANCE_NAME,
            "test": True,
        },
    }
    # Caller-visible headers: never leak the real bearer token. The
    # outbound request uses the real value; the diagnostic shows a
    # placeholder so the caller can confirm "yes a token was sent" or
    # "no, none was sent" without seeing the secret.
    visible_headers = {"Content-Type": "application/json"}
    outbound_headers = {"Content-Type": "application/json"}
    if TARGET_TOKEN:
        visible_headers["Authorization"] = "Bearer ***redacted***"
        outbound_headers["Authorization"] = f"Bearer {TARGET_TOKEN}"

    diag["request"] = {
        "url": TARGET_URL,
        "method": "POST",
        "headers": visible_headers,
        "body": payload,
    }

    ip = _client_ip(request)
    logger.info(
        "[%s] selftest ip=%s user=%s",
        INSTANCE_NAME, ip, session.email,
    )

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            res = await client.post(TARGET_URL, json=payload, headers=outbound_headers)
    except httpx.RequestError as exc:
        return fail("backend_reachable", f"{type(exc).__name__}: {exc}")
    elapsed_ms = round((time.time() - t0) * 1000)
    passed("backend_reachable", f"connected in {elapsed_ms}ms")

    body_text = res.text
    diag["response"] = {
        "status": res.status_code,
        "elapsed_ms": elapsed_ms,
        "body_preview": body_text[:500],
    }

    if res.status_code >= 400:
        return fail("status_2xx", f"backend returned HTTP {res.status_code}")
    passed("status_2xx", f"HTTP {res.status_code}")

    try:
        data = res.json()
    except ValueError:
        return fail("response_is_json", "body could not be parsed as JSON")
    passed("response_is_json", "")

    if not isinstance(data, dict):
        return fail("response_is_object", f"root is {type(data).__name__}, expected object")
    passed("response_is_object", "")

    resp_value = data.get("response")
    if not isinstance(resp_value, str):
        keys = list(data) if isinstance(data, dict) else []
        return fail(
            "response_field_string",
            f"missing or wrong type — top-level keys={keys}, "
            f"response={type(resp_value).__name__}",
        )
    passed("response_field_string", f"got {len(resp_value)} chars")

    diag["response"]["body_preview"] = resp_value[:500]
    return diag


app.mount("/", StaticFiles(directory="pwa", html=True), name="pwa")
