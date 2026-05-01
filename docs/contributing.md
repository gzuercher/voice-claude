# Contributing

Thanks for your interest in VoxGate. This file describes the workflow, conventions, and how to add new features.

## Language

- **Everything written into the repository is English**: code,
  comments, identifiers, docstrings, documentation, commit messages,
  PR descriptions, issues.
- **Exception:** UI text follows the product target language (Swiss
  German for the PWA).

## Setup

```bash
git clone git@github.com:gzuercher/vox-gate.git
cd vox-gate
make setup        # create venv, install dependencies
make test         # run tests
make check        # lint + tests
```

## Code conventions

The binding rules live in `.claude/rules/` and apply to both human contributors and Claude Code:

- [`../.claude/rules/security.md`](../.claude/rules/security.md) — no secrets in code, Google Sign-In with allowlist, validate inputs.
- [`../.claude/rules/code-quality.md`](../.claude/rules/code-quality.md) — strict typing, no empty `catch` blocks, components under 200 lines.
- [`../.claude/rules/accessibility.md`](../.claude/rules/accessibility.md) — semantic HTML, ARIA, keyboard navigation, color contrast (WCAG AA).
- [`../.claude/rules/dev-stack.md`](../.claude/rules/dev-stack.md) — tech stack and verification rules.

In addition:

- **Linter:** `ruff` — config in `pyproject.toml`, line length 100. `make lint` must be green.
- **Tests:** every new endpoint needs pytest tests in `tests/`. Mock external calls (httpx outbound) — no real network in tests.
- **Imports:** prefer absolute paths.
- **No new dependencies** without discussion. VoxGate should stay lightweight.

## Workflow

1. Branch from `main`.
2. Implement — `make check` must pass.
3. Open a PR against `main` with a clear description (what, why).
4. For security-relevant changes (auth, public APIs, deployment, personal data) call them out explicitly in the PR.

## Adding a new endpoint

1. Define the Pydantic request model in `server.py` (`Field(..., min_length=1, max_length=…)`).
2. Protect the endpoint with `session: SessionData = Depends(verify_session)` if auth is required. The dependency validates the signed `vg_session` cookie *and* the `X-CSRF-Token` header against the `vg_csrf` cookie. The PWA helper `VoxGateAuth.withAuthHeaders(...)` wires the header automatically.
3. Wrap external calls in a function so tests can patch them (see how `tests/test_server.py` patches `httpx.AsyncClient`).
4. Add tests in `tests/test_server.py` — at minimum: happy path, validation errors, auth errors (no session, missing CSRF), backend errors.
5. Document the endpoint in `README.md` under "API reference".
6. If a new env variable is introduced: extend `.env.example`, `deploy/caddy/.env.example`, and the configuration table in `docs/setup.md`.
7. If the change affects the `/chat` → TARGET_URL forwarding contract, update `docs/integration.md` *first* — that file is the source of truth for backend implementers.

## Working with Claude Code

VoxGate is primarily developed with Claude Code. Useful slash commands:

- `/commit-push-pr` — automate the git workflow
- `/review` — code review of the current branch
- `/build-and-test` — run build and tests
- `/security-review` — security review of pending changes

When Claude makes a mistake: correct immediately and document the lesson in [`lessons.md`](lessons.md) (format: `- [Date]: [What went wrong] → [Correct approach]`). For recurring patterns, update `CLAUDE.md` or a rule under `.claude/rules/` instead.

## Personal settings

Personal overrides belong in `.claude/settings.local.json` (gitignored), not in committed files.

## Extending the rules

1. Create a new file in `.claude/rules/`.
2. Set `globs` in frontmatter if the rule should apply only to specific file types.
3. Keep it short, specific, with reasoning.
4. Open a PR and align with the team.
