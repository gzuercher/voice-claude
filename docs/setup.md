# VoxGate setup

Installation, configuration, and operation. For what VoxGate *does* see
[`../README.md`](../README.md). For development workflow see
[`contributing.md`](contributing.md). For the operator security
checklist see [`security.md`](security.md). For backend examples see
[`backends.md`](backends.md).

## Which variant?

| Variant | When to use | Doc |
|---|---|---|
| **Caddy bundle** | Own (sub-)domain, server with free ports 80/443 | [`../deploy/caddy/README.md`](../deploy/caddy/README.md) |
| **API-only (root compose)** | Existing reverse-proxy infra (Traefik, k8s, nginx) | below, "Reverse proxy" |
| **Tunnel in front** | No domain of your own | below, "Tunnel in front" |
| **Direct (without Docker)** | Local development | below, "Direct (without Docker)" |

## Quick start (root compose, api-only)

```bash
git clone git@github.com:gzuercher/vox-gate.git
cd vox-gate
cp .env.example .env
# Optional: set API_TOKEN, ANTHROPIC_API_KEY, or TARGET_URL
docker compose up -d
```

VoxGate listens on `http://localhost:8000`. If `API_TOKEN` is left
empty, the server generates one on startup and logs it — for production
set a stable value.

## Configuration

Everything is configured via environment variables. With Docker, put
them in `.env` (Compose reads it via `env_file`).

### Required

| Variable | Description |
|---|---|
| `API_TOKEN` | Bearer token clients must send. If empty, the server auto-generates one on startup and logs it (per-run). |

Plus at least one backend:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic key — enables `/claude` (direct Claude with session history). |
| `TARGET_URL` | Custom HTTP backend URL — enables `/prompt` (stateless forwarding). |

### Branding

| Variable | Default | Description |
|---|---|---|
| `INSTANCE_NAME` | `VoxGate` | Technical identifier of the instance. Used in logs and as a fallback for the UI title. |
| `INSTANCE_DISPLAY_NAME` | *(empty → falls back to `INSTANCE_NAME`)* | Human-friendly title shown in the header and browser tab. Set this to a readable name (e.g. `"ZPlanner Voice"`). |
| `INSTANCE_COLOR` | `#c8ff00` | Accent color (hex). Drives focus rings, status dot, active borders. |
| `SPEECH_LANG` | `de-CH` | Default language tag (BCP-47). Initial selection if the visitor has no stored preference and the browser/OS language is not in `SPEECH_LANGS`. |
| `SPEECH_LANGS` | `de-CH,fr-CH,it-CH,en-US,es-ES` | Comma-separated list of selectable languages. The PWA renders a picker in the header; the choice drives speech recognition, TTS *and* the UI text. The first visit auto-detects from `navigator.languages`, then persists the user's choice in `localStorage`. |

### Debug capture (off by default)

| Variable | Default | Description |
|---|---|---|
| `DEBUG_ENABLED` | `0` | Master switch for the `/debug-log` endpoint. When `0`, the endpoint returns `404` and its existence stays hidden. |
| `DEBUG_TOKEN` | *(empty)* | Shared secret. The PWA must present it as `X-Debug-Token` for `/debug-log` to accept events. Leave empty to disable. |

When both are set, opening the PWA at `?debug=<token>` activates an
in-browser overlay that streams SpeechRecognition / state events to the
server. Events appear in `docker logs <container>` prefixed with `DEBUG`,
with rate-limit and 8 KiB body cap. Intended for short, opt-in debugging
sessions — flip back to `DEBUG_ENABLED=0` when done.

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
| `TRUST_PROXY_HEADERS` | `0` | Set to `1` behind Caddy/Nginx (X-Forwarded-For). See "Reverse proxy". |

## Reverse proxy

Web Speech API requires HTTPS on Android. Three paths:

1. **Caddy bundle** — preconfigured in [`../deploy/caddy/`](../deploy/caddy/).
   Recommended if you have nothing else running.
2. **Your own Caddy/nginx** in front of the root compose — see below.
3. **Tunnel** instead of a proxy — see the next section.

Prerequisites for variant 2:

- Server with free ports 80/443 (or different ones if your proxy
  listens elsewhere).
- DNS A/AAAA record for the chosen hostname pointing at the server.
- Firewall (e.g. UFW): 80, 443 open; 8000 *not* reachable from outside.

### Caddy (manual install)

```caddy
# /etc/caddy/Caddyfile
voxgate.example.com {
    reverse_proxy localhost:8000
}
```

```bash
apt install caddy
systemctl enable --now caddy
```

Caddy obtains and renews the certificate automatically.

### Nginx

```nginx
# /etc/nginx/sites-available/voxgate
server {
    listen 443 ssl http2;
    server_name voxgate.example.com;

    ssl_certificate     /etc/letsencrypt/live/voxgate.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/voxgate.example.com/privkey.pem;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name voxgate.example.com;
    return 301 https://$host$request_uri;
}
```

Cert renewal via certbot (`certbot --nginx -d voxgate.example.com`).
Cron/timer checks every 12 h.

### Important for both

- In `.env`: `TRUST_PROXY_HEADERS=1` (so the rate limit applies to the
  real client IP rather than the proxy IP).
- In `.env`: `ALLOWED_ORIGIN=https://voxgate.example.com`.
- **Do not** add a `Content-Security-Policy` header in the proxy —
  VoxGate sets a strict CSP itself.

## Tunnel in front

If you do not have your own domain (or do not want to open ports), put
VoxGate behind a tunnel service. HTTPS and the hostname come from the
tunnel provider.

```
[Phone] ──HTTPS──► [Tunnel provider] ──► [VoxGate on 127.0.0.1:8000]
```

VoxGate itself does not change — the tunnel points at `localhost:8000`,
just like a local reverse proxy.

### Cloudflare Tunnel

```bash
# one-time setup
cloudflared tunnel login
cloudflared tunnel create voxgate
# route a subdomain through the tunnel
cloudflared tunnel route dns voxgate voxgate.example.com
# run the tunnel — VoxGate must listen on 127.0.0.1:8000
cloudflared tunnel run --url http://localhost:8000 voxgate
```

Setup docs: <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/>.

In `.env`: `TRUST_PROXY_HEADERS=1` and `ALLOWED_ORIGIN=https://voxgate.example.com`.

### Tailscale Funnel

```bash
tailscale up
tailscale serve https / http://localhost:8000
tailscale funnel 443 on
```

Setup docs: <https://tailscale.com/kb/1223/funnel>.

In `.env`: `TRUST_PROXY_HEADERS=1` and
`ALLOWED_ORIGIN=https://<machine>.<tailnet>.ts.net`.

## Multi-instance (advanced)

Several VoxGate instances on the same host — for example a green PWA
"Claude" (direct Anthropic) and a blue PWA "Dokbot" (forwards to a
custom backend). Each instance is its own container with its own port,
env vars, and PWA icon.

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

Backend contract and examples (Python/FastAPI with Claude CLI,
Node/Express, bash stub, browser client): [`backends.md`](backends.md).

## Security

Operator checklist before the public deploy: [`security.md`](security.md).

## Scaling & deployment constraints

**VoxGate must run with exactly one Uvicorn worker per process.** The
`/claude` endpoint keeps conversation history per `session_id` in an
in-memory dict. Each worker process has its own copy — requests routed
to different workers see different (or empty) histories. Users would
experience sporadic "memory loss" mid-conversation.

The shipped `Dockerfile` and `docker-compose.yml` start a single worker
— out of the box this is fine.

### Why scale at all?

Three typical motives — none currently pressing for VoxGate:

1. **CPU utilization.** Python's GIL limits one process to one CPU
   core. Multiple workers can use multiple cores. Not relevant here:
   the server is I/O-bound (it just waits for the Anthropic API).
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
- **Anthropic costs:** monitor at console.anthropic.com; set spending limits.
