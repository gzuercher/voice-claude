# VoiceClaude

Voice-controlled interface for Claude Code – installable as a PWA on mobile.

Speech input on Pixel → Server receives text → Claude Code CLI processes → Response back to phone.

## Architecture

```
┌─────────────┐       HTTPS/POST        ┌─────────────────┐
│  PWA on     │  ──────────────────────► │  FastAPI Server  │
│  Android    │  ◄────────────────────── │  (VPS / local)   │
│  (Chrome)   │       JSON Response      │                  │
└─────────────┘                          │  → claude -p "…" │
                                         └─────────────────┘
```

## Features

- **Web Speech API** with `de-CH` – continuous recording without auto-stop
- **PWA** – installable on homescreen, standalone mode
- **Token auth** – optional Bearer token for API access
- **Minimal UI** – dark theme, IBM Plex Mono, zero overhead

## File Structure

```
voiceclaude/
├── server.py          # FastAPI backend, invokes claude CLI
├── pwa/
│   ├── index.html     # Frontend with Speech Recognition
│   ├── manifest.json  # PWA manifest
│   ├── sw.js          # Service Worker
│   └── icon.svg       # App icon
└── .venv/             # Python virtual environment
```

## Setup (local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn

uvicorn server:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in Chrome. Web Speech API works on localhost without HTTPS.

## Setup (VPS with HTTPS)

HTTPS is required for the Web Speech API on Android.

```bash
# 1. Start server (API_TOKEN is required for production!)
API_TOKEN=your-secret-token ALLOWED_ORIGIN=https://voice.example.com uvicorn server:app --host 127.0.0.1 --port 8000

# 2. Caddy as reverse proxy (automatic HTTPS)
# Caddyfile:
# voice.example.com {
#     reverse_proxy localhost:8000
# }
```

On Pixel: Chrome → `https://voice.example.com` → three-dot menu → "Add to Home screen".

## Configuration

| Variable | Description | Default |
|---|---|---|
| `API_TOKEN` | Bearer token for `/prompt` endpoint (**required for production**) | empty (warning at startup) |
| `ALLOWED_ORIGIN` | Allowed CORS origin (e.g. `https://voice.example.com`) | empty (no cross-origin) |

Server URL and token can also be configured in the app under Settings (⚙).

> **Security note:** Without `API_TOKEN`, the server starts in unauthenticated mode and logs a warning. Never expose an unauthenticated server to the internet.

## API

```
POST /prompt
Content-Type: application/json
Authorization: Bearer <token>  (optional)

{"text": "Your instruction for Claude"}

→ {"response": "Response from Claude"}
```

## Requirements

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- Chrome (desktop or Android) for Web Speech API

## License

MIT
