# VoxGate setup

Installation, configuration, and operation. For what VoxGate *does* see
[`../README.md`](../README.md). For development workflow see
[`contributing.md`](contributing.md). For the operator security
checklist see [`security.md`](security.md). For the JSON contract
between VoxGate and your backend see
[`integration.md`](integration.md). For example backend
implementations see [`backends.md`](backends.md).

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
# Required: GOOGLE_CLIENT_ID, ALLOWED_EMAILS, TARGET_URL.
docker compose up -d
```

VoxGate listens on `http://localhost:8000`. Login uses Google Sign-In;
only e-mails listed in `ALLOWED_EMAILS` may sign in. If `SESSION_SECRET`
is left empty, the server generates one on startup — for production set
a stable value so sessions survive restarts.

## Configuration

Everything is configured via environment variables. With Docker, put
them in `.env` (Compose reads it via `env_file`).

### Required (auth)

| Variable | Description |
|---|---|
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client ID from Google Cloud Console. Without it, no one can log in. |
| `ALLOWED_EMAILS` | Comma-separated list of permitted e-mail addresses. Optional `:provider` suffix per entry, e.g. `alice@example.com:google`. Without a suffix, every configured provider is acceptable. |
| `SESSION_SECRET` | Server-side key used to sign session cookies. Generate with `openssl rand -hex 32`. If empty, auto-generated per-run (sessions die on restart). |
| `SESSION_COOKIE_TTL_SECONDS` | Lifetime of a login session. Default `604800` (7 days). |
| `COOKIE_SECURE` | `1` in production (HTTPS). `0` for local http development. |

#### How requests authenticate (CSRF model)

After `POST /auth/login/{provider}` succeeds, the server sets two
cookies on the response:

- `vg_session` — HttpOnly, signed (`itsdangerous` + `SESSION_SECRET`),
  carries `{email, provider, subject, csrf, exp}`. Only the server
  reads it.
- `vg_csrf` — readable from JavaScript. The PWA copies its value into
  an `X-CSRF-Token` header on every state-changing request
  (`POST /chat`, `POST /auth/logout`).

The server's `verify_session` dependency requires that the
`X-CSRF-Token` header equals the `vg_csrf` cookie *and* that both
equal the csrf value bound inside the signed session blob. This is the
standard double-submit pattern, hardened with a session-internal
binding so an attacker cannot plant a fresh `vg_csrf` cookie in a
sibling subdomain attack and still hit a logged-in endpoint. Login and
logout are additionally Origin-checked when `ALLOWED_ORIGIN` is set.

For programmatic clients, see the curl example in
[`backends.md`](backends.md) — log in once, persist cookies, copy the
`vg_csrf` value into a header on subsequent calls.

#### Setting up the Google OAuth Client

1. Open the [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials) page.
2. Create a new OAuth 2.0 Client ID, type **Web application**.
3. Under **Authorized JavaScript origins**, add the URL(s) where the PWA is served (e.g. `https://voxgate.example.com`). For local development add `http://localhost:8000`.
4. **Authorized redirect URIs** are not needed — the PWA uses Google Identity Services (popup/credential flow), not a server-side redirect.
5. Copy the resulting Client ID into `GOOGLE_CLIENT_ID`.

The same Client ID can serve every VoxGate instance — just add each
domain to **Authorized JavaScript origins**.

### Required (backend)

| Variable | Description |
|---|---|
| `TARGET_URL` | URL of the chat backend. VoxGate POSTs the strict JSON contract here for every authenticated `/chat` request. Without it, `/chat` returns `503`. See [`integration.md`](integration.md). |
| `TARGET_TOKEN` | Optional bearer token added as `Authorization: Bearer <token>` on the forwarded request. Leave empty if the backend needs no auth. |

VoxGate has no built-in LLM client. If you want voice-to-Claude (or
voice-to-OpenAI, voice-to-anything), run a small adapter container
that exposes a single endpoint speaking the
[backend contract](integration.md) and forwards on to the model
provider.

### Branding

| Variable | Default | Description |
|---|---|---|
| `INSTANCE_NAME` | `VoxGate` | Technical identifier of the instance. Used in logs and forwarded to the backend as `metadata.instance` so one backend can serve multiple frontends. |
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
| `MAX_PROMPT_LENGTH` | `4000` | Maximum text length per request. |
| `REQUEST_TIMEOUT` | `120` | Outbound request timeout to TARGET_URL (seconds). |
| `ALLOWED_ORIGIN` | *(empty, blocked)* | Allowed CORS origin. |
| `RATE_LIMIT_PER_MINUTE` | `30` | Requests per IP per minute for `/chat`. |
| `AUTH_LOGIN_RATE_LIMIT_PER_MINUTE` | `10` | Requests per IP per minute for `/auth/login/*`. |
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
- In `.env`: `COOKIE_SECURE=1` (required for browsers to keep the
  session cookie over HTTPS).
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
"Family planner" pointing at one backend and a blue PWA "Recipe bot"
pointing at another. Each instance is its own container with its own
port, env vars, and PWA icon.

**This is for distinct backends or distinct user groups, not for
multiple human languages.** Speech recognition language, TTS voice and
UI text all switch through the in-app language picker — running one
instance per language is unnecessary duplication.

Replace the single-service `docker-compose.yml` with one block per
instance, e.g.:

```yaml
services:
  planner:
    build: .
    ports:
      - "8001:8000"
    environment:
      - INSTANCE_NAME=Planner
      - INSTANCE_COLOR=#c8ff00
      - SPEECH_LANG=de-CH
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - ALLOWED_EMAILS=${ALLOWED_EMAILS_PLANNER}
      - SESSION_SECRET=${SESSION_SECRET_PLANNER}
      - COOKIE_SECURE=1
      - TARGET_URL=${TARGET_URL_PLANNER}
      - TARGET_TOKEN=${TARGET_TOKEN_PLANNER:-}
      - ALLOWED_ORIGIN=${ALLOWED_ORIGIN_PLANNER:-}
      - TRUST_PROXY_HEADERS=1
    restart: unless-stopped

  recipes:
    build: .
    ports:
      - "8002:8000"
    environment:
      - INSTANCE_NAME=Recipes
      - INSTANCE_COLOR=#00b4d8
      - SPEECH_LANG=de-CH
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - ALLOWED_EMAILS=${ALLOWED_EMAILS_RECIPES}
      - SESSION_SECRET=${SESSION_SECRET_RECIPES}
      - COOKIE_SECURE=1
      - TARGET_URL=${TARGET_URL_RECIPES}
      - TARGET_TOKEN=${TARGET_TOKEN_RECIPES:-}
      - ALLOWED_ORIGIN=${ALLOWED_ORIGIN_RECIPES:-}
      - TRUST_PROXY_HEADERS=1
    restart: unless-stopped
```

Add a Caddy block per host (`planner.example.com`, `recipes.example.com`)
and install each URL on the phone separately — every host becomes its
own PWA with its own color and icon.

## Direct (without Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

export GOOGLE_CLIENT_ID="123-abc.apps.googleusercontent.com"
export ALLOWED_EMAILS="you@example.com"
export SESSION_SECRET="$(openssl rand -hex 32)"
export TARGET_URL="http://localhost:9000/"
export INSTANCE_NAME="VoxGate"
export ALLOWED_ORIGIN="https://voxgate.example.com"

uvicorn server:app --host 127.0.0.1 --port 8000
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

For multiple instances, copy the unit (`voxgate-planner.service`,
`voxgate-recipes.service`) with one `EnvironmentFile` and port per copy.

## Custom backend for `/chat`

Backend contract (strict): [`integration.md`](integration.md).
Example implementations (Python/FastAPI, Node/Express, bash stub,
adapter to Anthropic): [`backends.md`](backends.md).

## Security

Operator checklist before the public deploy: [`security.md`](security.md).

## Scaling notes

VoxGate itself is **stateless** — it carries no per-user data between
requests. Sessions live in signed cookies; everything else is
forwarded to the backend. You can run multiple containers behind a
load balancer without sticky sessions.

The single-process `Dockerfile` and `docker-compose.yml` are the
default. Add `--workers N` to `uvicorn` if you need more throughput;
the backend at TARGET_URL is the more likely bottleneck.

## Maintenance

- **Logs:** `docker compose logs -f` or `journalctl -u voxgate -f`
- **Update:** `git pull && docker compose build && docker compose up -d`
- **Sessions:** signed cookies, no server-side state. Restart-safe.
- **Backend costs/limits:** that is the backend's problem now — VoxGate
  doesn't know about model pricing.
