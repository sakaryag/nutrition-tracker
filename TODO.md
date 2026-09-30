# NutriTrack — TODO & Future Features

## Language Support
- [ ] **Turkish meal dataset** — curate common Turkish dishes (mercimek çorbası, mantı, iskender, döner, karnıyarık, börek, menemen, pilav, köfte, dolma…) with per-serving macros
- [ ] **Country-specific meal datasets** — extend seeding infrastructure for per-country datasets selectable in Settings

## Dataset & Food Library
- [x] **OpenFoodFacts API fallback** — already implemented in `routes/foods.py` (`_fetch_openfoodfacts()`)
- [ ] **USDA FoodData Central API (optional)** — opt-in via `USDA_API_KEY` env var (deferred — 817 foods already seeded)

## Multi-user data isolation
- [ ] **saved_food custom foods per-user** — currently all custom foods are shared across users; add user_id FK to saved_food for source='custom' (deferred)

## Weekly / monthly reports
- [x] **Reports page** — fully built; nav link restored (PR4). Compliance rate, streaks, charts at `/reports`
- [ ] **Monthly calendar heatmap** — not yet added to reports page

## PWA support
- [x] **manifest.json + service worker** — already built; fixed manifest path bug + SW precache bug (PR5)
- [x] **"Add to Home Screen" prompt** — enabled by fixed manifest

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
- [x] **Water/notes dashboard widgets** — fully built (WaterLog + DailyNote models, API routes, dashboard UI)
- [x] **Copy yesterday's entries to today** — implemented (`POST /api/entries/copy-yesterday`)
- [x] **Meal-type subtotals** — diary entries grouped by meal type with per-section macro subtotals (PR2)

## Dietitian Mode
- [ ] **Plans/Admin page full UI** — `templates/plans.html` + `templates/admin.html` are stubs; full dietitian workflow UI not built
- [x] **Plan slot items without food link** — SlotItem now has protein/fat/carbs/calories columns; dashboard JS uses slot item macros when no saved_food linked (PR6)
- [ ] **Dietitian plan builder macro input UI** — admin.html needs frontend fields for entering macros on free-text slot items

## Quality / Production Readiness
- [ ] **Full food data audit (strict)** — P1+P2 known errors fixed (PR1: peanut butters, Medjool dates, jams, English muffins, avocado, watermelon, hemp seeds). Full systematic diff vs USDA FDC source for all 751 foods still pending.
- [x] **valid_units filtering** — unit dropdown in food search now filtered by saved_food.valid_units (PR6)
- [x] **Test coverage for new routes** — 40 new tests added (PR7): water/notes/shared/friends/game/social + seed data correctness. 167 total tests.
- [x] **OpenFoodFacts fallback search** — already implemented
- [ ] **Turkish food dataset** — 50–100 common Turkish dishes seeded
- [ ] **Duplicate meal template** — clone button
- [ ] **datetime.utcnow() deprecation warnings** — entries.py, water.py, notes.py, shared.py use deprecated `datetime.utcnow()`. Replace with `datetime.now(timezone.utc)` (Python 3.12+).
- [ ] **No tests for admin routes** — /api/admin/* routes have no test coverage