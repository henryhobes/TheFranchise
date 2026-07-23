# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## Project overview

DraftOps is a retired weekend project (Aug-Sep 2025) that automated an ESPN
fantasy football draft. It has two halves:

1. **WebSocket protocol layer** (`draftOps/src/websocket_protocol/`) -
   reverse-engineered ESPN's undocumented draft WebSocket protocol, captures
   live draft events with Playwright, parses them, and cross-validates player
   IDs against ESPN's public API.
2. **LangGraph "front office"** (`draftOps/src/ai/`) - a multi-agent draft
   assistant (Draft Strategist, Scout, GM, Supervisor) that recommends picks
   in real time.

The project is archived. Changes should preserve behavior and keep the code
readable rather than add features.

## Layout

- `draftOps/src/` is the import root. The two top-level packages are `ai` and
  `websocket_protocol`; `data_loader.py` is a top-level module.
- `draftOps/src/ai/core/` - the agents: `draft_strategist.py` (rules-based),
  `scout.py` and `gm.py` (LLM), `draft_supervisor.py` (LangGraph graph).
- `draftOps/src/websocket_protocol/{monitor,state,api,utils,scripts}/` - capture,
  parsing, ESPN API client, ID extraction/validation, and runnable scripts.
- `draftOps/docs/` - sprint specifications and the protocol analysis.

## Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium          # only needed to run the live monitor

pytest                               # runs the suite; live-API tests deselected
pytest -m liveapi                    # agent tests that call OpenAI (needs OPENAI_API_KEY)
```

Pytest config lives in `pyproject.toml` (`pythonpath`, `testpaths`, markers).

## Conventions

- Python only. Prefer the simplest solution; let code be self-documenting.
- No emojis anywhere. Keep console output plain ASCII (`[PASS]`, `[FAIL]`,
  `SUCCESS:`, `ERROR:`) - the codebase was developed on Windows (CP1252).

## Notes

- Player data (`draftOps/playerData/*.csv`) and `.har` captures are gitignored
  and absent; the loader and live scripts need them locally to run.
- The LLM agents need `OPENAI_API_KEY` (loaded from `.env`).
- Known limitations are tracked in `draftOps/docs/stuff-to-clean.md`.
