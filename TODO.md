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
- [x] **Water intake tracker** — `WaterLog` model + `GET/POST /api/water` route exist; dashboard widget UI pending
- [x] **Notes / mood field per day** — `DailyNote` model + `GET/POST /api/notes` route exist; dashboard widget UI pending
- [ ] **Copy yesterday's entries to today** — one-tap copy

## Dietitian Plan Feature
- [x] **Admin/dietitian role** — `is_admin` + `plan_feature_enabled` on User model
- [x] **Plan model** — `NutritionPlan` (name, description, duration_days, created_by_admin_id)
- [x] **Plan task model** — `PlanTask` (plan_id, day_offset, food_name, quantity, unit, repeat pattern)
- [x] **User plan assignment** — `UserPlanAssignment` (user_id, plan_id, start_date)
- [x] **Task completion tracking** — `PlanTaskCompletion` model (user_id, task_id, date, completed)
- [x] **Backend routes** — `routes/plans.py` + `routes/admin.py` present
- [x] **Settings toggle** — plan nav link gated by `plan_feature_enabled` in `base.html`
- [ ] **Plan tracking UI** — `templates/plans.html` + `templates/admin.html` exist but need full implementation review

## Family Mode / Social (NEW — 2026-08)
- [x] **Friend connections** — `FriendConnection` model, `routes/friends.py`: send/accept/decline/remove
- [x] **Feed visibility** — `FeedVisibility` model, `GET/PUT /api/social/feed/visibility`
- [x] **Social feed** — `GET /api/social/feed` returns friends' daily summaries (respects privacy settings)
- [x] **Shared entries** — `SharedEntry` model, `routes/shared.py`: POST /api/shared, GET /api/shared/incoming
- [x] **Game engine** — `utils/game_engine.py`: `calculate_daily_score()`, `calculate_weekly_score()`, `get_user_streak()`, `check_and_award_badges()`
- [x] **Score/leaderboard API** — `routes/game.py`: `GET /api/game/score`, `GET /api/game/leaderboard`
- [x] **Badges** — `UserBadge` model, `GET /api/social/badges`; 6 badge types: 7_day_streak, perfect_week, protein_king, hydration_hero, early_bird, consistent_30
- [x] **Social frontend** — `templates/social.html` + `static/js/social.js`: 4-tab UI (Friends, Feed, Race, Badges)
- [x] **Friends nav link** — added to `base.html`
- [x] **20 tests** — `tests/test_family_mode.py` all passing

## Quality / Production Readiness
- [ ] **OpenFoodFacts fallback search** — live API fallback in food search
- [ ] **Turkish food dataset** — 50–100 common Turkish dishes seeded
- [ ] **Reports page** — `/api/summary/range` exists; no chart UI yet
- [ ] **PWA manifest + service worker** — installable on mobile home screen
- [ ] **Copy yesterday** — dashboard quick action
- [ ] **Water/notes dashboard widgets** — models + API routes exist, no dashboard UI
- [ ] **Duplicate meal template** — clone button
- [ ] **Audit food corrections** — workflow wf_b988d1f7 found calorie errors (peanut butter 2x, Medjool dates 14x, jams 2x, English muffin, avocado, most fruits); corrections not yet applied to foods.csv / DB
- [ ] **valid_units filtering** — column exists on saved_food but food search unit dropdown not filtered by it
- [ ] **Test coverage for new routes** — friends/game/social/shared/notes/water routes not yet in test_api.py
