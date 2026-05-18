# Changelog

All notable user- or operator-visible changes to VoxGate. The format
is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project does not yet ship versioned releases — entries are
grouped by date and each links the relevant commit range.

Operators upgrading should at minimum:

```bash
git pull
docker compose build
docker compose up -d
```

…and re-read the **Operator action required** items below since the
last upgrade, if any.

## [Unreleased]

## [0.3.0] - 2026-05-18

### Added
- **Auto-send on silence (PWA, opt-in).** Two new menu items —
  *Automatisch senden* (toggle) and *Pause vor Senden* (Schnell /
  Normal / Geduldig = 1.2 / 1.8 / 2.5 s). When enabled, the
  recording→review→send flow collapses to recording→silence→send: the
  mic button starts continuous Web Speech, and after the chosen
  silence threshold the locked transcript is sent automatically. A
  500 ms pre-send pulse on the mic icon warns the user that a send is
  about to fire (speaking resets the timer). Default off — the
  classic three-tap flow is fully preserved for anyone who doesn't
  flip the toggle. State persisted in `localStorage`
  (`voxAutoSend`, `voxAutoSendDelay`).
- **SSE streaming (`POST /chat/stream`).** Additive endpoint alongside
  `/chat`. Same auth, same request body, response is `text/event-stream`
  with `chunk` / `tool` / `final` / `error` events. Backends that reply
  with the legacy `application/json` `{"response": "..."}` shape are
  adapted to a single chunk+final event so the PWA codepath stays
  uniform — backends can adopt streaming at their own pace. See
  `docs/integration.md` § Streaming sub-contract.
- **Cancel (`POST /chat/cancel`).** User-initiated interrupt for an
  in-flight streamed turn. Body: `{session_id}`. Idempotent. Mic-button
  doubles as Stop while streaming. PWA also auto-cancels if a new
  prompt is submitted while a previous reply is still streaming
  ("one turn at a time"). Optional `BACKEND_CANCEL_URL` env adds a
  fire-and-forget `DELETE` hook for backends with explicit cleanup
  routes — by default only the TCP close is used.
- **Follow-up-hint contract fields.** Backends may set
  `awaiting_user_input: true` and optionally `suggestion: "<text>"` in
  the response (both `/chat` and the `final` SSE event). The PWA then
  keeps the text input focused, sets `suggestion` as placeholder, and
  marks the bubble with a `?` so the user sees this is a clarifying
  question, not a final answer.
- **`pwa/chat.js`.** Extracted all chat-network code (`/chat`,
  `/chat/stream`, `/chat/cancel`, SSE frame parser) into its own
  module. `pwa/app.js` keeps UI / render / Web-Speech concerns.
- **Single-source-of-truth integration doc.** Folded the runnable
  backend examples (FastAPI minimal + streaming, Anthropic streaming
  adapter, Express, bash stub) into `docs/integration.md` under a new
  `## Reference backend implementations` section. `docs/backends.md`
  removed — backend integrators now have everything at the live
  `GET /integration` URL, no repo checkout needed.

### Operator action required
- None — all three additions are backward compatible. To force-disable
  streaming on a specific instance set `STREAMING_ENABLED=0`. To wire
  an optional backend cancel hook set
  `BACKEND_CANCEL_URL=http://backend/cancel/{session_id}` (literal
  `{session_id}` is substituted).

## [0.2.0] - 2026-05-08

### Added
- **Roundtrip timing under each assistant reply.** PWA measures the
  client-observed `/chat` round-trip with `performance.now()` and
  shows it as a discreet `1.2 s` / `340 ms` line, right-aligned below
  the bubble. Frontend-only, no backend contract change.
- **Service worker caches Google Fonts.** First load fetches the font
  files once over the network; subsequent loads are served from the
  Cache Storage API. App responses (HTML/JS/CSS, `/chat`, `/config`,
  `/auth/*`) stay pass-through, so deploys are picked up immediately.
- **Backend roundtrip latency logging.** Every `/chat` request now
  emits a `backend_roundtrip status=… ms=…` log line after the
  TARGET_URL call returns, so the access log shows directly how much
  user-visible latency comes from the backend versus VoxGate itself.
  `backend_unreachable` carries an `after_ms` too.
- **Container default `TZ=Europe/Zurich`.** Log timestamps line up
  with the Swiss operator's wall clock without configuration.
  Operators in other zones override via the `TZ` env var in
  docker-compose; no rebuild needed.
- **Image / camera input.** PWA captures a photo (camera-direct on
  mobile via `capture="environment"`) or picks one from the gallery,
  downscales to 1600 px JPEG quality 0.85, and forwards via
  `attachments[]` in the `/chat` → TARGET_URL contract. One-way today
  (responses still match `{"response": "..."}`). Validation: per-file
  ≤ `MAX_ATTACHMENT_BASE64_BYTES` (default 4 MiB), per-request ≤
  `MAX_ATTACHMENTS_PER_REQUEST` (default 4), mime ∈ {jpeg, png, webp}.
- **Automatic dark / light mode.** `<html data-theme>` drives the
  palette; the menu offers a 3-way Auto / Light / Dark picker that
  follows `prefers-color-scheme` in Auto.
- **Hamburger menu, Help modal, TTS-off-by-default**, plus iOS Safari
  PWA zoom fix.
- **POST `/selftest`** — authenticated end-to-end probe of the
  VoxGate ↔ TARGET_URL wiring. Returns a structured per-clause
  diagnostic. Sets `metadata.test=true` on the synthetic forward so
  cooperating backends can short-circuit.

### Changed
- **PWA visual identity.** Replaced the system-font + mono-uppercase
  "developer-terminal" look with a distinctive pair: Instrument Serif
  italic for the wordmark and headings, Onest as the body sans. Mono
  is now restricted to the debug overlay. The mic button is filled
  with the per-instance accent in idle and inverts to a tinted
  outline while recording. Footer carries a soft radial accent halo
  for ambient depth.
- **PWA UX.** Transcript placeholder is CSS-driven (`:empty::before`)
  so it disappears on the first keystroke and never lands in
  `textContent`. Stable two-row footer layout: transcript + discard
  on the top row, camera + mic/send on the bottom row — order no
  longer shifts with state.
- **VoxGate is a pure voice gateway.** The previous direct-Anthropic
  `/claude` endpoint is removed; the only chat path is `POST /chat`
  → `TARGET_URL`. Voice-to-Claude is achieved by running the small
  adapter in `docs/integration.md` (Reference backend implementations)
  behind `TARGET_URL`.

### Operator action required
- **None for this range** — the contract change to add `attachments`
  is additive (the field is omitted when no images are attached);
  existing backends keep working.
- Backends that want to opt in to the diagnostic short-circuit on
  `POST /selftest` should branch on `metadata.test === true` (see
  `docs/integration.md#test-mode-flag`).

---

For the per-commit detail of any item above, run:

```bash
git log --oneline --since="2026-04-22"
```
