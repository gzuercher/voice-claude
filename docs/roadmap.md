# Roadmap

Living document — ideas for future development. Nothing here is a
commitment; the further down a horizon, the more uncertain. Each entry
has a rough **value** (why bother) and **cost/risk** (why it might
hurt).

The goal of VoxGate is to stay a small, dependency-light voice gateway.
That principle constrains the roadmap as much as it shapes it.

---

## Horizon 1 — near-term (weeks)

Small, well-defined improvements that fit the existing architecture.

### Streaming responses (SSE)
- **Value:** Claude replies start playing/showing within ~500 ms instead
  of after the full response. Big perceived-latency win.
- **Cost:** server: switch `/claude` to SSE; PWA: incremental TTS plus
  text accumulation. Modest. The tricky part is making `speechSynthesis`
  speak partial sentences without sounding chopped.

### Conversation history persistence (per session, per user)
- **Value:** restart no longer wipes ongoing threads. Phone reload
  doesn't lose context.
- **Cost:** persist `_sessions` to disk (SQLite or a JSON file in a
  mounted volume). Requires a mounted volume in compose.
- **Constraint — opt-in only:** the README, `docs/setup.md`, and
  `docs/security.md` currently advertise "nothing is persisted" as an
  intentional property (no disk leak, no backup duty, no GDPR storage
  obligation). Persistence must therefore ship behind an env switch,
  e.g. `SESSION_STORE=memory|sqlite` with `memory` as the default.
  Existing users keep the original contract; opt-in users accept the
  new one.
- **Doc updates required when shipped:** the three "intentional, lost
  on restart" passages must be rewritten to describe both modes. The
  security checklist gains a new item ("if `SESSION_STORE=sqlite`,
  back up and protect `/data/sessions.db` like personal data").

### Multi-token support (named keys)
- **Value:** today there is one shared `API_TOKEN`. Adding named keys
  (`API_TOKENS=alice:xxx,bob:yyy`) enables per-user revocation and
  per-user audit-log entries.
- **Cost:** small server change, but breaking for the `/config` and
  setup story. Keep single-token mode as default to not disrupt
  existing users.

### iOS Safari minimum support
- **Value:** unblock iPhone users who currently get a half-broken UX
  (Web Speech API is limited).
- **Cost:** at minimum: detect Safari, show a clear "open in Chrome"
  banner instead of silently failing. Going further (server-side STT
  fallback) is Horizon 2.

### Configurable system-prompt presets
- **Value:** quickly switch between "concise assistant", "language
  tutor", "pirate" etc. without rebuilding the container.
- **Cost:** UI: small dropdown next to the language toggle. Server:
  `SYSTEM_PROMPTS` env as named map. Cheap; fits the spirit.

---

## Horizon 2 — mid-term (months)

Larger work that introduces new dependencies or changes the surface.

### Server-side STT fallback (Whisper)
- **Value:** unlocks iOS/Safari and any browser with weak Web Speech
  support. Vastly better recognition quality and dialect tolerance —
  a *real* answer to "Schwyzerdütsch erkennen".
- **Cost:** new external dependency (OpenAI Whisper API or a local
  whisper.cpp container). Audio upload path. Cost per request. Token
  privacy concerns. Optional via `STT_BACKEND=webspeech|whisper`.

### Server-side TTS (better voices)
- **Value:** device-installed voices are inconsistent. ElevenLabs /
  OpenAI TTS / Azure produce reliably good audio across phones.
- **Cost:** another external dependency, another API key, latency, per-
  request cost. Streaming support needed to keep perceived speed.

### Image / camera input
- **Value:** point phone camera at something, ask Claude about it.
  Multimodal is one of Claude's strengths and currently unused.
- **Cost:** UI: capture button + preview. Server: image upload, base64
  encode for Anthropic API. Privacy considerations (where does the
  image live, audit log, etc.).

### Conversation export and search
- **Value:** voice conversations are ephemeral by default; users may
  want to revisit, share, export to markdown. Search across past
  conversations.
- **Cost:** depends on persistence (Horizon 1 prerequisite). Search at
  trivial scale is `LIKE %query%`; at non-trivial scale needs FTS5 or
  similar.

### Edge-pre-auth bundle
- **Value:** ship `deploy/caddy-private/` with Basic Auth or
  Cloudflare Access pre-wired for closed-group setups. Documents the
  pattern, removes guesswork.
- **Cost:** more bundles to maintain. Decide carefully whether docs
  alone (current state) are enough.

---

## Horizon 3 — vision / aspirational

Direction the project *could* take but each point would change what
VoxGate is. Listed for discussion, not commitment.

### Local-only mode (privacy-first)
- **Value:** drop external dependencies entirely. Whisper.cpp for STT,
  llama.cpp / Ollama for the LLM, Piper for TTS. No data leaves the
  device's LAN.
- **Cost:** completely different deployment story (GPU? CPU-only?
  model downloads). Quality far below Claude. Could become a
  "VoxGate Local" sibling project rather than an option.

### Native mobile apps (iOS/Android)
- **Value:** access to platform STT (Apple's, Google's), better
  background behaviour, push notifications, real wake-word support.
- **Cost:** two new codebases to maintain. PWA-first philosophy
  abandoned. Probably only worth it if the user base demands it.

### Wake word ("Hey VoxGate")
- **Value:** hands-free triggering, true voice assistant feel.
- **Cost:** wake-word detection wants always-on mic, which a PWA
  cannot really do reliably. Native app dependency. Privacy theatre
  unless local — and local wake-word adds yet another dependency.

### Multi-user / family profiles with proper login
- **Value:** different histories, settings, voices per user; per-user
  Anthropic budget tracking.
- **Cost:** introduces a real auth system, sessions, password reset,
  account UI. VoxGate stops being a single-tenant tool. Big philosophy
  break — only do this if it's clearly the new product.

### Plugin / skill ecosystem
- **Value:** community-contributed integrations (calendar, todo, home
  automation) without central maintenance.
- **Cost:** plugin protocol, sandboxing, versioning, distribution.
  This is "VoxGate becomes a platform" territory. MCP-bridge (Horizon
  2) is the lighter version of the same idea.

### Hosted SaaS offering
- **Value:** zero-setup option for non-technical users.
- **Cost:** abuse handling, payment, GDPR, on-call. A different
  business, not a feature.

---

## Deliberately not planned

To keep the roadmap honest, here's what we are *not* going to do, and
why:

- **Built-in user accounts with passwords.** Out of scope. The bearer
  token + edge-pre-auth pattern is enough for VoxGate's target
  audience. Bringing in account systems means owning password reset,
  email verification, etc. — none of which is core to "voice in,
  voice out".
- **Token in URL (`?key=…`) for easy sharing.** Security antipattern.
  Tokens leak via referer headers, browser history, and access logs.
- **Multi-worker uvicorn with sticky sessions.** The single-worker
  constraint is documented and intentional. If scaling ever becomes
  necessary, the right move is Redis-backed session storage, not
  sticky load-balancing (see `docs/setup.md` "Migration path").
- **Bundling cloudflared/Tailscale as docker-compose recipes.** The
  upstream tools have excellent setup UIs and docs. We point at them
  in `docs/setup.md` instead of duplicating moving targets.
- **Built-in MCP-server bridge.** Voice-driven tool execution would
  turn VoxGate from a 250-line voice forwarder into a multi-round
  tool-use orchestrator with its own security perimeter, allowlists,
  and connection management. The right place for that complexity is
  the user's own `/prompt` backend: it can speak MCP, do tool-use
  loops with Claude internally, and hand VoxGate just the final
  reply. VoxGate stays small.

---

## How to use this document

1. When picking work, prefer Horizon 1 unless there is an explicit
   reason to jump higher.
2. Before starting any item, write a short plan (in
   `~/.claude/plans/` or as a GitHub issue) — the roadmap entry is
   not a spec.
3. When something here turns out to be a bad idea, delete it and
   record why. Stale items rot the document.
4. Add new ideas with the same value/cost framing. Vague ideas
   ("better UX") have no place here — be concrete.
