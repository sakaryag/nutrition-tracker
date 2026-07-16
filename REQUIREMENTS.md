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

### FR-5: Food Database

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | App ships with a **seed database** of ~800-1000 common foods (sourced from USDA FoodData Central) pre-loaded into `saved_food` table on first run | Must |
| FR-5.2 | Seed foods are marked `source='usda'`; user-created foods are marked `source='custom'` | Must |
| FR-5.3 | When adding an entry, user can **search all foods** (seed + custom) by name with type-ahead | Must |
| FR-5.4 | Search results show the source badge (USDA / Custom) so user knows the origin | Should |
| FR-5.5 | User can **add custom foods** to the library with: name, serving size, protein, fat, carbs | Must |
| FR-5.6 | User can **edit or delete custom foods** | Must |
| FR-5.7 | USDA seed foods are **read-only** — user cannot edit or delete them, but can "clone" one to create an editable custom copy | Should |
| FR-5.8 | User can **override serving size** when logging any food (seed or custom) without changing the library entry | Must |
| FR-5.9 | "My Foods" page shows two tabs/sections: Custom Foods (editable) and USDA Foods (searchable, read-only) | Should |
| FR-5.10 | Seed database is loaded via `flask seed` CLI command; runs automatically on first app start if the table is empty | Must |

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

## 5. Database Strategy

### Local Mode (Default)

- **Engine:** SQLite 3
- **Location:** `instance/nutritrack.db` (auto-created on first run)
- **Why:** Zero installation, no background process, single file you can copy/backup
- **WAL mode** enabled for crash safety and concurrent reads

### Cloud / Deploy Mode

- **Engine:** PostgreSQL 14+
- **Why PostgreSQL over alternatives:**

| Option | Verdict | Reason |
|--------|---------|--------|
| **PostgreSQL** | **Chosen** | Best free tiers (Neon, Supabase, Render, Railway), full SQL standard, JSON support, excellent with SQLAlchemy, scales to millions of rows |
| MySQL/MariaDB | Viable | Good but fewer free cloud options; PostgreSQL has better type system |
| MongoDB | Rejected | Nutrition data is inherently relational (entries -> dates, targets -> dates); NoSQL adds complexity with no benefit here |
| Cloud-only (Firestore, DynamoDB) | Rejected | Vendor lock-in, can't run locally without emulators, breaks the local-first principle |

### How the Swap Works

The entire switch is **one environment variable**:

```bash
# Local (default — no setup needed)
DATABASE_URL=sqlite:///instance/nutritrack.db

# Cloud PostgreSQL (just change this line)
DATABASE_URL=postgresql://user:password@host:5432/nutritrack
```

**What makes this seamless:**

1. **Flask-SQLAlchemy** abstracts the database — all models, queries, and migrations work identically on both engines
2. **Alembic migrations** (`flask db upgrade`) handle schema creation on any supported engine
3. **No raw SQL anywhere** — everything goes through the ORM, so no SQLite-specific syntax leaks into the code
4. **`config.py`** reads `DATABASE_URL` from environment with SQLite as the fallback default
5. **Data types are portable** — we use `Float`, `String`, `Date`, `DateTime` which map cleanly to both engines

### Migration Path (Local to Cloud)

1. Provision a PostgreSQL instance (e.g., free tier on Neon/Supabase/Render)
2. Set `DATABASE_URL` to the PostgreSQL connection string
3. Run `flask db upgrade` to create tables in PostgreSQL
4. (Optional) Export local SQLite data to CSV and import, or use `pgloader` for direct migration
5. That's it — the app now runs against PostgreSQL

### Database Dependencies

```
# requirements.txt
Flask-SQLAlchemy     # ORM (works with any SQL engine)
Flask-Migrate        # Alembic-based migrations
psycopg2-binary      # PostgreSQL driver (only needed for deploy; harmless to install locally)
```

`psycopg2-binary` is included in `requirements.txt` from the start so there's no "oh I need to install something" surprise at deploy time. It has no effect when running with SQLite.

---

## 6. Data Model

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
| saved_food_id | INTEGER | FK -> saved_food.id, NULLABLE | Link to saved food (if selected from library) |
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
| name | VARCHAR(200) | NOT NULL | Food name |
| brand | VARCHAR(200) | NULLABLE | Brand or description (e.g., "generic", "Chobani") |
| source | VARCHAR(20) | NOT NULL, DEFAULT 'custom' | `'usda'` = seed data, `'custom'` = user-created |
| usda_fdc_id | INTEGER | NULLABLE, UNIQUE (when set) | USDA FoodData Central ID for traceability |
| category | VARCHAR(100) | NULLABLE | Food category (e.g., "Dairy", "Meat", "Grains") |
| protein | FLOAT | NOT NULL | Protein per serving (g) |
| fat | FLOAT | NOT NULL | Fat per serving (g) |
| carbs | FLOAT | NOT NULL | Carbs per serving (g) |
| calories | FLOAT | NOT NULL | Calories per serving (kcal) |
| fiber | FLOAT | NULLABLE | Fiber per serving (g) — optional extra nutrient |
| sugar | FLOAT | NULLABLE | Sugar per serving (g) — optional extra nutrient |
| default_serving | FLOAT | DEFAULT 100 | Default serving size |
| serving_unit | VARCHAR(20) | DEFAULT 'g' | Default unit |
| is_archived | BOOLEAN | DEFAULT false | Soft-delete for custom foods |
| created_at | DATETIME | DEFAULT NOW | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW | Last update timestamp |

**Indexes:** `(name)` for search, `(source)` for filtering, `(category)` for grouping, `(usda_fdc_id)` for lookups

### Table: `user` (deploy mode only)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Unique user ID |
| username | VARCHAR(80) | NOT NULL, UNIQUE | Login username |
| password_hash | VARCHAR(256) | NOT NULL | Bcrypt hashed password |
| created_at | DATETIME | DEFAULT NOW | Account creation |

---

## 7. Seed Food Database

### Data Source

**USDA FoodData Central** — Foundation Foods + SR Legacy datasets (public domain, no license issues).

- Download URL: `https://fdc.nal.usda.gov/download-datasets`
- Format: CSV bulk download
- We extract only the fields we need and curate to ~800-1000 common foods

### Curation Criteria

The seed list is NOT the full 380k USDA dump. We select foods that people actually log daily:

| Category | Example Foods | ~Count |
|----------|--------------|--------|
| Protein | Chicken breast, eggs, salmon, ground beef, tofu, Greek yogurt, whey protein | ~120 |
| Dairy | Milk (whole/skim), cheese (cheddar, mozzarella), butter, cream cheese | ~60 |
| Grains & Bread | White/brown rice, oats, pasta, bread (white/wheat), tortilla, quinoa | ~80 |
| Fruits | Banana, apple, strawberry, blueberry, orange, avocado, mango | ~60 |
| Vegetables | Broccoli, spinach, potato, sweet potato, tomato, onion, carrot | ~80 |
| Legumes & Nuts | Black beans, lentils, chickpeas, almonds, peanut butter, walnuts | ~50 |
| Oils & Fats | Olive oil, coconut oil, butter, mayo | ~20 |
| Snacks & Sweets | Dark chocolate, honey, granola bar, chips, ice cream | ~40 |
| Beverages | Orange juice, coffee (black), almond milk, soda, beer, wine | ~30 |
| Condiments | Ketchup, mustard, soy sauce, hot sauce, salsa, hummus | ~30 |
| Common Meals | Pizza slice, burger patty, fried egg, scrambled eggs, oatmeal | ~50 |

### Seed Script

- `seed_data/foods.csv` — curated food list with columns: `usda_fdc_id, name, brand, category, protein, fat, carbs, calories, fiber, sugar, default_serving, serving_unit`
- `seed_data/seed.py` — script that reads the CSV and bulk-inserts into `saved_food` table with `source='usda'`
- Registered as Flask CLI command: `flask seed`
- Auto-runs on first app start if `saved_food` table is empty
- Idempotent: skips foods that already exist (matched by `usda_fdc_id`)

### Custom Foods on Top

Users add their own foods via the UI or API. Custom foods:
- Have `source='custom'` and no `usda_fdc_id`
- Are fully editable and deletable
- Appear alongside USDA foods in search results (marked with a "Custom" badge)
- Can duplicate a USDA food name (e.g., user's own "Chicken Breast" with different macros)

---

## 8. API Endpoints (REST)

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

## 9. Project Structure

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
├── seed_data/
│   ├── foods.csv           # Curated ~800-1000 USDA foods
│   └── seed.py             # Seed script (flask seed CLI command)
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

## 10. Technology Choices

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

## 11. Configuration & Environment

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

## 12. Deployment Checklist

- [ ] Set `FLASK_ENV=production`
- [ ] Set a strong `SECRET_KEY`
- [ ] Set `DATABASE_URL` to PostgreSQL connection string
- [ ] Set `AUTH_ENABLED=true` and create a user account
- [ ] Run `flask db upgrade` to initialize the production database
- [ ] Build and run with `docker compose up -d`
- [ ] Verify the app loads at the configured URL

---

## 13. Development Phases

### Phase 1: Core (MVP) - Must Have
1. Project setup (Flask app, config, database models)
2. **Seed food database** — curate ~800-1000 USDA foods, `flask seed` command, auto-seed on first run
3. Food entry CRUD (add, edit, delete entries) with **food search** from seed + custom library
4. **Custom food management** — add/edit/delete custom foods
5. Daily dashboard (today's totals, entry list)
6. Daily targets (set and display progress)
7. Basic styling (clean, mobile-friendly)

### Phase 2: Enhanced UX - Should Have
8. Meal type grouping on dashboard
9. Macro donut chart (Chart.js)
10. Quick-add from recent foods
11. My Foods page (Custom vs USDA tabs, clone USDA to custom)
12. History page with date picker
13. Weekly trends chart

### Phase 3: Production Ready - Could Have
14. CSV export
15. Authentication (deploy mode)
16. Dockerfile + docker-compose
17. Test suite (pytest)
18. CI/CD pipeline (GitHub Actions)

---

## 14. Acceptance Criteria (Phase 1 MVP)

The MVP is complete when:

1. **App starts** with `python app.py` and auto-seeds ~800-1000 USDA foods on first run
2. **User can search foods** by name (type-ahead) and select from seed or custom foods
3. **User can add a food entry** with name, protein, fat, carbs, and optional calories
4. **Calories auto-calculate** when omitted
5. **User can add custom foods** to the library
6. **User can edit and delete custom foods** (USDA foods are read-only)
7. **Dashboard shows today's totals** for all four macros
8. **Dashboard lists all entries** for today
9. **User can edit and delete entries**
10. **User can set daily targets** that persist
11. **Progress bars** show consumed vs. target for each macro
12. **Mobile-responsive** layout works on a phone browser
13. **Data persists** across app restarts (SQLite)
14. **Database is swappable** — setting `DATABASE_URL` to a PostgreSQL string works with no code changes
