import logging
import os
import secrets
import sys
import time
from collections import deque

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("voxgate")

app = FastAPI()

API_TOKEN = os.environ.get("API_TOKEN", "")
TARGET_URL = os.environ.get("TARGET_URL", "")
TARGET_TOKEN = os.environ.get("TARGET_TOKEN", "")
INSTANCE_NAME = os.environ.get("INSTANCE_NAME", "VoxGate")
INSTANCE_COLOR = os.environ.get("INSTANCE_COLOR", "#c8ff00")
SPEECH_LANG = os.environ.get("SPEECH_LANG", "de-CH")
MAX_PROMPT_LENGTH = int(os.environ.get("MAX_PROMPT_LENGTH", "4000"))
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "")
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "120"))
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT", "You are a helpful assistant. Answer concisely."
)
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5")
SESSION_MAX_MESSAGES = 20
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "1800"))
MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", "1000"))
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "30"))
TRUST_PROXY_HEADERS = os.environ.get("TRUST_PROXY_HEADERS", "0") == "1"
ALLOW_OPEN = os.environ.get("VOXGATE_ALLOW_OPEN", "0") == "1"

if not ALLOW_OPEN and not API_TOKEN and (ANTHROPIC_API_KEY or TARGET_URL):
    print(
        "FATAL: API_TOKEN is empty but a backend is configured "
        "(ANTHROPIC_API_KEY or TARGET_URL). Refusing to start to prevent "
        "unauthenticated access to paid backends. "
        "Set API_TOKEN, or set VOXGATE_ALLOW_OPEN=1 for local development.",
        file=sys.stderr,
    )
    raise SystemExit(1)

if not API_TOKEN:
    print(
        "WARNING: API_TOKEN is not set. Endpoints are unauthenticated. "
        "Only acceptable for local development.",
        file=sys.stderr,
    )

if not TARGET_URL and not ANTHROPIC_API_KEY:
    print(
        "WARNING: Neither TARGET_URL nor ANTHROPIC_API_KEY is set. "
        "/prompt and /claude will return 503.",
        file=sys.stderr,
    )

_sessions: dict[str, dict] = {}
_anthropic_client = None
_rate_buckets: dict[str, deque] = {}


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic

        _anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _anthropic_client


def _client_ip(request: Request) -> str:
    if TRUST_PROXY_HEADERS:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _evict_expired_sessions(now: float) -> None:
    expired = [sid for sid, s in _sessions.items() if now - s["last_seen"] > SESSION_TTL_SECONDS]
    for sid in expired:
        del _sessions[sid]


def _enforce_session_cap() -> None:
    if len(_sessions) <= MAX_SESSIONS:
        return
    oldest = sorted(_sessions.items(), key=lambda kv: kv[1]["last_seen"])
    for sid, _ in oldest[: len(_sessions) - MAX_SESSIONS]:
        del _sessions[sid]


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(self), camera=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "manifest-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'"
    )
    return response


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path in ("/claude", "/prompt") and request.method == "POST":
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
    allow_methods=["POST", "GET"],
    allow_headers=["Authorization", "Content-Type"],
)

security = HTTPBearer(auto_error=False)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not API_TOKEN:
        return
    presented = credentials.credentials if credentials else ""
    if not secrets.compare_digest(presented, API_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")


class PromptRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)


class ClaudeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    session_id: str = Field(..., pattern=r"^[A-Za-z0-9_-]{8,128}$")


@app.get("/config")
async def get_config():
    return {
        "name": INSTANCE_NAME,
        "color": INSTANCE_COLOR,
        "lang": SPEECH_LANG,
        "maxLength": MAX_PROMPT_LENGTH,
    }


@app.post("/prompt")
async def prompt(req: PromptRequest, request: Request, _=Depends(verify_token)):
    if not TARGET_URL:
        raise HTTPException(status_code=503, detail="No target configured")

    ip = _client_ip(request)
    logger.info("prompt ip=%s text_len=%d", ip, len(req.text))

    headers = {"Content-Type": "application/json"}
    if TARGET_TOKEN:
        headers["Authorization"] = f"Bearer {TARGET_TOKEN}"

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            res = await client.post(TARGET_URL, json={"text": req.text}, headers=headers)
        except httpx.RequestError:
            logger.warning("prompt_target_unreachable ip=%s", ip)
            raise HTTPException(status_code=502, detail="Target unreachable")

    if res.status_code >= 400:
        logger.warning("prompt_target_error ip=%s status=%d", ip, res.status_code)
        raise HTTPException(status_code=502, detail="Target returned an error")

    try:
        data = res.json()
    except ValueError:
        data = {"response": res.text.strip()}

    return JSONResponse(content=data)


@app.post("/claude")
async def claude(req: ClaudeRequest, request: Request, _=Depends(verify_token)):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="No Anthropic API key configured")

    now = time.time()
    _evict_expired_sessions(now)

    ip = _client_ip(request)
    sid_short = req.session_id[:8]
    logger.info(
        "claude ip=%s session=%s text_len=%d sessions=%d",
        ip, sid_short, len(req.text), len(_sessions),
    )

    session = _sessions.setdefault(req.session_id, {"messages": [], "last_seen": now})
    session["last_seen"] = now
    _enforce_session_cap()
    if req.session_id not in _sessions:
        _sessions[req.session_id] = session
    history = session["messages"]
    history.append({"role": "user", "content": req.text})

    try:
        client = _get_anthropic_client()
        message = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=history,
        )
    except Exception:
        history.pop()
        logger.exception("claude_api_error ip=%s session=%s", ip, sid_short)
        raise HTTPException(status_code=502, detail="Anthropic API error")

    reply = "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )

    history.append({"role": "assistant", "content": reply})

    while len(history) > SESSION_MAX_MESSAGES:
        del history[0:2]

    return {"response": reply}


app.mount("/", StaticFiles(directory="pwa", html=True), name="pwa")
