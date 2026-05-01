---
description: Tech stack and build commands for VoxGate
globs: "*.py,*.html,*.js,*.json"
---

# Development stack

## Tech stack
- **Backend:** Python 3.10+, FastAPI, Uvicorn, httpx
- **Frontend:** Vanilla HTML/CSS/JS (no build step)
- **Speech:** Web Speech API. Default selectable list:
  `de-CH, fr-CH, it-CH, en-US, es-ES`. Configurable via `SPEECH_LANGS`.
- **Reverse proxy:** Caddy (production; bundled in `deploy/caddy/`)

## Build & run

```bash
make setup       # create venv, install dependencies
make run         # uvicorn server:app on :8000
make test        # pytest
make check       # lint + tests
```

## Verification

Check every change before reporting it as done:
1. Server starts without errors.
2. `make test` is green.
3. If UI changes: verify in the browser (and on a phone for PWA changes).

## Do not self-implement

| Topic | Use instead |
|---|---|
| Auth/Login | Google Sign-In with allowlist (`GOOGLE_CLIENT_ID` + `ALLOWED_EMAILS`) |
| Password hashing | Not applicable (identity provider handles credentials) |
| Input validation | Pydantic `Field` constraints |
