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
- **Example backend implementations** (FastAPI, Express, bash, an
  Anthropic adapter you can use as `TARGET_URL` to get voice-to-Claude
  back without re-introducing it into VoxGate itself):
  [`docs/backends.md`](backends.md).
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
sees only `{"response": ...}`. If you have metadata to surface in the
UI, propose extending the contract; do not stuff it into ad-hoc keys.

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
you're talking. Richer examples (Express, bash stub, Anthropic
adapter): [`docs/backends.md`](backends.md) in the repo.

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

## Versioning

This document is not yet versioned — there has only ever been one
contract version (the one above). If a breaking change becomes
necessary, the response will gain a `voxgate-contract-version` HTTP
header and integrators will be notified before the change ships.
