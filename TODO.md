# NutriTrack — TODO & Future Features

## Bugs (known)
- [x] **Unit dropdown not scaling macros correctly** — FIXED 2026-08: base macro tracking added to meal template item rows
- [x] **Meal dataset missing** — seed_data/meals.py exists and seeds meal rows on first run
- [x] **Food macro data wrong (per-100g stored as per-serving)** — FIXED 2026-08: fix_food_data.py corrected 69 foods (eggs, butter, condiments, etc.)

## Language Support
- [x] **Turkish UI translation** — DONE: i18n.js module with EN/TR dictionaries, lang toggle in nav, data-i18n attributes throughout
- [ ] **Turkish meal dataset** — curate common Turkish dishes (mercimek çorbası, mantı, iskender, döner, karnıyarık, börek, menemen, pilav, köfte, dolma…) with per-serving macros
- [ ] **Country-specific meal datasets** — extend seeding infrastructure for per-country datasets selectable in Settings

## Dataset & Food Library
- [x] **Bundle seed foods CSV** — 751 USDA foods in seed_data/foods.csv, auto-seeded on first run
- [ ] **OpenFoodFacts API fallback** — `GET https://search.openfoodfacts.org/search?q={query}` fallback when food not in local DB
- [ ] **USDA FoodData Central API (optional)** — opt-in via `USDA_API_KEY` env var

## Deploy
- [x] **GitHub repo** — pushed to https://github.com/sakaryag/nutrition-tracker
- [ ] **Deploy to Railway / Render / Fly.io** — Docker setup ready, needs env vars set
- [ ] **PostgreSQL in production** — `DATABASE_URL` swap works, needs provisioning
- [x] **Docker setup** — Dockerfile + docker-compose.yml present and working

## Multi-user data isolation
- [x] **user_id FK on food_entry** — present and filtered when AUTH_ENABLED
- [x] **daily_target user scoping** — filtered by user_id when auth enabled
- [ ] **saved_food custom foods per-user** — currently all custom foods are shared across users; add user_id FK to saved_food for source='custom'

## Barcode scanner
- [x] **Barcode input / camera scan** — ZXing-based camera barcode scanner implemented (barcode.js, integrated in dashboard)
- [x] **OpenFoodFacts lookup** — barcode scans look up via OFF API and auto-fill macros
- [x] **Save scanned food to library** — auto-saves new foods on entry creation

## Food photo recognition
- [x] **Claude vision food recognition** — photo capture → Claude Haiku identifies food and fills macros (food_image.js)

## Weekly / monthly reports
- [ ] **Average daily intake over a period** — /api/summary/range exists but no UI report page
- [ ] **Compliance rate** — % of days hitting each macro target
- [ ] **Streaks** — consecutive days of logging
- [ ] **Visual charts** — weekly bar chart, monthly calendar heatmap

## PWA support
- [ ] **manifest.json** — app name, icons, theme color
- [ ] **Service worker** — offline caching of static assets
- [ ] **"Add to Home Screen" prompt** — mobile install prompt

## Meal templates (enhancements)
- [x] **Log template to today** — template chips on dashboard log immediately
- [x] **Create template from existing log entries** — "From Log" panel added 2026-08
- [ ] **Log template to a specific past date** — currently only logs to today
- [ ] **Duplicate a template** — clone button
- [ ] **Sort/reorder template items** — drag and drop
- [ ] **Template categories / tags**

## Food library (enhancements)
- [x] **Clone a USDA food** — clone button on My Foods page
- [ ] **Import foods from CSV** — bulk import UI
- [ ] **Fuzzy search** — handle typos in food search
- [ ] **Recent search history**

## AI / Claude Integration
- [x] **Natural language food logging chatbot** — chat page with spaCy + Claude Haiku pipeline
- [x] **User-provided Claude API key** — stored in localStorage, sent per-request, never server-side
- [x] **Smart portion estimation** — Claude extracts quantities and suggests gram estimates
- [ ] **Daily summary insights** — end-of-day Claude review of macros vs targets (paragraph insight)

## Dashboard (enhancements)
- [ ] **Water intake tracker** — daily water log widget
- [ ] **Notes / mood field per day** — freetext note per date
- [ ] **Copy yesterday's entries to today** — one-tap copy

## Dietitian Plan Feature (NEW — 2026-08)
- [ ] **Admin/dietitian role** — admin flag on User model; admin UI to create nutrition plans
- [ ] **Plan model** — NutritionPlan (name, description, duration_days, created_by_admin)
- [ ] **Plan task model** — PlanTask (plan_id, day_offset, food_name/description, quantity, unit, repeat pattern)
- [ ] **User plan assignment** — assign a plan to a specific user with a start_date
- [ ] **Plan tracking UI** — calendar/table view showing tasks per day, checkmark completion
- [ ] **Settings toggle** — plan feature hidden by default, enabled per-user by admin
- [ ] **Task completion tracking** — UserPlanTaskCompletion model (user_id, task_id, date, completed)

## Quality / Production Readiness
- [ ] **OpenFoodFacts fallback search** — live API fallback in food search
- [ ] **Turkish food dataset** — 50–100 common Turkish dishes seeded
- [ ] **Reports page** — weekly/monthly compliance charts (MyFitnessPal-style)
- [ ] **PWA manifest + service worker** — installable on mobile home screen
- [ ] **Copy yesterday** — dashboard quick action
- [ ] **Daily notes** — per-day freetext notes field
- [ ] **Water tracker** — daily water intake widget
- [ ] **Duplicate meal template** — clone button
- [ ] **Migrate tests to cover new routes** — keep >80% route coverage
