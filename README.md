# VoxGate

**Talk to Claude (or another chatbot) by voice — straight from your phone.**

VoxGate is a small web app you install on your phone home screen like a
native app. Tap the mic, speak, and hear the answer read back to you.
Works in Swiss German and Swiss French.

## Was willst du tun?

### A) Mit Claude per Stimme reden — eigene (Sub-)Domain

Empfohlener Pfad. Du brauchst eine Subdomain, die auf deinen Server
zeigt, und einen Anthropic-API-Key.

```bash
git clone git@github.com:gzuercher/vox-gate.git
cd vox-gate/deploy/caddy
cp .env.example .env
# eintragen: VOXGATE_DOMAIN, ACME_EMAIL, ANTHROPIC_API_KEY
docker compose up -d
```

Caddy holt automatisch ein Lets-Encrypt-Zertifikat. Details:
[`deploy/caddy/README.md`](deploy/caddy/README.md).

### B) Eigenen Bot per Stimme erreichen (z.B. einen Planer)

Gleicher Aufbau wie A, aber statt `ANTHROPIC_API_KEY` setzt du eine
`TARGET_URL`, die auf dein Backend zeigt. Dein Backend muss einen
einfachen HTTP-Vertrag erfuellen — siehe
[`docs/backends.md`](docs/backends.md).

### C) Auf bestehender Reverse-Proxy-Infra (Traefik, Kubernetes, nginx)

Nutze das Root-`docker-compose.yml`. Es bringt nur den VoxGate-Container
mit; Cert-Handling und Hostname-Routing macht deine Infra. Hinweise:
[`SETUP.md`](SETUP.md#reverse-proxy-anleitung).

### D) Ohne eigene Domain (Cloudflare Tunnel / Tailscale Funnel)

VoxGate laesst sich problemlos hinter einen Tunnel haengen — Cloudflare
oder Tailscale stellen das HTTPS und einen Hostnamen. Konzept und
Pointer auf die offiziellen Setups: [`SETUP.md`](SETUP.md#tunnel-davorhaengen).

---

## Using the app

After installing the PWA on your home screen, open it:

| Element | Function |
|---|---|
| **Mic button (large)** | Tap to start recording. Tap again to send. |
| **Language (top left)** | Switch between `DE-CH` and `FR-CH`. Persisted. |
| **Speaker (top right)** | Mute/unmute speech output. |
| **Status dot (top right)** | Green = ready, blinking = sending, red = error. |
| **New conversation (bottom)** | Reset the conversation history. |

Replies are read aloud automatically unless muted. If you tap the mic
again while audio is playing, the current speech is cancelled.

### Requirements

- **Browser:** Chrome on Android or desktop (Web Speech API).
  Safari/iOS support is limited.
- **Microphone permission** must be granted on first launch.
- **HTTPS** is mandatory on Android — solved by Caddy/Tunnel above.

## Installing the PWA on your phone

1. Open Chrome on Android → `https://your-voxgate-host`.
2. Three-dot menu → "Add to Home screen".
3. The app now opens like any other app, with its own icon and color.

If you deploy multiple instances on different hostnames, repeat for
each — every URL becomes its own PWA with its own color.

## Troubleshooting

| Problem | What to do |
|---|---|
| Mic doesn't react | Grant permission in the browser. On Android the page must be HTTPS. |
| No speech output | Check the speaker button. iOS has limited Web Speech support. |
| `401` error | Bearer token missing or wrong — see operator/.env. |
| `429` error | Rate limit hit. Wait and retry. |
| `503` on `/claude` | Anthropic backend not configured — set `ANTHROPIC_API_KEY`. |
| Conversation suddenly "forgets" | Server restart — sessions are in-memory by design. |
| Doesn't work on Safari/iOS | Web Speech API is limited there; use Chrome. |

---

The rest is reference material for developers and clients calling the
HTTP API. For installation/operation see [`SETUP.md`](SETUP.md). For
security checklist see [`SECURITY.md`](SECURITY.md). For backend
examples see [`docs/backends.md`](docs/backends.md). For contributing
see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Architecture

```
┌─────────────┐                             ┌──────────────────┐
│  PWA        │     POST /claude            │                  │     Anthropic API
│  (phone     │  ────────────────────────►  │  VoxGate server  │  ────────────────────►  Claude
│  home       │  ◄────────────────────────  │  (FastAPI)       │  ◄────────────────────  (claude-sonnet-4-5)
│  screen)    │                             │                  │
│             │     POST /prompt            │                  │     POST TARGET_URL
│             │  ────────────────────────►  │                  │  ────────────────────►  Custom backend
│             │  ◄────────────────────────  │                  │  ◄────────────────────  (e.g. zursetti-planner)
└─────────────┘                             └──────────────────┘
```

The server exposes two endpoints:

- **`/claude`** — calls the Anthropic API directly. Keeps conversation
  history per session. Uses `ANTHROPIC_API_KEY`.
- **`/prompt`** — forwards to a custom backend (`TARGET_URL`).
  Stateless. Voice gateway for any chatbot service.

## API reference

### `POST /claude`

```json
POST /claude
Authorization: Bearer <API_TOKEN>
Content-Type: application/json

{
  "text": "What time is it in Tokyo?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Response: `{ "response": "Currently it's …" }`

`session_id` must match `^[A-Za-z0-9_-]{8,128}$`. Up to 20 messages
per session are kept in memory; older ones are dropped in pairs.

### `POST /prompt`

```json
POST /prompt
Authorization: Bearer <API_TOKEN>
Content-Type: application/json

{ "text": "Hello backend" }
```

VoxGate forwards to `TARGET_URL` and expects JSON with a `response`
(or `text`) field back.

### `GET /config`

Returns instance configuration for the PWA. No auth.

```json
{ "name": "Claude", "color": "#c8ff00", "lang": "de-CH", "maxLength": 4000 }
```

### Errors

| Code | Meaning |
|---|---|
| 401 | Token missing or wrong |
| 422 | Validation failed |
| 429 | Rate limit exceeded |
| 502 | Backend error |
| 503 | Backend not configured |

## File structure

```
voxgate/
├── server.py              # FastAPI gateway (/claude, /prompt, /config)
├── pwa/                   # PWA (HTML, JS, CSS, manifest, service worker)
├── tests/                 # pytest tests
├── deploy/
│   └── caddy/             # Bundled Caddy + VoxGate (recommended path)
├── docs/
│   └── backends.md        # /prompt and /claude examples
├── .claude/rules/         # Code rules for Claude Code
├── .env.example           # Configuration template (api-only, root)
├── docker-compose.yml     # api-only (no proxy bundled)
├── Dockerfile
├── pyproject.toml
├── Makefile               # make setup/run/test/lint
├── README.md              # This file
├── SETUP.md               # Installation and operation
├── SECURITY.md            # Operator checklist
├── CONTRIBUTING.md        # Development workflow
├── CLAUDE.md              # Playbook for Claude Code
└── lessons.md             # Lessons learned
```

## License

MIT
