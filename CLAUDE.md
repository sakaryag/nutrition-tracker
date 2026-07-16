# NutriTrack - Build Instructions

## What is this project?

A local-first daily nutrition tracker (protein, fat, carbs, calories) built with Flask + SQLite. See `REQUIREMENTS.md` for full specs.

## Quick Start

```bash
cd nutrition-tracker
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
python app.py
# Open http://localhost:5000
```

## Tech Stack

- **Backend:** Flask 3.x, Flask-SQLAlchemy, Flask-Migrate
- **Database:** SQLite (local), PostgreSQL (deploy)
- **Frontend:** Vanilla HTML/CSS/JS + Chart.js (CDN)
- **Testing:** Pytest

## Architecture Decisions

- **Flask over Streamlit** — full control over UI, REST API, and deployment
- **No frontend build step** — vanilla JS, no npm/webpack/vite
- **App factory pattern** — `create_app()` in `app.py` for testability
- **Blueprint-based routes** — one blueprint per resource (`entries`, `summary`, `targets`, `foods`, `export`, `pages`)
- **SQLite WAL mode** — enabled in config for crash safety
- **Config via environment** — `config.py` reads from env vars with sensible defaults

## Project Structure

```
app.py              → Flask app factory, entry point
config.py           → Environment-based configuration
models/             → SQLAlchemy models (food_entry, daily_target, saved_food, user)
routes/             → Flask blueprints (entries, summary, targets, foods, export, pages)
templates/          → Jinja2 templates (base, dashboard, history, foods, settings)
static/css/         → Mobile-first CSS
static/js/          → Page-specific JS (dashboard.js, history.js, foods.js)
tests/              → Pytest tests
instance/           → SQLite database (gitignored)
```

## Key Patterns

- All API routes return JSON, all page routes return HTML
- API prefix: `/api/`
- Calories auto-calculate if omitted: `(protein * 4) + (fat * 9) + (carbs * 4)`
- Dates use `YYYY-MM-DD` format everywhere
- Daily targets use an `effective_from` date so history is preserved when targets change

## Database

- Models use Flask-SQLAlchemy declarative style
- Migrations managed by Flask-Migrate (Alembic)
- SQLite stored at `instance/nutritrack.db`
- Tables: `food_entry`, `daily_target`, `saved_food`, `user`

## Running Tests

```bash
pytest tests/ -v
```

## Build Phases

Building this project incrementally. Current status tracked below.

### Phase 1: Core MVP (Must Have)
- [ ] Project setup (Flask app, config, models, requirements.txt)
- [ ] Food entry CRUD API + UI
- [ ] Daily dashboard (totals, entry list, progress bars)
- [ ] Daily targets (set/get + progress display)
- [ ] Mobile-first CSS

### Phase 2: Enhanced UX (Should Have)
- [ ] Meal type grouping
- [ ] Macro donut chart
- [ ] Quick-add from recents
- [ ] Saved foods library
- [ ] History page + date picker
- [ ] Weekly trends chart

### Phase 3: Production Ready (Could Have)
- [ ] CSV export
- [ ] Authentication
- [ ] Docker setup
- [ ] Test suite
- [ ] CI/CD

## Conventions

- Python: PEP 8, type hints on function signatures
- HTML: Semantic elements, accessible forms
- JS: No frameworks, use `fetch()` for API calls, update DOM directly
- CSS: Mobile-first, CSS custom properties for theming
- Git: Conventional commits (`feat:`, `fix:`, `docs:`, `test:`)
