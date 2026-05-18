# VoxGate

**Talk to your chatbot by voice — straight from your phone.**

VoxGate is a small voice-frontend PWA you install on your phone home
screen like a native app. Tap the mic, speak, and hear the answer read
back to you. VoxGate authenticates the speaker (Google Sign-In + an
operator-controlled allowlist) and forwards each turn to a backend you
configure via `TARGET_URL`. The backend owns all LLM logic.

VoxGate has **no built-in LLM integration**. There is no Claude/OpenAI
client inside; if you want voice-to-Claude, run a small adapter
container behind `TARGET_URL` that speaks the contract below. The
project is deliberately a thin, opinionated voice + auth shell.

## Languages

VoxGate is language-agnostic by design — your backend (and the LLM
behind it) can answer in any language you speak. The UI offers a small
selectable set (default: German, French, Italian, English, Spanish —
Swiss locales for the first three). What actually works depends on
three independent layers:

| Layer | What it does | Caveats |
|---|---|---|
| **Speech recognition** | Browser converts your voice to text | Standard variants only — no Schwyzerdütsch / regional dialects. Quality varies by browser (Chrome best, Safari/iOS limited). |
| **Backend** | Understands and answers | Whatever your TARGET_URL routes to. |
| **TTS (read-aloud)** | Browser speaks the response | Depends on the voices installed on the device. The locale tag (`de-CH`, `fr-CH`, …) is a *preference*, not a guarantee. |

The selectable list is configurable via `SPEECH_LANGS` (see
[`docs/setup.md`](docs/setup.md#configuration)).

## What do you want to do?

### A) Voice-frontend on your own (sub-)domain

Recommended path. You need a subdomain pointing at your server and a
backend that speaks the [contract](docs/integration.md).

```bash
git clone git@github.com:gzuercher/vox-gate.git
cd vox-gate/deploy/caddy
cp .env.example .env
# Fill in: VOXGATE_DOMAIN, ACME_EMAIL, GOOGLE_CLIENT_ID, ALLOWED_EMAILS,
# TARGET_URL.
docker compose up -d
```

Caddy fetches a Let's Encrypt certificate automatically. Details:
[`deploy/caddy/README.md`](deploy/caddy/README.md).

### B) Existing reverse-proxy infra (Traefik, Kubernetes, nginx)

Use the root `docker-compose.yml`. It only ships the VoxGate container;
cert handling and hostname routing happen in your infra. Notes:
[`docs/setup.md`](docs/setup.md#reverse-proxy).

### C) No domain of your own (Cloudflare Tunnel / Tailscale Funnel)

VoxGate works behind any tunnel — Cloudflare or Tailscale provide HTTPS
and a hostname. Concept and pointers to the official setups:
[`docs/setup.md`](docs/setup.md#tunnel-in-front).

---

## Using the app

After installing the PWA on your home screen, open it:

| Element | Function |
|---|---|
| **Mic button (large)** | Tap to start recording. Tap again to send. |
| **Transcript box** | Editable any time — tap to type, mix with voice freely. |
| **Camera (📷)** | Pick a photo from your library or take one — sent alongside (or instead of) text on the next tap. |
| **Clear (✕)** | Wipes the transcript and any attached image, returns to idle. |
| **Language (top left)** | Switch UI language. Persisted. |
| **Speaker (header)** | Mute/unmute speech output. |
| **Logout (header, 🚪)** | Sign out. Visible only when signed in. |
| **Status dot (top right)** | Green = ready, blinking = sending, red = error. |
| **New conversation (bottom)** | Start a new session id (your backend may use this to reset history). |

Replies are read aloud automatically unless muted. If you tap the mic
again while audio is playing, the current speech is cancelled.

### Requirements

- **Browser:** Chrome on Android or desktop (Web Speech API).
  Safari/iOS support is limited.
- **Microphone permission** must be granted on first launch.
- **HTTPS** is mandatory on Android — solved by Caddy/tunnel above.

## Installing the PWA on your phone

1. Open Chrome on Android → `https://your-voxgate-host`.
2. The first screen offers **Sign in with Google**. Use a Google
   account that the operator has added to `ALLOWED_EMAILS`. The login
   produces a server-signed, `HttpOnly` session cookie — no token is
   stored in the browser.
3. Three-dot menu → "Add to Home screen".
4. The app now opens like any other app, with its own icon and color.

If you deploy multiple instances on different hostnames, repeat for
each — every URL becomes its own PWA with its own color.

## Access (operator + user)

VoxGate authenticates users via **Google Sign-In**. The operator lists
permitted Google accounts in `ALLOWED_EMAILS`; everybody else is
rejected at login. Practical guidance:

- **Set `GOOGLE_CLIENT_ID` and `ALLOWED_EMAILS`** in `.env` before
  sharing the URL.
- **Set a stable `SESSION_SECRET`** so sessions survive container
  restarts. The auto-generated, per-restart secret is fine for
  development but logs everyone out on every restart.
- **Granting access:** add the user's Google e-mail to
  `ALLOWED_EMAILS`. Takes effect on the next request — no restart.
- **Revoking access:** remove the e-mail from `ALLOWED_EMAILS`. The
  next request from that user's session returns 403, which kicks the
  PWA back to the login screen.
- **Lost device:** the device's session cookie remains valid until its
  TTL expires (`SESSION_COOKIE_TTL_SECONDS`, default 7 days) or until
  the e-mail is revoked. For immediate revocation, remove the e-mail
  from the allowlist.

Edge-level pre-auth (HTTP Basic Auth in your reverse proxy, Cloudflare
Access, Tailscale-only access) is independently possible — see
[`docs/setup.md`](docs/setup.md) and the security checklist in
[`docs/security.md`](docs/security.md).

## Troubleshooting

| Problem | What to do |
|---|---|
| Mic doesn't react | Grant permission in the browser. On Android the page must be HTTPS. |
| No speech output | Check the speaker button. iOS has limited Web Speech support. |
| `401` error | Session expired or missing. The PWA shows the Google Sign-In screen automatically. |
| `403` error | Your Google account is not in `ALLOWED_EMAILS` (ask the operator) or your session was revoked. |
| `429` error | Rate limit hit. Wait and retry. |
| `502` on `/chat` | Backend at TARGET_URL returned an error, was unreachable, or violated the response contract (see `docs/integration.md`). |
| `503` on `/chat` | TARGET_URL is not configured. |
| Doesn't work on Safari/iOS | Web Speech API is limited there; use Chrome. |

---

The rest is reference material for developers and clients calling the
HTTP API. For installation/operation see [`docs/setup.md`](docs/setup.md).
For the security checklist see [`docs/security.md`](docs/security.md).
For the backend JSON contract (including runnable backend examples)
see [`docs/integration.md`](docs/integration.md). For contributing
see [`docs/contributing.md`](docs/contributing.md). For where the
project might go next see [`docs/roadmap.md`](docs/roadmap.md).

## Architecture

```
┌─────────────┐                            ┌──────────────────┐
│  PWA        │                            │                  │
│  (phone     │     POST /chat             │                  │     POST TARGET_URL
│  home       │  ───────────────────────►  │  VoxGate server  │  ───────────────────►  Your backend
│  screen)    │  ◄───────────────────────  │  (FastAPI)       │  ◄───────────────────  (LLM, planner, …)
│             │                            │                  │
└─────────────┘                            └──────────────────┘
        │                                          ▲
        │ Google Sign-In (id_token)                │
        ▼                                          │
   accounts.google.com                             │
        │                                          │
        └──────────────────────────────────────────┘
                       Verified e-mail
```

VoxGate exposes a single chat endpoint:

- **`POST /chat`** — authenticated request. VoxGate enriches with the
  verified user e-mail and forwards to `TARGET_URL`. Strict response
  contract.

The full HTTP surface (endpoints, request/response shapes,
attachments, error codes, auth flows) is documented in
[`docs/integration.md`](docs/integration.md). That file is also
served live at `GET /integration` on every running instance — backend
integrators can `curl https://<voxgate-host>/integration` to fetch
the exact contract their target version ships with.

## File structure

```
voxgate/
├── server.py              # FastAPI gateway (/chat, /config, /auth/*)
├── auth/                  # Google ID-token verification + session cookies
├── pwa/                   # PWA (HTML, JS, CSS, manifest, service worker)
├── tests/                 # pytest tests
├── deploy/
│   └── caddy/             # Bundled Caddy + VoxGate (recommended path)
├── docs/
│   ├── setup.md            # Installation and operation
│   ├── security.md         # Operator security checklist
│   ├── contributing.md     # Development workflow
│   ├── integration.md      # HTTP surface + /chat → TARGET_URL contract + backend examples
│   ├── roadmap.md          # Future-development ideas (incl. "Shipped")
│   └── lessons.md          # Architecture-decision log (mistakes + fixes)
├── .github/                # CI workflow + PR/issue templates
├── .claude/rules/          # Binding code rules for human + Claude contributors
├── CHANGELOG.md            # User-visible changes per version
├── SECURITY.md             # Vulnerability disclosure policy
├── .env.example            # Configuration template (api-only, root)
├── docker-compose.yml      # api-only (no proxy bundled)
├── Dockerfile
├── pyproject.toml
├── Makefile                # make setup/run/test/lint
├── README.md               # This file
├── CLAUDE.md               # Playbook for Claude Code
└── LICENSE
```

## License

MIT
