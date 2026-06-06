# Repository Guidelines

QuickBid is a hospital-IT bid document generator built on a "confirmation-driven" multi-agent workflow: an Agent does a step, the user confirms or corrects, and the pipeline advances. This file is the contributor guide for humans and AI agents working in this repo.

## Project Structure & Module Organization

- `cli.py` — CLI entry point, thin I/O layer over the Orchestrator.
- `main.py` — FastAPI server (REST + SSE, Vercel AI SDK Data Stream Protocol) consumed by the web frontend.
- `orchestrator.py` — State machine (`IDLE → AWAIT_TENDER_FILE → ... → DONE`) and Agent dispatcher.
- `agents/` — Agent implementations. `base.py` defines `BaseAgent` and `AgentContext`; subpackages hold specialized agents (`bid_parser/`, `parser_agent.py`, `matcher_agent.py`, `generator_agent.py`, `reviewer_agent.py`, `subbid_agent.py`).
- `models.py` — SQLAlchemy models for `Project`, `Tender`, `Material`, `MaterialUsage`. Status and type fields are plain strings, not Enums.
- `web-next/` — Current Next.js 15 + React 19 + Tailwind 4 + Vercel AI SDK frontend. `web/` is the legacy Vue 3 codebase, kept for reference only.
- `materials/` — Material library, six fixed categories (`01_公司资质` ... `06_其他`).
- `projects/` — One subdirectory per bid project, named `<timestamp>_<name>/`, containing `tender.pdf`.
- `exports/` — Generated Word/PDF outputs.
- `docs/` — `technical-design.md`, `multi-agent-architecture.md`, `architecture-decisions.md`, `implementation-log.md`.

## Build, Test, and Development Commands

Python environment (mandatory `uv`, no global `pip`):

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env   # then fill TENDER_DEEPSEEK_API_KEY
```

Run the app:

```bash
python cli.py                                # CLI chat mode
python main.py                               # FastAPI on :8000
cd web-next && npm install && npm run dev    # Next.js on :3000 (proxies /api/* to :8000)
```

Smoke checks:

```bash
python -c "from models import init_db; print('OK')"   # DB schema
```

## Coding Style & Naming Conventions

- Python: 4-space indent, `snake_case` for modules/functions/variables, `PascalCase` for classes, type hints on public APIs. Keep Agents stateless — all context flows through `AgentContext`.
- TypeScript/React: 2-space indent, `PascalCase` for components, `camelCase` for hooks and utilities; colocate component-specific helpers under `web-next/components/`.
- Configuration lives in `config.yaml` (project-local) with fallback to `~/.tender-tool/config.yaml`. Do not hard-code paths or API keys — read from `config.yaml` and `TENDER_DEEPSEEK_API_KEY`.
- File paths are system-generated and persisted to the DB; do not pass paths as parameters.
- No formatter or linter is enforced today; match the existing module's style and run `python -m py_compile` / `tsc --noEmit` (in `web-next/`) before pushing.

## Testing Guidelines

There is no automated test suite. Verify changes manually:

1. `python -c "from models import init_db; print('OK')"` for schema changes.
2. End-to-end run: start `python main.py` + `npm run dev`, walk a project from upload through export.
3. SSE changes must be checked against the Vercel AI SDK Data Stream Protocol event order: `start → text-* → tool-input-available → tool-output-available → finish-step → finish-message → finish`.

When adding tests in the future, place them in `tests/test_<module>.py` (Python) or `web-next/__tests__/<name>.test.tsx` (TypeScript) and name them `test_<behavior>_<expectation>`.

## Commit & Pull Request Guidelines

Commit messages follow Conventional Commits, frequently bilingual (Chinese summaries are common):

```
feat(scope): short summary
fix(backend): keyword router reads parts[] from AI SDK v3
docs: reflect Vue 3 to Next.js 15 migration
chore(gitignore): exclude runtime artifacts
```

Use scopes observed in history: `backend`, `parser`, `frontend`, `web-next`, `ai`, `router`, `sidebar`, `upload`, `design`, `gitignore`.

Default behavior: **commit locally only, never `git push` unless the user explicitly asks** ("推到远端" / "push" / "同步到Git").

PRs should include: a one-line summary, the affected scope, manual verification steps performed, and screenshots for any `web-next/` UI change. Link the originating issue or task.

## Security & Configuration Tips

- `.env` contains the DeepSeek API key and is git-ignored. Never commit it; use `chmod 600 .env`.
- API keys are read via `TENDER_DEEPSEEK_API_KEY`; the field `api_key_env` in `config.yaml` controls which env var is consulted.
- Materials, projects, and exports contain potentially sensitive bid data — keep `.gitkeep` placeholders and do not commit real PDFs.
- `tender.db` (SQLite) is generated locally and ignored; delete it to reset state during development.
