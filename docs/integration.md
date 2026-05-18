# VoxGate integration reference

> **Live at every running VoxGate instance:** `GET /integration`
> (no auth, `text/markdown`). Backend integrators can
> `curl https://<voxgate-host>/integration` to fetch the contract their
> target instance is actually shipping with — no repo checkout, no
> guessing the version. **This is the only URL you need to remember.**

---

## What is VoxGate?

A small voice-frontend PWA with a Google-Sign-In auth gate. Every
authenticated request is forwarded as a JSON POST to a backend you
configure via `TARGET_URL`. VoxGate has **no built-in LLM integration**
— the backend at `TARGET_URL` owns all chat logic (system prompts,
model selection, history, routing, tool calls).

If you are implementing that backend, the strict contract is below.
If you are running VoxGate, see the cheatsheet of other endpoints
right after.

## Endpoint map (all there is)

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/` | GET | none | The PWA itself, plus every static asset under it (`/app.js`, `/auth.js`, `/styles.css`, `/manifest.json`, `/icon.svg`, `/sw.js`, `/platform.js`, `/debug.js`) |
| `/integration` | GET | none | This page (markdown) |
| `/config` | GET | none | PWA config — branding, languages, Google client ID, max prompt length. JSON. |
| `/openapi.json` | GET | none | OpenAPI spec for VoxGate's HTTP surface (machine-readable) |
| `/docs` | GET | none | Interactive Swagger UI for the same spec |
| `/redoc` | GET | none | Alternative ReDoc rendering of the same spec |
| `/chat` | POST | session cookie + CSRF | The one endpoint the PWA calls for every chat turn. Body: `{text, session_id, lang}`. Returns `{response}`. Forwards to `TARGET_URL` using the contract below. |
| `/chat/stream` | POST | session cookie + CSRF | Streaming variant of `/chat`. Same request body. Response is `text/event-stream` (see [Streaming sub-contract](#streaming-sub-contract)). Optional — operators can disable via `STREAMING_ENABLED=0`. |
| `/chat/cancel` | POST | session cookie + CSRF | Cancel an in-flight `/chat/stream` for a session. Body: `{session_id}`. Returns `{cancelled: bool}`. Idempotent. |
| `/selftest` | POST | session cookie + CSRF | Authenticated diagnostic. Sends a synthetic request through the same forward path as `/chat` and returns a structured per-clause report (target configured, reachable, 2xx, JSON, object, response-string). Use it to debug "is my backend wired correctly?" without grepping logs. Sets `metadata.test=true` (see [test-mode flag](#test-mode-flag)). |
| `/auth/login/{provider}` | POST | none (origin-checked, rate-limited) | Exchange a provider ID token for a VoxGate session. Today only `provider=google`. Returns `429` after `AUTH_LOGIN_RATE_LIMIT_PER_MINUTE` (default 10/min/IP). |
| `/auth/logout` | POST | session + CSRF (when logged in) | Clears session and CSRF cookies. Idempotent. |
| `/auth/me` | GET | session cookie | `{email, provider}` of the signed-in user, or 401. |
| `/auth/providers` | GET | none | `{providers: [...]}` — identity providers this instance has registered. |
| `/debug-log` | POST | `X-Debug-Token` | 404 unless `DEBUG_ENABLED=1`. PWA opt-in diagnostics overlay. |

That's the entire surface. If you need anything else, you're guessing.

**No dedicated health-check endpoint.** Probes should hit `GET /config`
— it is cheap, requires no auth, and exercises the real request path
(middleware, CSP headers, JSON serialisation). A 200 there means the
process is alive and serving.

## Where to find the rest

Everything below is in the source repository, not at runtime. Pointers
are listed here so a backend integrator does not need to crawl the
repo:

- **Operator setup, env vars, reverse-proxy patterns:**
  [`docs/setup.md`](setup.md) in the repo.
- **Operator security checklist:** [`docs/security.md`](security.md).
- **Example backend implementations** (FastAPI minimal, FastAPI
  streaming SSE, Anthropic streaming adapter, Express, bash stub) —
  inline at the end of this document, see
  [Reference backend implementations](#reference-backend-implementations).
- **Roadmap and explicit non-goals:** [`docs/roadmap.md`](roadmap.md).
- **Contributing guide:** [`docs/contributing.md`](contributing.md).
- **PWA usage from the user's perspective:** the
  [project README](../README.md).

---

# Backend contract

This section is the **strict** contract between VoxGate and the
backend at `TARGET_URL`. Any deviation surfaces as a `502` to the PWA.

## Request: VoxGate → backend

`POST <TARGET_URL>` with `Content-Type: application/json`. If
`TARGET_TOKEN` is configured, an `Authorization: Bearer <TARGET_TOKEN>`
header is added. Outbound timeout is `REQUEST_TIMEOUT` seconds
(default 120).

```json
{
  "user":        "<text the user typed or spoke>",
  "user_email":  "<verified Google e-mail of the signed-in user>",
  "session_id":  "<opaque, client-generated, [A-Za-z0-9_-]{8,128}>",
  "metadata": {
    "lang":     "<BCP-47 tag the PWA was using, e.g. de-CH>",
    "instance": "<INSTANCE_NAME from VoxGate's .env>"
  },
  "attachments": [        // present only when the user attached files
    {
      "kind": "image",
      "mime": "image/jpeg",
      "name": "photo.jpg",
      "data": "<base64-encoded bytes>"
    }
  ]
}
```

Field semantics:

| Field | Trust | Purpose |
|---|---|---|
| `user` | user-typed | Free text. Validated for length (`MAX_PROMPT_LENGTH`, default 4000). May be empty if at least one attachment is present. |
| `user_email` | **server-injected, verified** | Authenticated by Google + allowlisted by the operator. Backends can rely on this for ACL decisions and *should not* trust any client-provided e-mail field. |
| `session_id` | client-generated | Opaque correlator. VoxGate keeps no state for it. The backend may use it as its own conversation key. |
| `metadata.lang` | client-set | The UI language at the moment of sending. May differ from `INSTANCE_NAME`'s default. Hint, not a guarantee. |
| `metadata.instance` | server-set | Useful when one backend serves multiple VoxGate instances (different families/contexts). |
| `attachments` | user-uploaded, validated | Optional array. Omitted entirely when the user uploaded nothing — backends may branch on key presence. See "Attachments" below. |

Backends may receive additional `metadata.*` fields in future versions.
**Treat unknown fields as informational, do not reject them.**

### Attachments (one-way, client → backend)

The PWA can upload images alongside (or instead of) text. VoxGate is a
**pure pass-through** for these — it validates size and mime, then
forwards the base64 verbatim. VoxGate never decodes the bytes, never
writes to disk, and has no shared volume with the backend. What the
backend does with the bytes (write to a Docker volume, push to S3,
inline into an LLM prompt as a vision input, …) is its own choice.

Per-attachment validation done by VoxGate before forwarding:

| Field | Constraint | Override env var |
|---|---|---|
| `kind` | string ≤ 16 chars (today only `"image"` is produced by the PWA, but backends should treat unknown kinds as informational) | — |
| `mime` | one of `image/jpeg`, `image/png`, `image/webp` | — |
| `name` | string ≤ 255 chars; may be empty | — |
| `data` | base64 string ≤ `MAX_ATTACHMENT_BASE64_BYTES` (default 4 MiB ≈ 3 MiB binary) | `MAX_ATTACHMENT_BASE64_BYTES` |

Per-request:

| Constraint | Default | Override env var |
|---|---|---|
| Max attachments per request | 4 | `MAX_ATTACHMENTS_PER_REQUEST` |
| `user` may be empty if attachments are present | — | — |
| `user` + no attachments → 422 | — | — |

The PWA currently downscales any picked photo to 1600px on the longest
side and re-encodes as JPEG (quality 0.85), so a typical phone photo
arrives at ~500 KiB regardless of source size or format (HEIC/PNG/etc.
are decoded and re-encoded by the browser canvas). Photos beyond the
client cap surface a friendly "image too large" message before any
network call.

**One-way today:** responses still match `{"response": "<text>"}`
exactly. Backends do not return images via the `/chat` contract. If
that becomes useful, it is a separate contract change with its own
discussion.

#### Recommended backend handling (suggestion, not contract)

Where a backend stores attachment bytes is its own choice — VoxGate
takes no opinion. But every backend ends up making the same handful
of decisions, so here is a sane default that downstream tools (LLM
containers, audit scripts, future backends sharing the same volume)
can rely on:

- **Storage path:** decode `data` and write to a deterministic path
  keyed by session and attachment index, e.g.
  `/data/voxgate/<session_id>/<idx>-<sanitised_name>`. Sanitise
  `name` to a safe filename (strip path separators, control chars,
  cap length); fall back to `<idx>.<ext>` derived from `mime` when
  `name` is empty.
- **Determinism:** `<session_id>` from the request as the directory,
  `<idx>` (0-based) as the prefix. Re-uploads in the same session
  overwrite predictably, which is usually what the user expects when
  iterating ("no, this photo").
- **Lifetime:** clean up either when the user starts a new session
  (the PWA mints a fresh `session_id` on "Neues Gespräch") or via a
  daily cron that drops directories older than 24 h. Pick whichever
  fits your retention policy. VoxGate keeps no state about
  attachments and cannot signal session boundaries to you.
- **Hand-off to LLM containers:** if the LLM runs in a sibling
  container, mount the same `/data/voxgate/` directory read-only
  into that container and pass the path string in the prompt. Avoid
  re-base64-ing the bytes for the LLM — file-on-disk is faster and
  Claude's `Read` tool handles it natively.
- **Privacy / GDPR:** these files contain user-uploaded images. They
  belong to the same data-protection regime as anything else the
  backend stores. Document the retention period; do not back up
  indefinitely without thinking about it.

None of this is enforced by VoxGate. A backend that prefers S3 keys,
sqlite blobs, or in-memory caching is equally fine — the contract is
the JSON shape above, nothing more.

## Response: backend → VoxGate

The backend must respond with HTTP 2xx **and** a JSON body of exactly
this shape:

```json
{ "response": "<assistant reply, plain string>" }
```

Strict rules:

- HTTP status `< 400`. `4xx` and `5xx` are forwarded as `502` to the
  PWA — the backend is the source of truth on what is or is not an
  error, but VoxGate intentionally collapses all backend errors into a
  single client-visible status.
- Body must be valid JSON. Plain-text responses are rejected.
- Body must be a JSON object (not an array, not a primitive).
- The object must contain key `"response"`.
- The value of `"response"` must be a string. Empty strings are
  allowed (e.g., the backend deliberately stays silent).

Anything else → VoxGate logs `backend_bad_shape` and returns `502`.

Additional keys in the response are tolerated but ignored — the PWA
sees only `{"response": ...}` plus the two optional follow-up fields
documented below. If you have metadata to surface in the UI, propose
extending the contract; do not stuff it into ad-hoc keys.

### Optional follow-up-hint fields

Backends may signal that the reply is a clarifying question and that
the user should answer immediately:

```json
{
  "response": "Welche Wurst meinst du?",
  "awaiting_user_input": true,
  "suggestion": "z.B. Cervelat"
}
```

| Field | Type | Default | Effect |
|---|---|---|---|
| `awaiting_user_input` | bool | `false` | When `true`, the PWA keeps the text input focused, does *not* auto-stop the mic session, and renders a `?` marker on the bubble. |
| `suggestion` | string | absent | When present, used as the text-input placeholder. |

Both fields default to absent/`false` — existing backends are
unaffected. They appear identically on `/chat` (legacy JSON) and inside
the `final` SSE event (streaming).

## Failure modes summary

| Backend behaviour | VoxGate response | Log line |
|---|---|---|
| Unreachable / connection refused / DNS fail / timeout | `502 Backend unreachable` | `backend_unreachable` |
| HTTP 4xx or 5xx | `502 Backend returned an error` | `backend_error` |
| Non-JSON body | `502 Backend response was not JSON` | `backend_non_json` |
| JSON without `response` string field | `502 Backend response did not match contract` | `backend_bad_shape` |

For completeness, the PWA can also see request-validation errors that
never reach the backend — `422` when `text` is empty/too long or
`session_id` does not match `^[A-Za-z0-9_-]{8,128}$`. Backends do not
need to handle these: VoxGate rejects the request before forwarding.

When debugging a 502, run on the VoxGate host:

```bash
docker compose logs --tail 30 vg | grep -E 'backend_(unreachable|error|non_json|bad_shape)'
```

The matching log line tells you exactly which clause was violated.

## Minimal reference backend (Python)

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/")
async def chat(req: Request):
    body = await req.json()
    user = body["user"]
    email = body["user_email"]
    session = body["session_id"]
    # ... do whatever (LLM call, planner, lookup, …)
    return {"response": f"hello {email}, you said: {user}"}
```

Set `TARGET_URL=http://your-backend:port/` in the VoxGate `.env` and
you're talking. Richer examples (Express, bash stub, streaming SSE,
Anthropic streaming adapter) are inline in
[Reference backend implementations](#reference-backend-implementations)
at the end of this document.

## Authentication boundary

By the time a request hits your backend, VoxGate has already:

- verified the user's Google ID token signature, issuer, audience and
  `email_verified` flag,
- matched the e-mail against the operator's `ALLOWED_EMAILS`,
- enforced the CSRF double-submit and (when configured) Origin check.

The backend can therefore trust `user_email` and treat the request as
an authorised action by that user. There is no shared bearer token to
verify on the backend side beyond the optional `TARGET_TOKEN` you set
yourself.

## Test-mode flag

When VoxGate's `POST /selftest` probe forwards to the backend, it
includes `metadata.test = true` (boolean) in the payload. Backends
*should* check this flag and either short-circuit (no real side
effects, e.g. don't write a calendar entry) or echo a synthetic
response. Backends that ignore the flag will process the request as a
normal `/chat` turn — the user typing "VoxGate self-test ping" by hand
would have the same effect.

Recognising the flag is a backend-side opt-in convention, not a hard
contract requirement. Document in your backend whether it honours
`metadata.test`.

## Self-test diagnostic shape

`POST /selftest` returns JSON like this on success:

```json
{
  "ok": true,
  "checks": [
    {"name": "target_url_configured", "ok": true,  "detail": "http://zplanner:8090/prompt"},
    {"name": "backend_reachable",     "ok": true,  "detail": "connected in 23ms"},
    {"name": "status_2xx",            "ok": true,  "detail": "HTTP 200"},
    {"name": "response_is_json",      "ok": true,  "detail": ""},
    {"name": "response_is_object",    "ok": true,  "detail": ""},
    {"name": "response_field_string", "ok": true,  "detail": "got 4 chars"}
  ],
  "request":  { "url": "...", "method": "POST", "headers": {...}, "body": {...} },
  "response": { "status": 200, "elapsed_ms": 23, "body_preview": "pong" }
}
```

On failure, `ok` flips to `false` and the offending check carries the
diagnostic in its `detail`. Bearer tokens are masked as
`Bearer ***redacted***` in the response — the real `TARGET_TOKEN` never
appears in the diagnostic body. Curl example, given a valid session
cookie jar:

```bash
CSRF=$(awk '$6=="vg_csrf"{print $7}' cookies.txt)
curl -b cookies.txt -H "X-CSRF-Token: $CSRF" -X POST \
     https://<voxgate-host>/selftest | jq .
```

## Streaming sub-contract

`POST /chat/stream` is an **additive** alternative to `/chat`. Same
auth, same request body, but the response is `text/event-stream`. The
PWA falls back to `/chat` transparently when the backend doesn't speak
SSE — backends can adopt streaming at their own pace.

### Backend negotiation

VoxGate adds `Accept: text/event-stream` to the outbound POST and
inspects the response `Content-Type`:

| Backend returns | VoxGate behaviour |
|---|---|
| `Content-Type: text/event-stream` | Frames are proxied line-buffered to the PWA. |
| `Content-Type: application/json` with `{"response": "..."}` | Adapted to a single `chunk` + `final` event. |
| Anything else | Single `error` event with `code: backend_bad_shape`. |

### Event types

```
event: chunk
data: {"delta": "<text fragment>"}

event: tool
data: {"name": "<tool_name>", "phase": "start" | "end"}

event: final
data: {"response": "<full assembled text>",
       "awaiting_user_input": <bool, optional>,
       "suggestion": "<string, optional>"}

event: error
data: {"code": "<short_code>", "message": "<human>"}
```

Rules:

- `final` is **mandatory and terminal**. The PWA uses its `response`
  field as the canonical reply (idempotent against the accumulated
  `chunk.delta`s, which keeps things sane when a backend's chunking
  mid-sentence doesn't line up with what it actually meant to send).
- `chunk.delta` is appended in order. **Never assume word or sentence
  boundaries** — backends may split mid-codepoint or mid-Markdown.
- `tool` events are informational. Skipping them is fine; UI may
  render a transient indicator (e.g. "🔧 reading inventory…"). Backends
  do not have to pair `start`/`end` strictly — the PWA treats each
  event independently and resets on `final`.
- Connection close without a `final` event is treated as an error
  (PWA renders a failed-turn message, same UX as a 502 on `/chat`).
- Error codes used by VoxGate itself: `backend_error`,
  `backend_unreachable`, `backend_non_json`, `backend_bad_shape`,
  `stream_truncated`, `cancelled`. Backends may add their own codes.

### Encoding rules

These are the wire-format details that trip up SSE implementors. None
are negotiable — getting them right is the difference between "works
on my machine" and "works in production behind a proxy".

- **One JSON object per `data:` line, minified.** Encode embedded
  newlines inside strings as `\n` (escaped) — never as raw bytes. A
  bare newline inside the `data:` value terminates the SSE event.
  `json.dumps(obj, separators=(",", ":"))` does the right thing.
- **UTF-8 only.** Multi-byte codepoints are fine; VoxGate proxies
  bytes line-buffered and the PWA decodes with `TextDecoder` in
  streaming mode, so a chunk that lands mid-codepoint is reassembled
  on the next chunk.
- **Frame separator is `\n\n`** (two line-feeds). Some libraries emit
  `\r\n\r\n`; both are accepted by browsers and by VoxGate. Pick one
  and stick with it.
- **Comment lines** (starting with `:`) are passed through verbatim
  and ignored by the PWA — useful for heartbeats, see below.
- **No chunked-encoding gymnastics required.** Just write your bytes
  to the response body and flush per event; FastAPI's
  `StreamingResponse` and Express' `res.write` handle the framing.

### Heartbeats and proxy buffering

VoxGate sets a per-byte idle timeout on the outbound stream
(`STREAM_IDLE_TIMEOUT`, default 60 s). A turn that goes silent for
longer — typically a long-running tool call — will be killed with
`stream_truncated`. Backends that expect such gaps should emit a
heartbeat every 15-30 s:

```
: heartbeat
```

(comment line + `\n\n`). VoxGate forwards it, the PWA ignores it, and
the idle timer resets.

If you sit behind nginx / Cloudflare / Caddy, also set
`X-Accel-Buffering: no` on the response (VoxGate already does this on
its own response to the PWA). Without it, the proxy may collect bytes
until you have ~8 KB before flushing, which defeats the entire point
of streaming.

### Ordering and idempotency

- `chunk` events are appended in arrival order; the PWA renders them
  as they come.
- `tool` events may be interleaved with `chunk`s.
- `final.response` is the **canonical** reply. If the PWA's
  concatenated chunks happen to differ from `final.response` (e.g.
  because the backend revised a tool-use thought mid-stream and
  shouldn't have shown it), the canonical text wins on screen.
  Emitting `final.response = "".join(all_deltas)` is the simplest
  correct choice for backends that don't have a reason to differ.
- Anything emitted after `final` is dropped — VoxGate closes the
  proxy as soon as it sees that event.

### Cancel

`POST /chat/cancel` with `{"session_id": "<sid>"}` aborts the in-flight
stream for that session.

- **Primary mechanism (always on):** VoxGate cancels the outbound
  httpx task → backend sees a clean TCP close (FastAPI:
  `ClientDisconnect`; Express: `req.on('close')`). Backends *should*
  treat that as "abort the current turn".
- **Optional backend hook:** if the operator sets
  `BACKEND_CANCEL_URL` (with literal `{session_id}` as a placeholder),
  VoxGate additionally fires a fire-and-forget
  `DELETE <BACKEND_CANCEL_URL>` with a 5 s timeout after closing the
  stream. Use this for backends that need an explicit cleanup signal
  beyond TCP close.
- Idempotent: cancelling a session with no in-flight stream returns
  HTTP 200 with `{"cancelled": false}`.

### Deployment note

The cancel registry is per-process. If you run multiple Uvicorn workers
(`--workers N`, `N>1`), `/chat/cancel` may land in a different worker
than the stream it should cancel. The bundled Docker image runs a
single worker on purpose — keep it that way unless you add external
state.

### Testing your streaming backend

Once your backend responds with `text/event-stream`, you can verify
end-to-end without the PWA:

```bash
# Direct against the backend (skips VoxGate auth — for local dev only):
curl -N -X POST -H 'Content-Type: application/json' \
     -H 'Accept: text/event-stream' \
     -d '{"user":"ping","user_email":"dev@example.com",
          "session_id":"abcd1234","metadata":{"lang":"de-CH","instance":"dev"}}' \
     http://127.0.0.1:9000/

# Through VoxGate (real auth path, requires a logged-in cookie jar):
CSRF=$(awk '$6=="vg_csrf"{print $7}' cookies.txt)
curl -N -b cookies.txt -H "X-CSRF-Token: $CSRF" \
     -H 'Content-Type: application/json' \
     -d '{"text":"hi","session_id":"abcd1234"}' \
     https://<voxgate-host>/chat/stream
```

`-N` disables curl's output buffering so you see chunks as they
arrive. A correctly framed stream looks like:

```
event: chunk
data: {"delta":"Hel"}

event: chunk
data: {"delta":"lo"}

event: final
data: {"response":"Hello"}
```

### Migration: existing JSON backend → streaming

Concrete checklist for converting a backend that today returns
`{"response": "..."}`:

1. **Detect the negotiation.** Branch on
   `Accept: text/event-stream` in the request headers. Keep the JSON
   path untouched so VoxGate can still hit it from `/chat` and so
   integration tests don't break.
2. **Wrap your LLM call in an async generator.** If your client SDK
   exposes a streaming iterator (Anthropic `messages.stream(...)`,
   OpenAI `stream=True`, Ollama `/api/chat`, etc.), yield each token
   as a `chunk` event. If it doesn't, you can still adopt streaming
   by yielding one chunk per logical step (per sentence, per tool
   result) — any progressivity beats none.
3. **Always emit `final`.** Send the full assembled text in
   `final.response`. This is the safety net for clients whose chunk
   reassembly drifted.
4. **Handle disconnects.** On a cancel, the TCP connection closes —
   check for that between chunks (FastAPI: `await req.is_disconnected()`,
   Express: `req.on('close', ...)`) and abort the LLM call. Otherwise
   you keep paying for tokens the user will never see.
5. **Emit heartbeats** if any step in your turn can take >30 s of
   silence (long tool calls, slow first token).
6. **Optional: surface tool use.** If your backend invokes external
   tools, emit `tool` events with `name` + `phase`. The PWA shows a
   transient indicator; ignoring this is fine.
7. **Optional: signal clarifying questions.** When the assistant
   needs more input from the user, set `awaiting_user_input: true`
   (and optionally `suggestion: "..."`) in the `final` payload.

A worked example is in [Python / FastAPI — streaming echo (SSE)](#python--fastapi--streaming-echo-sse)
below.

### Non-goals

- **Multiple concurrent turns per session.** The PWA enforces one
  in-flight turn (auto-cancel on new prompt). Backends may rely on
  this.
- **Server-side TTS streaming.** VoxGate ships the text; the PWA's
  `speechSynthesis` speaks it once the `final` event lands. Partial-
  sentence TTS is out of scope (see roadmap).
- **Persistent server-side conversation log inside VoxGate.**
  `session_id` stays opaque; backends own their own history.

## Versioning

This document is not yet versioned — there has only ever been one
contract version (the one above). If a breaking change becomes
necessary, the response will gain a `voxgate-contract-version` HTTP
header and integrators will be notified before the change ships.

---

## Reference backend implementations

The strict contract is everything above. The runnable examples below
are reference templates for the most common backend shapes — drop the
parts you don't need.

> ⚠️ Bind any backend below to `127.0.0.1` (or a private Docker
> network), or require a `TARGET_TOKEN` of its own. Otherwise VoxGate
> inadvertently exposes your backend to the internet.

### Python / FastAPI — minimal echo

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/")
async def chat(req: Request):
    body = await req.json()
    user = body["user"]
    email = body["user_email"]
    # body may also include body["attachments"] — list of
    # {kind, mime, name, data}. See "Attachments" above.
    return {"response": f"hello {email}, you said: {user}"}
```

Run: `uvicorn app:app --host 127.0.0.1 --port 9000`.
VoxGate `.env`: `TARGET_URL=http://127.0.0.1:9000/`.

### Python / FastAPI — streaming echo (SSE)

Demonstrates the optional streaming sub-contract. VoxGate adds
`Accept: text/event-stream` to the outbound POST; if the backend
replies with that content-type, VoxGate proxies the frames through
to the PWA. Otherwise the legacy `{"response": "..."}` shape is
adapted to a single chunk+final event — so you can ship streaming
and non-streaming endpoints from the same backend.

The example below covers all the moving parts a real streaming
backend needs: SSE framing, content-type negotiation, chunked output,
optional tool events, heartbeats, disconnect detection, and the
follow-up-hint fields. Drop unused parts when adapting.

```python
import asyncio, json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI()


def sse(event: str, data: dict) -> bytes:
    """One SSE frame. `separators` keeps the JSON on a single line,
    which is what the contract requires for `data:`."""
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


HEARTBEAT = b": keepalive\n\n"


@app.post("/")
async def chat(req: Request):
    body = await req.json()
    accepts_sse = "text/event-stream" in req.headers.get("accept", "")
    user = body["user"]
    email = body["user_email"]

    if not accepts_sse:
        # Legacy non-streaming path — same shape backends have always
        # returned. Keep this branch so /chat (without /stream) and
        # smoke tests via curl still work.
        return {"response": f"hello {email}, you said: {user}"}

    async def gen():
        deltas: list[str] = []

        # Optional: surface a tool call to the UI.
        yield sse("tool", {"name": "lookup_user_prefs", "phase": "start"})
        await asyncio.sleep(0.2)
        yield sse("tool", {"name": "lookup_user_prefs", "phase": "end"})

        # In a real backend, iterate your LLM client's streaming
        # response here and yield each token as a chunk.
        text = f"hello {email}, you said: {user}"
        for word in text.split():
            # User hit Stop, or submitted a new prompt while this one
            # was still running. VoxGate closed the TCP connection;
            # abort the LLM call (which would otherwise burn tokens).
            if await req.is_disconnected():
                return
            delta = word + " "
            deltas.append(delta)
            yield sse("chunk", {"delta": delta})
            await asyncio.sleep(0.05)

        # Heartbeat example: emit one every 15-30 s when your turn
        # has a silent phase longer than STREAM_IDLE_TIMEOUT (60 s
        # default). Without it the proxy times out the stream.
        # yield HEARTBEAT

        final = {"response": "".join(deltas).rstrip()}
        # Optional: tell the PWA this was a clarifying question and
        # the user should answer immediately.
        if user.lower().startswith("which"):
            final["awaiting_user_input"] = True
            final["suggestion"] = "e.g. the red one"
        yield sse("final", final)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            # Defence in depth — VoxGate already sets this on its own
            # response to the PWA, but if you also sit behind a
            # buffering proxy of your own (nginx, Cloudflare), this
            # header makes sure your bytes reach VoxGate immediately.
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache, no-transform",
        },
    )
```

What you don't need to do:

- **No chunked-encoding setup.** `StreamingResponse` handles that.
- **No CORS / auth headers.** VoxGate is the only client that ever
  hits your backend; bind to `127.0.0.1` or a private Docker network.
- **No session storage in VoxGate.** `session_id` is opaque — if you
  want history, key it yourself (see the Anthropic adapter below).

### Python / FastAPI — voice-to-Claude adapter (streaming)

A small adapter that forwards to the Anthropic API. This used to be
built into VoxGate; it now lives in your backend so VoxGate stays
LLM-agnostic. The adapter serves both the legacy JSON path *and* SSE
streaming from a single endpoint — VoxGate picks whichever it asks
for via `Accept`.

```python
import json, os
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from anthropic import AsyncAnthropic

app = FastAPI()
client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Per-session in-memory history, keyed by VoxGate's session_id.
HISTORY: dict[str, list[dict]] = {}
MAX_TURNS = 20
SYSTEM = "You are a helpful assistant. Answer concisely."


def sse(event: str, data: dict) -> bytes:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


def _trim(history: list[dict]) -> None:
    while len(history) > MAX_TURNS:
        del history[0:2]


@app.post("/")
async def chat(req: Request):
    body = await req.json()
    sid = body["session_id"]
    history = HISTORY.setdefault(sid, [])
    history.append({"role": "user", "content": body["user"]})

    accepts_sse = "text/event-stream" in req.headers.get("accept", "")

    if not accepts_sse:
        # Non-streaming branch — one round-trip, full reply.
        msg = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM,
            messages=history,
        )
        reply = "".join(
            b.text for b in msg.content if getattr(b, "type", None) == "text"
        )
        history.append({"role": "assistant", "content": reply})
        _trim(history)
        return {"response": reply}

    async def gen():
        deltas: list[str] = []
        try:
            async with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=SYSTEM,
                messages=history,
            ) as stream:
                async for text in stream.text_stream:
                    if await req.is_disconnected():
                        return                       # user cancelled
                    deltas.append(text)
                    yield sse("chunk", {"delta": text})
        except Exception as exc:
            yield sse("error", {"code": "llm_error", "message": str(exc)})
            return

        reply = "".join(deltas)
        history.append({"role": "assistant", "content": reply})
        _trim(history)
        yield sse("final", {"response": reply})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache, no-transform",
        },
    )
```

`pip install fastapi uvicorn anthropic`. Run on a private port; set
`TARGET_URL=http://127.0.0.1:9000/` in VoxGate's `.env`. The PWA
automatically uses `/chat/stream` when `streaming: true` is reported
by `/config` (default) — no PWA changes needed to switch the backend.

If you do tool-use, emit `tool` events from the
`async for event in stream:` loop on `content_block_start` /
`content_block_stop` blocks where `type == "tool_use"`. VoxGate
forwards them verbatim; the PWA renders a transient indicator.

This adapter ignores any `body["attachments"]`. To pass images through
to Claude as a vision input, decode each attachment's `data` field
(base64) and append it as a `{"type": "image", "source": ...}` content
block to the user message — see the
[Attachments](#attachments-one-way-client--backend) section above for
the field semantics.

### Node / Express — echo

```javascript
import express from "express";

const app = express();
app.use(express.json({ limit: "20mb" })); // enough headroom for attachments

app.post("/", (req, res) => {
  const { user, user_email } = req.body;
  res.json({ response: `Hello ${user_email}, you said: ${user}` });
});

app.listen(9000, "127.0.0.1");
```

### Bash + nc — test stub

```bash
#!/usr/bin/env bash
# Tiny HTTP responder. Test use only — does not parse the request body.
while true; do
  printf 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n%s' \
    '{"response":"ok"}' | nc -l -p 9000 -q 1
done
```

### Your own service

If your service already has an HTTP API (e.g. a planner with its own
business logic), give it an endpoint that accepts the
[contract](#backend-contract) and returns `{"response": "..."}`. The
`user_email` field is verified by VoxGate via Google Sign-In; backends
can rely on it for ACL decisions and *should not* trust any
client-provided e-mail.
