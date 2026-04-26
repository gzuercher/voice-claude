# VoxGate

**Talk to Claude (or another chatbot) by voice — straight from your phone.**

VoxGate is a small web app you install on your smartphone home screen
like a native app. Tap the microphone button, speak, and hear the answer
read back to you. It works in Swiss German and Swiss French.

## What can I do with it?

- **Talk to Claude directly** — provide an Anthropic API key and VoxGate
  calls Claude for you. Conversation context is preserved within a session.
- **Talk to your own backend** — for example a script on your Mac that
  runs Claude Code in the terminal. VoxGate forwards your spoken prompt
  as an HTTP POST.
- **Run multiple instances side by side** — e.g. a green PWA "Claude"
  and a blue PWA "Dokbot", each with its own icon on the home screen.

Typical use case: you go for a walk, tap the Claude icon, ask "What
time is it in Tokyo?", and hear the answer without having to type.

## Using the app

After installing the PWA on your home screen, open it:

| Element | Function |
|---|---|
| **Microphone button (large)** | Tap to start recording. Tap again to send. |
| **Language (top left)** | Switch between `DE-CH` and `FR-CH`. Choice is persisted. |
| **Speaker (top right)** | Mute/unmute speech output. |
| **Status dot (top right)** | Green = ready, blinking = sending, red = error. |
| **New conversation (bottom)** | Reset the conversation history. |

Replies are read aloud automatically unless muted. If you tap the mic
again while audio is playing, the current speech is cancelled.

### Requirements

- **Browser:** Chrome on Android or desktop (Web Speech API).
  Safari/iOS support is limited.
- **Microphone permission** must be granted on first launch.
- **HTTPS** is mandatory on Android.

## Installing the PWA on your phone

1. Open Chrome on Android → `https://your-voxgate-host`
2. Three-dot menu → "Add to Home screen"
3. The app now opens like any other app, with its own icon and color.

If multiple instances are deployed (different hostnames), repeat for
each — every URL becomes its own PWA.

## Troubleshooting

| Problem | What to do |
|---|---|
| Microphone doesn't react | Grant permission in the browser. On Android the page must be HTTPS. |
| No speech output | Check the speaker button (top right). iOS has limited Web Speech support. |
| `401` error | Bearer token missing or wrong — ask your operator. |
| `429` error | Rate limit hit. Wait a minute and retry. |
| `503` on `/claude` | Anthropic backend not configured — ask your operator. |
| Conversation suddenly "forgets" | The server was restarted; sessions live in memory. |
| Doesn't work properly on Safari/iOS | Web Speech API is limited there; use Chrome. |

---

The rest of this file is reference material for developers and clients
calling VoxGate's HTTP API. For installing and operating a VoxGate
server see [`SETUP.md`](SETUP.md). For contributing see
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Architecture

```
┌─────────────┐                             ┌──────────────────┐
│  PWA        │     POST /claude            │                  │     Anthropic API
│  (phone     │  ────────────────────────►  │  VoxGate server  │  ────────────────────►  Claude
│  home       │  ◄────────────────────────  │  (FastAPI)       │  ◄────────────────────  (claude-sonnet-4-5)
│  screen)    │                             │                  │
│             │     POST /prompt            │                  │     POST TARGET_URL
│             │  ────────────────────────►  │                  │  ────────────────────►  Custom backend
│             │  ◄────────────────────────  │                  │  ◄────────────────────  (e.g. Mac with Claude Code)
└─────────────┘                             └──────────────────┘
```

The server exposes two endpoints:

- **`/claude`** — calls the Anthropic API directly. Keeps conversation
  history per session. Uses `ANTHROPIC_API_KEY`.
- **`/prompt`** — forwards to a custom backend (`TARGET_URL`).
  Stateless. Original use case: voice gateway for any chatbot service.

The PWA uses `/claude`. `/prompt` is kept for backwards compatibility
and can be driven by your own clients.

## API reference

### `POST /claude`

Direct Anthropic call with session history.

```json
POST /claude
Authorization: Bearer <API_TOKEN>
Content-Type: application/json

{
  "text": "What time is it in Tokyo?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Response:

```json
{ "response": "Currently it's …" }
```

Errors:
- `401` — token missing or wrong
- `422` — validation failed (`text` too long/empty, `session_id` missing or malformed)
- `429` — rate limit exceeded
- `502` — Anthropic API error
- `503` — `ANTHROPIC_API_KEY` not configured

History: up to 20 messages per `session_id` are kept in memory; older
ones are dropped in pairs. `session_id` must match
`^[A-Za-z0-9_-]{8,128}$`.

### `POST /prompt`

Pure forwarding to `TARGET_URL`.

```json
POST /prompt
Authorization: Bearer <API_TOKEN>
Content-Type: application/json

{ "text": "Hello backend" }
```

VoxGate forwards:

```json
POST <TARGET_URL>
Authorization: Bearer <TARGET_TOKEN>
Content-Type: application/json

{ "text": "Hello backend" }
```

The backend must return JSON with a `response` (or `text`) field.

### `GET /config`

Returns instance configuration for the PWA. No auth.

```json
{ "name": "Claude", "color": "#c8ff00", "lang": "de-CH", "maxLength": 4000 }
```

## File structure

```
voxgate/
├── server.py              # FastAPI gateway (/claude, /prompt, /config)
├── pwa/                   # PWA (HTML, JS, CSS, manifest, service worker)
├── tests/                 # pytest tests
├── .claude/rules/         # Code rules for Claude Code
├── .env.example           # Configuration template
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── Makefile               # make setup/run/test/lint
├── README.md              # This file — end-user view
├── SETUP.md               # Installation and operation
├── CONTRIBUTING.md        # Development workflow
├── CLAUDE.md              # Playbook for Claude Code
└── lessons.md             # Lessons learned
```

## License

MIT
