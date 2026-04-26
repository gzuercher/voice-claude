# VoxGate Setup

Installation, configuration and operation. For what VoxGate *does* see
[`README.md`](README.md). For development workflow see
[`CONTRIBUTING.md`](CONTRIBUTING.md). For the operator security checklist
see [`SECURITY.md`](SECURITY.md). For backend examples see
[`docs/backends.md`](docs/backends.md).

## Welche Variante?

| Variante | Wann | Doku |
|---|---|---|
| **Caddy-Bundle** | Eigene (Sub-)Domain, Server mit freien Ports 80/443 | [`deploy/caddy/README.md`](deploy/caddy/README.md) |
| **API-only (Root-Compose)** | Eigene Reverse-Proxy-Infra (Traefik, k8s, nginx) | unten, "Reverse-Proxy-Anleitung" |
| **Tunnel davorhaengen** | Keine eigene Domain | unten, "Tunnel davorhaengen" |
| **Direct (ohne Docker)** | Lokale Entwicklung | unten, "Direct (without Docker)" |

## Quick start (Root-Compose, api-only)

```bash
git clone git@github.com:gzuercher/vox-gate.git
cd vox-gate
cp .env.example .env
# Optional: API_TOKEN, ANTHROPIC_API_KEY oder TARGET_URL setzen
docker compose up -d
```

VoxGate listens on `http://localhost:8000`. Wenn `API_TOKEN` leer
bleibt, generiert der Server beim Start einen und loggt ihn — fuer
Produktion solltest du einen festen Wert setzen.

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
| `TRUST_PROXY_HEADERS` | `0` | Set to `1` behind Caddy/Nginx (X-Forwarded-For). See Reverse-Proxy section. |

## Reverse-Proxy-Anleitung

Web Speech API verlangt HTTPS auf Android. Drei Wege:

1. **Caddy-Bundle** — fertig konfiguriert in [`deploy/caddy/`](deploy/caddy/).
   Empfohlen, wenn du nichts anderes laufen hast.
2. **Eigenes Caddy/Nginx** vor dem Root-Compose — siehe unten.
3. **Tunnel** statt eigenem Proxy — siehe naechster Abschnitt.

Voraussetzungen fuer Variante 2:

- Server mit freien Ports 80/443 (oder anderen, wenn der Proxy auf
  anderen Ports lauscht).
- DNS A/AAAA-Eintrag fuer den gewuenschten Hostname auf den Server.
- Firewall (z.B. UFW): 80, 443 offen, 8000 *nicht* von aussen erreichbar.

### Caddy (eigene Installation)

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

Caddy holt das Zertifikat automatisch und erneuert es selbststaendig.

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

Zertifikat-Renewal mit certbot (`certbot --nginx -d voxgate.example.com`).
Cron/Timer prueft alle 12 h.

### Wichtig fuer beide

- In `.env` setzen: `TRUST_PROXY_HEADERS=1` (damit das Rate-Limit auf
  die echte Client-IP statt auf die Proxy-IP angewendet wird).
- In `.env` setzen: `ALLOWED_ORIGIN=https://voxgate.example.com`.
- **Keine** zusaetzliche `Content-Security-Policy` im Proxy — VoxGate
  setzt eine strikte CSP selbst.

## Tunnel davorhaengen

Wenn du keine eigene Domain hast (oder keine Ports oeffnen willst),
kannst du VoxGate hinter einen Tunnel-Service haengen. Das HTTPS und der
Hostname kommen vom Tunnel-Anbieter.

```
[Phone] ──HTTPS──► [Tunnel-Anbieter] ──► [VoxGate auf 127.0.0.1:8000]
```

VoxGate selbst aendert sich nicht — Tunnel zeigt auf `localhost:8000`,
genau wie ein lokaler Reverse-Proxy.

### Cloudflare Tunnel

```bash
# einmalig einrichten
cloudflared tunnel login
cloudflared tunnel create voxgate
# Subdomain auf den Tunnel routen
cloudflared tunnel route dns voxgate voxgate.example.com
# Service starten — VoxGate muss auf 127.0.0.1:8000 lauschen
cloudflared tunnel run --url http://localhost:8000 voxgate
```

Setup-Doku: <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/>.

In `.env`: `TRUST_PROXY_HEADERS=1` und `ALLOWED_ORIGIN=https://voxgate.example.com`.

### Tailscale Funnel

```bash
tailscale up
tailscale serve https / http://localhost:8000
tailscale funnel 443 on
```

Setup-Doku: <https://tailscale.com/kb/1223/funnel>.

In `.env`: `TRUST_PROXY_HEADERS=1` und
`ALLOWED_ORIGIN=https://<machine>.<tailnet>.ts.net`.

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

Backend-Vertrag und Beispiele (Python/FastAPI mit Claude-CLI,
Node/Express, Bash-Stub, Browser-Client): [`docs/backends.md`](docs/backends.md).

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
