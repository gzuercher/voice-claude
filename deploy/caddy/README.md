# VoxGate + Caddy bundle

Recommended path for self-hosting with your own (sub-)domain. Caddy
obtains the Let's Encrypt certificate automatically and reverse-proxies
to VoxGate. The VoxGate container is reachable only through Caddy.

## Prerequisites

- Server with Docker and free ports 80 and 443.
- DNS A/AAAA record for `voxgate.example.com` pointing at the server.
- No other web server on 80/443.

## Start

```bash
cd deploy/caddy
cp .env.example .env
# Required: VOXGATE_DOMAIN, ACME_EMAIL, GOOGLE_CLIENT_ID,
# ALLOWED_EMAILS, TARGET_URL.
docker compose up -d
```

On first start Caddy fetches a certificate (30-60 s). Logs:

```bash
docker compose logs -f caddy
docker compose logs -f voxgate
```

Open `https://voxgate.example.com` in the browser. The PWA shows a
**Sign in with Google** button. Use a Google account that you added to
`ALLOWED_EMAILS` in `.env`. After login you can install the PWA
("Add to Home screen").

## Customisation

- **Multiple instances** (e.g. one for the family planner, one for a
  recipe bot): copy the compose file, add a second `voxgate-*` service,
  extend the `Caddyfile` with another hostname block.
- **CSP**: VoxGate sets its own Content-Security-Policy. Do not add a
  separate `header Content-Security-Policy …` directive in the
  Caddyfile — it would collide with the server-side one.

## Further docs

- All env vars: [`../../docs/setup.md`](../../docs/setup.md)
- Security checklist: [`../../docs/security.md`](../../docs/security.md)
- Backend JSON contract: [`../../docs/integration.md`](../../docs/integration.md)
- Example backend implementations: [`../../docs/backends.md`](../../docs/backends.md)
