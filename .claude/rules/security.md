---
description: Security rules for the VoxGate stack (Python + vanilla JS)
globs: "*.py,*.js,*.html"
---

# Security

## Boundaries

- **VoxGate is the auth boundary.** Endpoints handling user requests
  must declare `session: SessionData = Depends(verify_session)`. The
  dependency validates the signed `vg_session` cookie *and* the
  `X-CSRF-Token` header against `vg_csrf` (double-submit). No endpoint
  bypasses the dependency without an explicit reason in the docstring.
- **Allowlist re-checked on every authenticated request.** Removing a
  user from `ALLOWED_EMAILS` revokes access on the next request.
  Never cache the allowlist decision past the request boundary.
- **`user_email` is server-injected** before forwarding to TARGET_URL.
  Never accept a client-provided `user_email` field.

## Secrets and config

- No secrets (API keys, tokens, OAuth client secrets, session secrets)
  in code, tests, or fixtures. Read from `os.environ` / `.env`.
- `.env`, `.env.*` are gitignored; `.env.example` is the template and
  must not contain real values. New env vars get an entry there *and*
  in `deploy/caddy/.env.example` when deploy-relevant.
- Logs include user e-mail, IP, session prefix, byte counts. Logs
  never include the text payload, the session cookie, the CSRF token,
  the Google ID token, or any `Authorization` header value.

## Input handling

- Pydantic `Field` constraints (`min_length`, `max_length`, `pattern`,
  `max_items`) at the request boundary. Don't post-validate in the
  handler.
- `session_id` is always validated against `^[A-Za-z0-9_-]{8,128}$`.
- Frontend: never `innerHTML` with user-controlled or backend-returned
  text — use `textContent`. Strict CSP is set in `server.py`; do not
  weaken it (no `'unsafe-inline'` for scripts, no wildcard origins).

## Outbound

- Outbound HTTP uses `httpx.AsyncClient` with explicit `timeout=`,
  never indefinite. The default `REQUEST_TIMEOUT` is the upper bound;
  endpoints may shrink but not grow it.
- Backend errors collapse to `502` for the PWA — never propagate the
  backend's status code, body, or headers to the client.

## Sensitive responses

- Error messages exposed to the PWA must not contain stack traces,
  paths, or internal state. The strict response-shape contract on
  TARGET_URL replies prevents accidental backend leakage.
