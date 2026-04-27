# Security checklist

Walk through this checklist point by point before going public. Every
item should be answerable with yes/no without reading source code.

## Before the first public deploy

- [ ] **`API_TOKEN` is set explicitly in `.env`.** Otherwise VoxGate
      generates a fresh token on every container start (fine for dev,
      bad for production — PWA clients lose access on each restart).
- [ ] **`ANTHROPIC_API_KEY` has a spending limit.** Set it in the
      Anthropic console dashboard so token leaks are bounded by cost.
- [ ] **`ALLOWED_ORIGIN` points at the real domain.** Empty = no
      browser origin may call the API. Wildcards (`*` etc.) are
      intentionally not supported.
- [ ] **`TRUST_PROXY_HEADERS=1` only when the server is reachable
      exclusively through the reverse proxy.** Otherwise clients can
      spoof `X-Forwarded-For` and bypass rate limiting. Inside the
      `deploy/caddy/` bundle this is automatically the case.
- [ ] **`RATE_LIMIT_PER_MINUTE` chosen deliberately.** Default 30 is
      fine for one person; raise it for a family. Too high = no
      protection against bot abuse.

## Backend-specific

### When `ANTHROPIC_API_KEY` is active (`/claude`)

- [ ] **API-key rotation:** the key is cached on the first `/claude`
      call. Restart the container after rotation.
- [ ] **`SYSTEM_PROMPT` contains no secrets.** It lives in plain text
      inside the container — and anyone with access to `/config` or
      logs can see it.

### When `TARGET_URL` is active (`/prompt`)

- [ ] **Target backend binds to `127.0.0.1`** or requires its own
      `TARGET_TOKEN`. Otherwise VoxGate inadvertently exposes your
      backend to the internet.
- [ ] **Target backend has its own backups.** VoxGate has no state
      worth backing up; the target backend may.

## During operation

- [ ] **Logs are reviewed.** `docker compose logs -f voxgate` shows
      audit entries with IP, session prefix and text length (no
      payload). 429s and backend errors too.
- [ ] **No additional `Content-Security-Policy` in the reverse
      proxy.** VoxGate sets a strict CSP itself. A second directive
      in Caddy/nginx collides.
- [ ] **Updates are checked.** `git pull && docker compose build &&
      docker compose up -d` regularly — especially after security
      releases.

## What VoxGate brings out of the box

Active without any operator action:

- Token requirement on `/prompt` and `/claude`. Auto-generation when
  empty (no "open mode").
- Timing-safe token comparison (`secrets.compare_digest`).
- Per-IP rate limit on both endpoints.
- Session TTL and a global session cap (memory DoS protection).
- Strict `session_id` validation (`^[A-Za-z0-9_-]{8,128}$`).
- Strict CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options:
  nosniff`, `Referrer-Policy`, `Permissions-Policy` (microphone only).
- Audit log without payload.
- CORS blocked by default.

## Optional: edge-level pre-auth for closed groups

VoxGate's bearer-token check is cryptographically sufficient — without
the token nobody can run prompts or hit your `/prompt` backend. For a
closed group of users (family, small team) you may still want to hide
the instance from random visitors of the URL. That is independent of
VoxGate and lives one layer up:

- **HTTP Basic Auth in Caddy/nginx.** Add a `basicauth` block in front
  of VoxGate. Users see the browser's auth dialog before the PWA
  loads. Credentials persist across PWA installs.
- **Cloudflare Access** in front of a Cloudflare Tunnel. Magic-link
  email login at the edge; no code changes inside VoxGate. Free tier
  covers small groups.
- **Tailnet-only**: run VoxGate behind Tailscale and skip Funnel.
  Only members of your tailnet can reach the URL at all.

In all three cases, VoxGate's `API_TOKEN` still applies inside —
defence in depth, not a replacement.

## Residual risks

- **localStorage XSS:** the bearer token lives in browser
  `localStorage`. CSP blocks inline scripts; any future use of
  `innerHTML` with server data must be very careful.
- **In-memory sessions:** histories live in the process. Restarts
  drop them. Intentional.
- **Per-IP rate limit only:** behind NAT/CGNAT users share the quota.
