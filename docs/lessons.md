# Lessons learned

This file is maintained automatically. When Claude makes a mistake and is
corrected, the lesson is recorded here.

Format: `- [YYYY-MM-DD]: [What was wrong] → [Correct approach]`

## Lessons

<!-- Append new entries at the top -->

- [2026-04-30]: VoxGate carried two endpoints (`/claude` for direct
  Anthropic, `/prompt` for forward) and the frontend was hardcoded to
  `/claude`, silently breaking the forward setup → Designentscheid:
  VoxGate is now a **pure voice-frontend with auth gate**. No
  built-in LLM client, single `/chat` endpoint, strict JSON contract
  to TARGET_URL. Anyone wanting voice-to-Claude runs a small adapter
  container behind TARGET_URL. See `docs/integration.md`.

- [2026-04-30]: Dockerfile mirrored Python deps from `pyproject.toml`
  by hand, drifted twice in one week (auth/ + google-auth[requests] +
  itsdangerous missed in commit `bb90392`) → Always install from
  `pyproject.toml` (`pip install .`), never re-list deps in the
  Dockerfile. BuildKit cache mount keeps the speed advantage.
