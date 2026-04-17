# VoiceClaude

Voice gateway for your phone – speak and forward to any backend.

Each instance targets one backend (Claude Code, Dokbot, etc.) via a simple HTTP POST. Deploy multiple instances, each with its own name and color, as separate PWAs on your homescreen.

## Architecture

```
┌─────────────┐                    ┌──────────────────┐
│  PWA:       │   POST /prompt     │  VoiceClaude     │   POST TARGET_URL
│  "Claude"   │  ───────────────►  │  Container :8001 │  ───────────────►  Claude Code
│  (green)    │  ◄───────────────  │                  │  ◄───────────────  (Mac/VPS)
└─────────────┘                    └──────────────────┘

┌─────────────┐                    ┌──────────────────┐
│  PWA:       │   POST /prompt     │  VoiceClaude     │   POST TARGET_URL
│  "Dokbot"   │  ───────────────►  │  Container :8002 │  ───────────────►  Dokbot
│  (blue)     │  ◄───────────────  │                  │  ◄───────────────  (anywhere)
└─────────────┘                    └──────────────────┘
```

## 1-Click UI

- **Tap** → start recording
- **Tap again** → stop and send automatically
- No menus, no dropdowns, no second button

## Configuration

Everything is configured via environment variables. One instance = one target.

| Variable | Description | Default |
|---|---|---|
| `INSTANCE_NAME` | Name shown in the UI header | `VoiceClaude` |
| `INSTANCE_COLOR` | Accent color (hex) | `#c8ff00` |
| `SPEECH_LANG` | Web Speech API language | `de-CH` |
| `TARGET_URL` | Backend URL to forward voice text to | *(required)* |
| `TARGET_TOKEN` | Bearer token for the target backend | *(empty)* |
| `API_TOKEN` | Bearer token for this gateway | *(empty, warns)* |
| `ALLOWED_ORIGIN` | Allowed CORS origin | *(empty, blocked)* |
| `MAX_PROMPT_LENGTH` | Max text length | `4000` |
| `REQUEST_TIMEOUT` | Timeout for target requests (seconds) | `120` |

## Quick Start (local)

```bash
make setup
TARGET_URL=http://localhost:9000/prompt make run
```

## Quick Start (Docker)

```bash
docker compose up -d
```

This starts two instances by default (see `docker-compose.yml`):
- **Claude** on port 8001 (green)
- **Dokbot** on port 8002 (blue)

Edit `docker-compose.yml` to add more instances or change targets.

## Target Backend Contract

VoiceClaude sends a POST request to `TARGET_URL` with:

```json
POST <TARGET_URL>
Content-Type: application/json
Authorization: Bearer <TARGET_TOKEN>  (if set)

{"text": "the transcribed voice input"}
```

The target must return JSON. VoiceClaude displays the `response` or `text` field:

```json
{"response": "answer from the backend"}
```

Any HTTP service that accepts this contract works as a target.

## PWA on Pixel

1. Open Chrome → `https://claude.example.com` (instance 1)
2. Three-dot menu → "Add to Home screen"
3. Repeat for `https://dokbot.example.com` (instance 2)
4. Each icon on the homescreen opens a different instance

## HTTPS (required for Android)

Use Caddy as reverse proxy for automatic HTTPS:

```
# Caddyfile
claude.example.com {
    reverse_proxy localhost:8001
}
dokbot.example.com {
    reverse_proxy localhost:8002
}
```

## File Structure

```
voiceclaude/
├── server.py              # FastAPI gateway (forwards to TARGET_URL)
├── pwa/
│   ├── index.html         # 1-click voice UI
│   ├── manifest.json      # PWA manifest
│   ├── sw.js              # Service Worker
│   └── icon.svg           # App icon
├── Dockerfile             # Container image
├── docker-compose.yml     # Multi-instance setup
├── tests/
│   └── test_server.py     # pytest tests
├── pyproject.toml         # Python project config
└── Makefile               # make setup/run/test/lint
```

## Development

```bash
make setup          # create venv, install deps
make test           # run tests
make lint           # ruff linter
make format         # auto-format
make check          # lint + test
```

## Requirements

- Python 3.10+ (or Docker)
- Chrome (desktop or Android) for Web Speech API

## License

MIT
