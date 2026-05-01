# Security checklist

Walk through this checklist point by point before going public. Every
item should be answerable with yes/no without reading source code.

## Before the first public deploy

- [ ] **`GOOGLE_CLIENT_ID` is set** to the OAuth Client ID issued by the
      Google Cloud Console. Without it, login is disabled and every
      request to `/chat` is rejected.
- [ ] **`TARGET_URL` is set** and points at a backend that speaks the
      contract in [`integration.md`](integration.md). Without
      it, every authenticated `/chat` request returns `503`.
- [ ] **`ALLOWED_EMAILS` lists every permitted user explicitly.**
      Adding/removing an entry takes effect on the next request — no
      restart needed.
- [ ] **`SESSION_SECRET` is set explicitly in `.env`.** Otherwise
      VoxGate generates a fresh secret on every container start
      (fine for dev, bad for production — every restart logs all users
      out and may invalidate active PWA installs).
- [ ] **`COOKIE_SECURE=1` in production.** With `0`, browsers refuse to
      keep the session cookie over HTTPS in some configurations. Only
      use `0` for local `http://localhost` development.
- [ ] **`ALLOWED_ORIGIN` points at the real domain.** Empty = no
      browser origin may call the API. Wildcards (`*` etc.) are
      intentionally not supported.
- [ ] **`TRUST_PROXY_HEADERS=1` only when the server is reachable
      exclusively through the reverse proxy.** Otherwise clients can
      spoof `X-Forwarded-For` and bypass rate limiting. Inside the
      `deploy/caddy/` bundle this is automatically the case.
- [ ] **`RATE_LIMIT_PER_MINUTE` and `AUTH_LOGIN_RATE_LIMIT_PER_MINUTE`
      chosen deliberately.** Defaults 30 / 10 are fine for a small
      group.

## Backend-specific

- [ ] **Target backend binds to `127.0.0.1`** (or a private network) or
      requires its own `TARGET_TOKEN`. Otherwise VoxGate inadvertently
      exposes your backend to the internet.
- [ ] **Target backend trusts `user_email`.** VoxGate verifies the
      e-mail via Google and matches it against `ALLOWED_EMAILS` before
      forwarding. The backend can rely on `body.user_email` for ACL
      decisions and *should not* trust any client-supplied e-mail field.
- [ ] **Target backend has its own backups.** VoxGate has no state
      worth backing up; the target backend may.
- [ ] **LLM/API credentials live in the backend, not VoxGate.** VoxGate
      has no model credentials by design. Set spending limits on those
      keys in the relevant provider console.

## During operation

- [ ] **Logs are reviewed.** `docker compose logs -f voxgate` shows
      audit entries with the user's e-mail, IP, session prefix and
      text length (no payload), plus `auth_login_ok` /
      `auth_not_allowed` lines.
- [ ] **No additional `Content-Security-Policy` in the reverse
      proxy.** VoxGate sets a strict CSP itself. A second directive
      in Caddy/nginx collides.
- [ ] **Updates are checked.** `git pull && docker compose build &&
      docker compose up -d` regularly — especially after security
      releases.

## What VoxGate brings out of the box

Active without any operator action:

- Google Sign-In with strict ID-token verification (issuer, audience,
  signature against Google JWKS, `email_verified=true`, `exp`).
- Allowlist match on every login *and* every authenticated request —
  removing a user from `ALLOWED_EMAILS` revokes access on the next
  request without a restart.
- Optional `email:provider` binding in `ALLOWED_EMAILS` — defends
  against an attacker registering the same e-mail at a different
  identity provider once a second provider is added.
- Session cookies are `HttpOnly`, `Secure` (when `COOKIE_SECURE=1`) and
  `SameSite=Strict`, signed with `itsdangerous` using `SESSION_SECRET`.
  XSS cannot read them.
- CSRF protection: every state-changing endpoint requires the
  `X-CSRF-Token` header to match the `vg_csrf` cookie (double-submit).
- Per-IP rate limit on `/chat` *and* `/auth/login/*`.
- Strict `session_id` validation (`^[A-Za-z0-9_-]{8,128}$`).
- Strict response-shape validation on TARGET_URL replies — backends
  cannot accidentally leak unexpected fields into the PWA.
- Strict CSP (Google Identity Services script and frame allowed only at
  `/gsi/*`), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
  `Referrer-Policy`, `Permissions-Policy` (microphone only).
- Audit log lines include the authenticated user's e-mail.
- CORS blocked by default; `allow_credentials=True` only with an
  explicit `ALLOWED_ORIGIN`.

## Optional: edge-level pre-auth for closed groups

For paranoid setups you can layer additional auth in front of VoxGate.
That is independent of VoxGate's own login and lives one layer up:

- **Cloudflare Access** in front of a Cloudflare Tunnel. Magic-link
  email login at the edge; no code changes inside VoxGate. Free tier
  covers small groups.
- **Tailnet-only**: run VoxGate behind Tailscale and skip Funnel.
  Only members of your tailnet can reach the URL at all.

VoxGate's Google login still applies inside — defence in depth, not a
replacement.

## Residual risks

- **Per-IP rate limit only:** behind NAT/CGNAT users share the quota.
- **Dependency on Google availability:** during a Google Identity
  Services outage, no one can log in. The session cookie remains valid
  for `SESSION_COOKIE_TTL_SECONDS` regardless, so already-logged-in
  users are unaffected.
- **Token replay until expiry:** revoking a Google account does *not*
  immediately invalidate an issued VoxGate session cookie. Remove the
  e-mail from `ALLOWED_EMAILS` to revoke instantly (the live allowlist
  check rejects every subsequent request).
- **Stateless logout:** `POST /auth/logout` clears the cookies on the
  client but the signed session blob remains cryptographically valid
  until `SESSION_COOKIE_TTL_SECONDS` elapses. If a cookie was captured
  before logout (e.g. on a stolen laptop) and the e-mail stays in
  `ALLOWED_EMAILS`, the cookie still authenticates. Mitigations:
  remove the e-mail from `ALLOWED_EMAILS`, or rotate `SESSION_SECRET`
  to invalidate every session at once. A per-session deny-list would
  add server-side state and is intentionally not implemented at this
  scale — the allowlist provides the practical revoke path.
