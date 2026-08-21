# NutriTrack — TODO & Future Features

## Language Support
- [ ] **Turkish meal dataset** — curate common Turkish dishes (mercimek çorbası, mantı, iskender, döner, karnıyarık, börek, menemen, pilav, köfte, dolma…) with per-serving macros
- [ ] **Country-specific meal datasets** — extend seeding infrastructure for per-country datasets selectable in Settings

## Dataset & Food Library
- [ ] **OpenFoodFacts API fallback** — `GET https://search.openfoodfacts.org/search?q={query}` fallback when food not in local DB
- [ ] **USDA FoodData Central API (optional)** — opt-in via `USDA_API_KEY` env var

## Deploy
- [ ] **Deploy to Railway / Render / Fly.io** — Docker setup ready, needs env vars set
- [ ] **PostgreSQL in production** — `DATABASE_URL` swap works, needs provisioning

## Multi-user data isolation
- [ ] **saved_food custom foods per-user** — currently all custom foods are shared across users; add user_id FK to saved_food for source='custom'

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
- [ ] **Log template to a specific past date** — currently only logs to today
- [ ] **Duplicate a template** — clone button
- [ ] **Sort/reorder template items** — drag and drop
- [ ] **Template categories / tags**

## Food library (enhancements)
- [ ] **Import foods from CSV** — bulk import UI
- [ ] **Fuzzy search** — handle typos in food search
- [ ] **Recent search history**

## AI / Claude Integration
- [ ] **Daily summary insights** — end-of-day Claude review of macros vs targets (paragraph insight)

## Dashboard (enhancements)
- [ ] **Water/notes dashboard widgets** — `WaterLog` + `DailyNote` models and API routes exist; no dashboard UI yet
- [ ] **Copy yesterday's entries to today** — one-tap copy

## Dietitian Mode
- [ ] **Plans/Admin page full UI** — `templates/plans.html` + `templates/admin.html` are stubs; need full dietitian workflow UI

## Quality / Production Readiness
- [ ] **Full food data audit (strict)** — every food in the DB must have correct per-100g macros (protein/fat/carbs/calories) verified against USDA FoodData Central source values. Known errors from workflow wf_b988d1f7: peanut butters ~2× calories, Medjool dates ~14× calories, jams ~2×, English muffin stored as per-piece not per-100g, avocado whole-fruit vs per-100g, most fresh fruits wrong. Audit scope: (1) re-download USDA FDC data for all 751 seeded foods and diff against current foods.csv, (2) flag every food where stored kcal deviates >5% from calculated `(protein×4 + fat×9 + carbs×4)`, (3) apply corrections to foods.csv and re-seed. No food correction should be applied without cross-checking the FDC source; do not guess values.
- [ ] **valid_units filtering** — column exists on saved_food but food search unit dropdown not filtered by it
- [ ] **Test coverage for new routes** — friends/game/social/shared/notes/water routes not yet in test_api.py
- [ ] **OpenFoodFacts fallback search** — live API fallback in food search
- [ ] **Turkish food dataset** — 50–100 common Turkish dishes seeded
- [ ] **Reports page** — `/api/summary/range` exists; no chart UI yet
- [ ] **PWA manifest + service worker** — installable on mobile home screen
- [ ] **Duplicate meal template** — clone button
