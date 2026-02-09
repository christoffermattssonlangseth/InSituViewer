# Agent Instructions

## Project overview
Local desktop app for Xenium-style spatial transcriptomics analysis (InSituCore).

## Environment
- Use Python 3 with a local venv.
- Install dependencies from `requirements.txt` and optionally `requirements-optional.txt` when needed.

## Common commands
- Create venv:
  `python3 -m venv .venv && source .venv/bin/activate`
- Install deps:
  `pip install -r requirements.txt`
- Optional deps:
  `pip install -r requirements-optional.txt`
- Check env:
  `python3 check_env.py` (add `--require-optional` for strict)
- Run app:
  `python3 -m app.main` or `python3 run_app.py`

## Working conventions
- Prefer `rg` for search.
- Avoid editing generated artifacts in `dist/` unless explicitly asked.
- Keep changes minimal and aligned with existing patterns in `app/`, `utils/`, and `scripts/`.
- When updating UI styles, coordinate with `app/theme_light.qss` and `app/theme_dark.qss`.

## Notes
- Build/packaging scripts live in `scripts/`.
- Local output artifacts are git-ignored; do not commit large data files.
