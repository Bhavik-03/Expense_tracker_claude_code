# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Spendly is a Flask-based personal expense tracker, built incrementally as a step-by-step learning project. Many routes and modules are intentionally left as placeholders (e.g. `database/db.py` and several routes in `app.py`) with comments marking which "Step" will implement them. When working on this codebase, follow the existing step structure rather than jumping ahead and fully implementing unrelated future steps unless asked.

## Commands

Activate the virtualenv before running anything (the `venv/` directory is already present):

```
# from repo root
source venv/Scripts/activate   # Git Bash on Windows
```

Run the app:
```
python app.py
```
Serves on `http://localhost:5001` with `debug=True`.

Install/update dependencies:
```
pip install -r requirements.txt
```

Run tests (pytest + pytest-flask are declared as dependencies, but no test files exist yet):
```
pytest
```

## Architecture

- **`app.py`** — single Flask app with all routes defined directly on it (no blueprints). Routes fall into two groups:
  - Implemented pages that just `render_template(...)`: `/`, `/register`, `/login`, `/terms`, `/privacy`.
  - Placeholder routes returning plain strings, each marked "coming in Step N": `/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`. When implementing one of these, replace the placeholder with real logic and remove the "coming in Step N" comment.

- **`database/db.py`** — not yet implemented. Per its own header comment, it is expected to provide:
  - `get_db()` — SQLite connection with `row_factory` and foreign keys enabled
  - `init_db()` — creates tables using `CREATE TABLE IF NOT EXISTS`
  - `seed_db()` — inserts sample dev data
  
  There is currently no schema, no `.db` file, and no ORM — plain SQLite via the standard library is the intended approach.

- **`templates/`** — Jinja2 templates. `base.html` is the shared layout (nav + footer) that all pages extend via `{% block title %}`, `{% block head %}`, `{% block content %}`, `{% block scripts %}`. All internal links use `url_for(...)` with the Flask route function name, not hardcoded paths.

- **`static/css/style.css`** and **`static/js/main.js`** — single global stylesheet/script shared across all pages (no per-page CSS/JS files, no bundler/build step). Fonts are loaded from Google Fonts (`DM Serif Display`, `DM Sans`) directly in `base.html`.

- No authentication, sessions, or database wiring exists yet — `/login` and `/register` currently only render static forms.

## Testing workflow

After implementing any feature/step, invoke the `spendly-test-writer` subagent (`.claude/agents/spendly-test-writer.md`) with the step's spec from `.claude/specs/`. It writes pytest tests from the spec (not the implementation) into `tests/`, reusing the fixtures in `tests/conftest.py`.
