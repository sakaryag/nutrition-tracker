# NutriTrack

A local-first daily nutrition tracker. Log meals, track macros (protein, fat, carbs, calories), and build meal templates for one-tap logging.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![Flask](https://img.shields.io/badge/Flask-3.x-green) ![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey)

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/sakaryag/nutrition-tracker.git
cd nutrition-tracker
```

### 2. Create a virtual environment and install dependencies

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Run the app

```bash
python app.py
```

Open **http://localhost:5000** in your browser. The database is created automatically on first run and seeded with ~800 common foods.

---

## Features

- **Daily dashboard** — log foods, see macro totals with progress bars and a donut chart
- **Food search** — 800+ USDA foods + your own custom foods and meals
- **Meal templates** — save a group of foods (e.g. "My usual breakfast") and log them all with one tap
- **History** — browse past days and view weekly trends
- **Targets** — set your daily protein / fat / carbs / calorie goals
- **CSV export** — download your full log
- **Optional login** — multi-user auth via environment variable (off by default)

---

## Configuration

Create a `.env` file in the project root to override defaults:

```env
# Disable login/register (default: true — login is required)
# AUTH_ENABLED=false

# Required when AUTH_ENABLED=true — use a long random string
SECRET_KEY=change-me-to-something-secret

# Use PostgreSQL instead of SQLite (optional)
# DATABASE_URL=postgresql://user:password@host:5432/nutritrack

# Default macro targets (grams / kcal)
DEFAULT_PROTEIN_TARGET=150
DEFAULT_FAT_TARGET=65
DEFAULT_CARBS_TARGET=250
DEFAULT_CALORIES_TARGET=2200
```

---

## Running with Docker

```bash
docker compose up --build
```

App runs on **http://localhost:5000**. Data is stored in a named volume so it persists across restarts.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Tech Stack

- **Backend:** Flask 3, Flask-SQLAlchemy, Flask-Migrate
- **Database:** SQLite (local) — drop-in PostgreSQL for production
- **Frontend:** Vanilla HTML / CSS / JS, Chart.js
- **Auth:** Session-based, optional
- **Deploy:** Docker + Gunicorn, GitHub Actions CI
