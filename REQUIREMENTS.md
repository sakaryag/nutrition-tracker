# NutriTrack - Daily Nutrition Tracker

## Project Overview

**NutriTrack** is a local-first web application for tracking daily macronutrient intake (protein, fat, carbohydrates) and calories. Built with Python (Flask backend + lightweight frontend), it runs locally via a single command and is structured for easy deployment to cloud platforms (Heroku, Railway, Render, or Docker).

---

## 1. Goals & Constraints

| Dimension | Decision |
|-----------|----------|
| **Primary goal** | Track daily protein, fat, carbs, and calories with minimal friction |
| **Tech stack** | Python 3.10+, Flask, SQLite (local) / PostgreSQL (deploy), HTML/CSS/JS (vanilla + Chart.js) |
| **Why Flask over Streamlit** | Flask gives full control over UI, REST API, and deployment; Streamlit is great for prototyping but harder to customize and deploy as a production app |
| **Local-first** | SQLite database, no external services required to run |
| **Deploy-ready** | Dockerfile, environment-based config, database URL swap to PostgreSQL |
| **Auth** | Optional — disabled locally, simple login when deployed |
| **Data persistence** | SQLite file stored in `instance/` directory (gitignored) |

---

## 2. Functional Requirements

### FR-1: Food Entry Management

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | User can add a food entry with: name, protein (g), fat (g), carbs (g), optional calories | Must |
| FR-1.2 | If calories are omitted, auto-calculate: `(protein * 4) + (fat * 9) + (carbs * 4)` | Must |
| FR-1.3 | User can edit an existing food entry | Must |
| FR-1.4 | User can delete a food entry | Must |
| FR-1.5 | Each entry is timestamped with date and time | Must |
| FR-1.6 | User can assign a meal type: Breakfast, Lunch, Dinner, Snack | Should |
| FR-1.7 | User can add serving size and unit (g, ml, piece, cup, tbsp) | Should |

### FR-2: Daily Dashboard

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | Show today's total: protein, fat, carbs, calories | Must |
| FR-2.2 | Show a list of all food entries for today, grouped by meal | Must |
| FR-2.3 | Show progress bars or visual indicators against daily targets | Must |
| FR-2.4 | Show macro split as a pie/donut chart (% protein, fat, carbs) | Should |
| FR-2.5 | Quick-add from recently used foods (last 20 unique entries) | Should |

### FR-3: Daily Targets

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | User can set daily targets for protein, fat, carbs, and calories | Must |
| FR-3.2 | Targets persist across sessions | Must |
| FR-3.3 | Dashboard shows remaining vs. consumed for each macro | Must |
| FR-3.4 | Visual warning when a target is exceeded | Should |

### FR-4: History & Trends

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | User can view entries for any past date via a date picker | Must |
| FR-4.2 | Weekly summary view: average daily intake per macro | Should |
| FR-4.3 | Line chart showing daily totals over the past 7 / 14 / 30 days | Should |
| FR-4.4 | Export data to CSV | Could |

### FR-5: Food Database (Saved Foods)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | User can save a food item to a personal "My Foods" library | Should |
| FR-5.2 | When adding an entry, user can search saved foods by name | Should |
| FR-5.3 | Saved foods store: name, default serving size, protein, fat, carbs per serving | Should |
| FR-5.4 | User can edit or delete saved foods | Should |

### FR-6: Authentication (Deploy Mode)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-6.1 | When `AUTH_ENABLED=true`, require login to access the app | Could |
| FR-6.2 | Simple username/password auth with hashed passwords | Could |
| FR-6.3 | Single-user mode by default (no registration page unless configured) | Could |

---

## 3. Non-Functional Requirements

| ID | Requirement | Details |
|----|-------------|---------|
| NFR-1 | **Performance** | Page loads < 500ms locally; all queries indexed |
| NFR-2 | **Portability** | Runs on Windows, macOS, Linux with `python app.py` |
| NFR-3 | **Zero external dependencies at runtime** | No API calls, no internet required for core features |
| NFR-4 | **Deploy in < 5 minutes** | Dockerfile + `docker-compose.yml` provided; single `docker compose up` |
| NFR-5 | **Data safety** | SQLite WAL mode; no data loss on crash |
| NFR-6 | **Responsive UI** | Usable on mobile browsers (phone-first layout for quick logging) |
| NFR-7 | **Accessibility** | Semantic HTML, form labels, keyboard navigable |
| NFR-8 | **Testability** | Pytest test suite with > 80% route coverage |

---

## 4. Use Cases

### UC-1: Log a Meal

**Actor:** User
**Precondition:** App is running, dashboard is open
**Main Flow:**
1. User clicks "Add Food" button
2. Form appears with fields: food name, protein, fat, carbs, calories (optional), meal type, serving size
3. User fills in the fields (or searches saved foods to auto-fill)
4. User clicks "Save"
5. Entry appears in today's list; dashboard totals update immediately
**Alternate Flow:**
- 3a. User selects from "Recent Foods" — fields auto-populate
- 3b. User selects from "My Foods" library — fields auto-populate
**Postcondition:** Entry saved to database, daily totals recalculated

### UC-2: Set Daily Targets

**Actor:** User
**Precondition:** App is running
**Main Flow:**
1. User navigates to Settings/Targets page
2. User enters target values for protein, fat, carbs, and calories
3. User clicks "Save Targets"
4. Dashboard progress bars reflect the new targets
**Postcondition:** Targets stored in database, used for all future dashboard renders

### UC-3: Review Today's Progress

**Actor:** User
**Precondition:** User has logged at least one entry today
**Main Flow:**
1. User opens the app (lands on dashboard)
2. Dashboard shows: total protein/fat/carbs/calories consumed today
3. Progress bars show percentage of daily target reached
4. Donut chart shows macro split
5. Food list shows all entries grouped by meal type
**Postcondition:** None (read-only)

### UC-4: View Historical Data

**Actor:** User
**Precondition:** User has logged entries on past days
**Main Flow:**
1. User clicks on "History" tab
2. Date picker defaults to today; user selects a past date
3. Page shows that date's entries and totals
4. User switches to "Trends" view
5. Line chart shows daily totals over selected period (7/14/30 days)
**Postcondition:** None (read-only)

### UC-5: Manage Saved Foods

**Actor:** User
**Precondition:** App is running
**Main Flow:**
1. User navigates to "My Foods" page
2. User clicks "Add Food to Library"
3. User enters: food name, serving size, protein, fat, carbs per serving
4. User clicks "Save"
5. Food appears in the library and is now searchable when logging meals
**Alternate Flow:**
- 5a. User edits an existing saved food
- 5b. User deletes a saved food
**Postcondition:** Food library updated

### UC-6: Edit or Delete an Entry

**Actor:** User
**Precondition:** Entry exists for today or a past date
**Main Flow:**
1. User finds the entry in the daily list
2. User clicks "Edit" — form pre-fills with current values
3. User modifies values and clicks "Save"
4. Totals recalculate
**Alternate Flow:**
- 2a. User clicks "Delete" — confirmation dialog appears — entry removed
**Postcondition:** Database updated, totals recalculated

### UC-7: Quick-Add from Recent Foods

**Actor:** User
**Precondition:** User has logged foods before
**Main Flow:**
1. User clicks "Quick Add" on the dashboard
2. A list of the 20 most recently used unique food names appears
3. User clicks one — the add-food form pre-fills with that food's last-used macros
4. User adjusts serving size if needed and saves
**Postcondition:** New entry created

### UC-8: Export Data

**Actor:** User
**Precondition:** User has logged entries
**Main Flow:**
1. User goes to History page
2. User clicks "Export CSV"
3. Browser downloads a CSV file with columns: date, meal, food_name, serving_size, protein, fat, carbs, calories
**Postcondition:** CSV file downloaded

---

## 5. Data Model

### Table: `food_entry`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO_INCREMENT | Unique entry ID |
| food_name | VARCHAR(200) | NOT NULL | Name of the food |
| protein | FLOAT | NOT NULL, >= 0 | Grams of protein |
| fat | FLOAT | NOT NULL, >= 0 | Grams of fat |
| carbs | FLOAT | NOT NULL, >= 0 | Grams of carbohydrates |
| calories | FLOAT | NOT NULL, >= 0 | Total calories |
| meal_type | VARCHAR(20) | DEFAULT 'Snack' | Breakfast/Lunch/Dinner/Snack |
| serving_size | FLOAT | NULLABLE | Amount consumed |
| serving_unit | VARCHAR(20) | DEFAULT 'g' | g, ml, piece, cup, tbsp |
| entry_date | DATE | NOT NULL, INDEXED | Date of consumption |
| entry_time | TIME | NOT NULL | Time of consumption |
| created_at | DATETIME | DEFAULT NOW | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW | Last update timestamp |

### Table: `daily_target`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Unique ID |
| protein | FLOAT | NOT NULL | Target grams of protein |
| fat | FLOAT | NOT NULL | Target grams of fat |
| carbs | FLOAT | NOT NULL | Target grams of carbs |
| calories | FLOAT | NOT NULL | Target calories |
| effective_from | DATE | NOT NULL | When this target starts |
| created_at | DATETIME | DEFAULT NOW | Record creation timestamp |

### Table: `saved_food`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO_INCREMENT | Unique food ID |
| name | VARCHAR(200) | NOT NULL, UNIQUE | Food name |
| protein | FLOAT | NOT NULL | Protein per serving |
| fat | FLOAT | NOT NULL | Fat per serving |
| carbs | FLOAT | NOT NULL | Carbs per serving |
| calories | FLOAT | NOT NULL | Calories per serving |
| default_serving | FLOAT | DEFAULT 100 | Default serving size |
| serving_unit | VARCHAR(20) | DEFAULT 'g' | Default unit |
| created_at | DATETIME | DEFAULT NOW | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW | Last update timestamp |

### Table: `user` (deploy mode only)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Unique user ID |
| username | VARCHAR(80) | NOT NULL, UNIQUE | Login username |
| password_hash | VARCHAR(256) | NOT NULL | Bcrypt hashed password |
| created_at | DATETIME | DEFAULT NOW | Account creation |

---

## 6. API Endpoints (REST)

### Food Entries

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/entries?date=YYYY-MM-DD` | Get all entries for a date |
| POST | `/api/entries` | Create a new food entry |
| PUT | `/api/entries/<id>` | Update an existing entry |
| DELETE | `/api/entries/<id>` | Delete an entry |
| GET | `/api/entries/recent` | Get 20 most recent unique foods |

### Daily Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/summary?date=YYYY-MM-DD` | Get totals for a specific date |
| GET | `/api/summary/range?start=YYYY-MM-DD&end=YYYY-MM-DD` | Get daily totals for a date range |

### Targets

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/targets` | Get current daily targets |
| POST | `/api/targets` | Set new daily targets |

### Saved Foods

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/foods?q=search_term` | Search saved foods |
| POST | `/api/foods` | Save a new food to library |
| PUT | `/api/foods/<id>` | Update a saved food |
| DELETE | `/api/foods/<id>` | Delete a saved food |

### Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/export?start=YYYY-MM-DD&end=YYYY-MM-DD` | Export entries as CSV |

### Pages (HTML)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard (today's view) |
| GET | `/history` | History and trends page |
| GET | `/foods` | Saved foods library |
| GET | `/settings` | Targets and preferences |

---

## 7. Project Structure

```
nutrition-tracker/
├── app.py                  # Flask app factory & entry point
├── config.py               # Configuration (env-based: dev/prod)
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container build
├── docker-compose.yml      # One-command deploy
├── .env.example            # Template for environment variables
├── .gitignore
├── REQUIREMENTS.md         # This document
├── CLAUDE.md               # Build instructions for AI assistants
│
├── instance/               # SQLite database (gitignored)
│   └── nutritrack.db
│
├── models/
│   ├── __init__.py
│   ├── food_entry.py       # FoodEntry model
│   ├── daily_target.py     # DailyTarget model
│   ├── saved_food.py       # SavedFood model
│   └── user.py             # User model (deploy mode)
│
├── routes/
│   ├── __init__.py
│   ├── entries.py          # /api/entries routes
│   ├── summary.py          # /api/summary routes
│   ├── targets.py          # /api/targets routes
│   ├── foods.py            # /api/foods routes
│   ├── export.py           # /api/export routes
│   └── pages.py            # HTML page routes
│
├── templates/
│   ├── base.html           # Base layout with nav
│   ├── dashboard.html      # Main daily view
│   ├── history.html        # History & trends
│   ├── foods.html          # Saved foods library
│   └── settings.html       # Targets configuration
│
├── static/
│   ├── css/
│   │   └── style.css       # App styles (mobile-first)
│   └── js/
│       ├── app.js           # Shared utilities, API calls
│       ├── dashboard.js     # Dashboard logic & charts
│       ├── history.js       # History page logic
│       └── foods.js         # Saved foods page logic
│
└── tests/
    ├── conftest.py          # Pytest fixtures (test client, test db)
    ├── test_entries.py      # Entry CRUD tests
    ├── test_summary.py      # Summary calculation tests
    ├── test_targets.py      # Target setting tests
    └── test_foods.py        # Saved foods tests
```

---

## 8. Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Backend** | Flask 3.x | Lightweight, well-documented, full control over routing and templates |
| **ORM** | Flask-SQLAlchemy | Simplifies DB operations, handles migrations |
| **Migrations** | Flask-Migrate (Alembic) | Schema versioning for deploy |
| **Database (local)** | SQLite | Zero setup, single file, perfect for local use |
| **Database (deploy)** | PostgreSQL | Robust, free tier on most cloud providers |
| **Frontend** | Vanilla HTML/CSS/JS | No build step, minimal complexity |
| **Charts** | Chart.js (CDN) | Simple, responsive charts with zero bundling |
| **CSS Framework** | None (custom, mobile-first) | Full control, no unnecessary bloat |
| **Testing** | Pytest + Flask test client | Standard, fast, good coverage tooling |
| **Containerization** | Docker + docker-compose | One-command deployment |

---

## 9. Configuration & Environment

```bash
# .env.example
FLASK_ENV=development          # development | production
SECRET_KEY=change-me-in-prod   # Flask session secret
DATABASE_URL=sqlite:///instance/nutritrack.db  # Override for PostgreSQL
AUTH_ENABLED=false              # Enable login requirement
DEFAULT_PROTEIN_TARGET=150     # Default daily protein target (g)
DEFAULT_FAT_TARGET=65          # Default daily fat target (g)
DEFAULT_CARBS_TARGET=250       # Default daily carbs target (g)
DEFAULT_CALORIES_TARGET=2200   # Default daily calorie target
```

---

## 10. Deployment Checklist

- [ ] Set `FLASK_ENV=production`
- [ ] Set a strong `SECRET_KEY`
- [ ] Set `DATABASE_URL` to PostgreSQL connection string
- [ ] Set `AUTH_ENABLED=true` and create a user account
- [ ] Run `flask db upgrade` to initialize the production database
- [ ] Build and run with `docker compose up -d`
- [ ] Verify the app loads at the configured URL

---

## 11. Development Phases

### Phase 1: Core (MVP) - Must Have
1. Project setup (Flask app, config, database models)
2. Food entry CRUD (add, edit, delete entries)
3. Daily dashboard (today's totals, entry list)
4. Daily targets (set and display progress)
5. Basic styling (clean, mobile-friendly)

### Phase 2: Enhanced UX - Should Have
6. Meal type grouping on dashboard
7. Macro donut chart (Chart.js)
8. Quick-add from recent foods
9. Saved foods library (My Foods)
10. History page with date picker
11. Weekly trends chart

### Phase 3: Production Ready - Could Have
12. CSV export
13. Authentication (deploy mode)
14. Dockerfile + docker-compose
15. Test suite (pytest)
16. CI/CD pipeline (GitHub Actions)

---

## 12. Acceptance Criteria (Phase 1 MVP)

The MVP is complete when:

1. **User can add a food entry** with name, protein, fat, carbs, and optional calories
2. **Calories auto-calculate** when omitted
3. **Dashboard shows today's totals** for all four macros
4. **Dashboard lists all entries** for today
5. **User can edit and delete entries**
6. **User can set daily targets** that persist
7. **Progress bars** show consumed vs. target for each macro
8. **App runs locally** with `python app.py` and no external dependencies
9. **Mobile-responsive** layout works on a phone browser
10. **Data persists** across app restarts (SQLite)
