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
  adapter in `docs/backends.md` behind `TARGET_URL`.

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
