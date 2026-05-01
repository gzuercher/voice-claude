---
description: Code quality rules for Python and vanilla JS
globs: "*.py,*.js,*.html,*.css"
---

# Code quality

## Python (server.py, auth/, tests/)

- Type hints on every function. Pydantic models for request/response
  shapes — Field constraints (`min_length`, `max_length`, `pattern`)
  do the validation at the framework boundary.
- No silenced exceptions. `except Exception:` is acceptable only when
  the next line either re-raises a domain error, returns an explicit
  fallback, or logs with enough context to debug from logs alone.
- Logging: use the module-level `logger` (`logging.getLogger(...)`).
  Never `print()` in server code. Audit lines must include at least
  IP, user e-mail (when authenticated) and session prefix — never the
  text payload.
- Outbound HTTP: `httpx.AsyncClient` with an explicit `timeout=`. Wrap
  in a function or method so tests can patch it (see how
  `tests/test_server.py` patches `httpx.AsyncClient`).
- `ruff` config in `pyproject.toml`, line length 100. `make lint`
  must be green before committing.
- New endpoint = new tests in `tests/test_server.py`: happy path,
  validation errors, auth errors (no session, missing CSRF), backend
  errors. No real network in tests — mock httpx outbound.

## JavaScript (pwa/)

- Vanilla JS only — no build step, no framework, no bundler. The
  files are served as-is.
- No `eval()`, no `new Function()`, no `innerHTML` with user-controlled
  data. Use `textContent` for any string that originated from a user
  message or a backend response.
- `console.log` is fine for debug-overlay opt-in (`debug.js`); never
  leave one behind in `app.js` / `auth.js` shipping in production.
- Keep modules small. The `app.js` IIFE is already at the upper limit
  of what is comfortable — split before adding another major feature.

## Both

- Imports / requires sorted: stdlib first, third-party next, local
  last. One blank line between groups.
- No new runtime dependencies without discussion. VoxGate stays small
  on purpose; every dep is a future update treadmill.
- No dead code, no commented-out blocks. Delete and rely on git.
