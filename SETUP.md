# VoxGate Setup

Installation, configuration and operation. For what VoxGate *does* see
[`README.md`](README.md). For development workflow see
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Quick start (Docker)

```bash
git clone git@github.com:gzuercher/vox-gate.git
cd vox-gate
cp .env.example .env
# Edit .env — at minimum set API_TOKEN and one backend
docker compose up -d
```

VoxGate listens on `http://localhost:8000`.

> ⚠️ The server refuses to start when a backend (`ANTHROPIC_API_KEY` or
> `TARGET_URL`) is configured but `API_TOKEN` is empty. Generate one with
> `openssl rand -hex 32`. For local development only, `VOXGATE_ALLOW_OPEN=1`
> bypasses the check.

## Configuration

Everything is configured via environment variables. With Docker, put them
in `.env` (the compose file reads it automatically via `env_file`).

### Required

| Variable | Description |
|---|---|
| `API_TOKEN` | Bearer token clients must send. Without it the server refuses to start once a backend is configured. |

Plus at least one backend:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic key — enables `/claude` (direct Claude with session history). |
| `TARGET_URL` | Custom HTTP backend URL — enables `/prompt` (stateless forwarding). |

### Branding

| Variable | Default | Description |
|---|---|---|
| `INSTANCE_NAME` | `VoxGate` | Name shown in the UI header. |
| `INSTANCE_COLOR` | `#c8ff00` | Accent color (hex). |
| `SPEECH_LANG` | `de-CH` | Default language (Web Speech API). |

### Tuning

| Variable | Default | Description |
|---|---|---|
| `SYSTEM_PROMPT` | *helpful assistant…* | System prompt for `/claude`. |
| `CLAUDE_MODEL` | `claude-sonnet-4-5` | Anthropic model ID. |
| `TARGET_TOKEN` | *(empty)* | Bearer token forwarded to `TARGET_URL`. |
| `MAX_PROMPT_LENGTH` | `4000` | Maximum text length. |
| `REQUEST_TIMEOUT` | `120` | Outbound request timeout (seconds). |
| `ALLOWED_ORIGIN` | *(empty, blocked)* | Allowed CORS origin. |
| `RATE_LIMIT_PER_MINUTE` | `30` | Requests per IP per minute for `/claude` and `/prompt`. |
| `SESSION_TTL_SECONDS` | `1800` | Lifetime of an idle session. |
| `MAX_SESSIONS` | `1000` | Global cap on concurrent sessions. |
| `TRUST_PROXY_HEADERS` | `0` | Set to `1` behind Caddy/Nginx (X-Forwarded-For). See HTTPS section. |
| `VOXGATE_ALLOW_OPEN` | *(empty)* | Set to `1` to bypass the fail-loud check (development only). |

## HTTPS (mandatory for Web Speech API on Android)

Caddy with automatic certificates:

```
# Caddyfile
voxgate.example.com {
  reverse_proxy localhost:8000
}
```

```bash
apt install caddy
caddy run --config /etc/caddy/Caddyfile
```

Caddy sets `X-Forwarded-For` automatically. To make rate limiting use
the real client IP, also set in `.env`:

```bash
TRUST_PROXY_HEADERS=1
```

> ⚠️ Only enable `TRUST_PROXY_HEADERS=1` when the server is reachable
> **only** through the proxy. Otherwise clients can spoof
> `X-Forwarded-For` and bypass rate limiting.
>
> ⚠️ Do not add a CSP header in Caddy — VoxGate sets its own and a
> duplicate would either be merged confusingly or override the strict one.

## Multi-instance (advanced)

Several VoxGate instances on the same host — for example a green PWA
"Claude" (direct Anthropic) and a blue PWA "Dokbot" (forwards to a
custom backend). Each instance is its own container with its own port,
env vars and PWA icon.

Replace the single-service `docker-compose.yml` with one block per
instance, e.g.:

```yaml
services:
  claude:
    build: .
    ports:
      - "8001:8000"
    environment:
      - INSTANCE_NAME=Claude
      - INSTANCE_COLOR=#c8ff00
      - SPEECH_LANG=de-CH
      - API_TOKEN=${API_TOKEN_CLAUDE}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SYSTEM_PROMPT=${SYSTEM_PROMPT_CLAUDE:-}
      - ALLOWED_ORIGIN=${ALLOWED_ORIGIN_CLAUDE:-}
      - TRUST_PROXY_HEADERS=1
    restart: unless-stopped

  dokbot:
    build: .
    ports:
      - "8002:8000"
    environment:
      - INSTANCE_NAME=Dokbot
      - INSTANCE_COLOR=#00b4d8
      - SPEECH_LANG=de-CH
      - API_TOKEN=${API_TOKEN_DOKBOT}
      - TARGET_URL=${TARGET_URL_DOKBOT:-http://host.docker.internal:9001/prompt}
      - TARGET_TOKEN=${TARGET_TOKEN_DOKBOT:-}
      - ALLOWED_ORIGIN=${ALLOWED_ORIGIN_DOKBOT:-}
      - TRUST_PROXY_HEADERS=1
    restart: unless-stopped
```

Add a Caddy block per host (`claude.example.com`, `dokbot.example.com`)
and install each URL on the phone separately — every host becomes its
own PWA with its own color and icon.

## Direct (without Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

export API_TOKEN="your-long-random-token"
export ANTHROPIC_API_KEY="sk-ant-..."
export INSTANCE_NAME="VoxGate"
export ALLOWED_ORIGIN="https://voxgate.example.com"

uvicorn server:app --host 127.0.0.1 --port 8000
# Do not pass --workers N — see "Scaling" below.
```

## Systemd

```ini
# /etc/systemd/system/voxgate.service
[Unit]
Description=VoxGate
After=network.target

[Service]
WorkingDirectory=/opt/voxgate
EnvironmentFile=/opt/voxgate/.env
ExecStart=/opt/voxgate/.venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now voxgate
journalctl -u voxgate -f
```

For multiple instances, copy the unit (`voxgate-claude.service`,
`voxgate-dokbot.service`) with one `EnvironmentFile` and port per copy.

## Custom backend for `/prompt`

Any HTTP service that fulfills this contract works as a target:

```
POST <TARGET_URL>
Content-Type: application/json
Authorization: Bearer <TARGET_TOKEN>     # if TARGET_TOKEN is set

{"text": "voice input text"}
→ {"response": "answer"}
```

### Example: Claude Code wrapper

A minimal backend that invokes the Claude Code CLI:

```python
from fastapi import FastAPI
from pydantic import BaseModel
import subprocess

app = FastAPI()

class Req(BaseModel):
    text: str

@app.post("/prompt")
async def prompt(req: Req):
    result = subprocess.run(
        ["claude", "-p", req.text],
        capture_output=True, text=True, timeout=120,
    )
    return {"response": result.stdout.strip()}
```

Runs on the machine where Claude Code is installed (e.g. your Mac).
VoxGate runs on the server and forwards to it.

## Security

Operator-Checkliste vor dem Public-Deploy: [`SECURITY.md`](SECURITY.md).

## Scaling & deployment constraints

**VoxGate must run with exactly one Uvicorn worker per process.** The
`/claude` endpoint keeps conversation history per `session_id` in an
in-memory dict. Each worker process has its own copy — requests routed
to different workers see different (or empty) histories. Users would
experience sporadic "memory loss" mid-conversation.

The shipped `Dockerfile` and `docker-compose.yml` start a single worker
— out of the box this is fine.

### Why scale at all?

Three typical motives — none of them currently pressing for VoxGate:

1. **CPU utilization.** Python's GIL limits one process to one CPU core.
   Multiple workers can use multiple cores. Not relevant here: the
   server is I/O-bound (it just waits for the Anthropic API).
2. **Throughput / concurrent users.** Many simultaneously active
   sessions could saturate one worker. A personal or family-sized
   installation will never hit this.
3. **High availability.** Multiple containers behind a load balancer
   survive the loss of any single instance.

### Implications

- Do **not** set `--workers N` (N > 1) on `uvicorn`.
- Do **not** put multiple VoxGate containers behind a load balancer
  with `/claude` enabled, unless sticky sessions are configured.
- Histories are lost on container restart — intentional for a
  lightweight install.
- `/prompt` is stateless and unaffected.

### Migration path (if scaling becomes necessary)

Move the `_sessions` dict out of process memory into a shared store —
Redis is the standard choice. Adds a dependency and requires reworking
`server.py`.

## Maintenance

- **Logs:** `docker compose logs -f` or `journalctl -u voxgate -f`
- **Update:** `git pull && docker compose build && docker compose up -d`
- **Sessions:** kept in memory; lost on restart. Intentional.
- **Anthropic costs:** monitor at console.anthropic.com, set spending limits.
