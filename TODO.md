# NutriTrack — TODO & Future Features

## Language Support
- [x] **Turkish meal dataset** — 65 authentic Turkish dishes seeded via seed_turkish_meals() in seed_data/meals.py (PR9); covers soups, kebabs, pilavs, börek, mezze, salads, desserts, drinks
- [ ] **Country-specific meal datasets** — extend seeding infrastructure for per-country datasets selectable in Settings

## Dataset & Food Library
- [x] **OpenFoodFacts API fallback** — already implemented in `routes/foods.py` (`_fetch_openfoodfacts()`)
- [x] **Fuzzy search** — rapidfuzz WRatio matching triggered when LIKE search returns <5 results (PR13)
- [x] **Import foods from CSV** — bulk import UI at /foods → Import CSV button; validates columns, auto-calcs calories, skips duplicates, 500-row cap (PR13)
- [x] **Recent search history** — localStorage-backed, shown on focus, max 10 entries (PR13)
- [ ] **USDA FoodData Central API (optional)** — opt-in via `USDA_API_KEY` env var (deferred — 817 foods already seeded)

## Multi-user data isolation
- [ ] **saved_food custom foods per-user** — currently all custom foods are shared across users; add user_id FK to saved_food for source='custom' (deferred)

## Weekly / monthly reports
- [x] **Reports page** — fully built; nav link restored (PR4). Compliance rate, streaks, charts at `/reports`
- [x] **Monthly calendar heatmap** — calendar heat-map added to reports page with prev/next month nav, color-coded compliance cells, tooltip on hover (PR11)

## PWA support
- [x] **manifest.json + service worker** — already built; fixed manifest path bug + SW precache bug (PR5)
- [x] **"Add to Home Screen" prompt** — enabled by fixed manifest

## Meal templates (enhancements)
- [x] **Log template to a specific past date** — date-picker modal on each template card (PR14)
- [x] **Duplicate a template** — clone button on template cards via POST /api/meal-templates/<id>/clone (PR14)
- [x] **Sort/reorder template items** — native HTML5 drag & drop, persisted via PUT /api/meal-templates/<id>/reorder (PR14)
- [x] **Template categories / tags** — category field on template; filter bar dynamically built from loaded templates (PR14)

## Recipe Builder
- [x] **Recipe builder** — full CRUD at /recipes; ingredient food search, live macro preview with piece/slice/serving unit scaling, per-serving/total toggle, log-to-date, save-as-food (PR15)

## AI / Claude Integration
- [x] **Daily summary insights** — "✨ Daily Insight" button on dashboard; reads current macro values, POSTs to /api/chat with user's API key (PR12)

## Social / Family Mode
- [x] **Emoji reactions on social feed** — 👏🔥💪 reactions on friend feed cards; toggle/update/remove; inline count update without reload (PR16)

## Dashboard (enhancements)
- [x] **Water/notes dashboard widgets** — fully built (WaterLog + DailyNote models, API routes, dashboard UI)
- [x] **Copy yesterday's entries to today** — implemented (`POST /api/entries/copy-yesterday`)
- [x] **Meal-type subtotals** — diary entries grouped by meal type with per-section macro subtotals (PR2)
- [x] **Remaining macros panel** — shows how much protein/fat/carbs/calories remain for the day, with visual bar and food suggestions (PR12)
- [x] **Per-meal "+ Add" buttons** — quick add button in every meal section including "Other" (PR12)

## Dietitian Mode
- [x] **Plans/Admin page full UI** — full dietitian workflow UI built in templates/plans.html + templates/admin.html (PR10)
- [x] **Plan slot items without food link** — SlotItem now has protein/fat/carbs/calories columns; dashboard JS uses slot item macros when no saved_food linked (PR6)
- [x] **Dietitian plan builder macro input UI** — admin.html frontend fields for entering macros on free-text slot items (PR10)

## Quality / Production Readiness
- [ ] **Full food data audit (strict)** — P1+P2 known errors fixed (PR1: peanut butters, Medjool dates, jams, English muffins, avocado, watermelon, hemp seeds). Full systematic diff vs USDA FDC source for all 751 foods still pending.
- [x] **valid_units filtering** — unit dropdown in food search now filtered by saved_food.valid_units (PR6)
- [x] **Test coverage for admin routes** — 108 tests added for /api/admin/* routes + 14 quota CRUD tests (PR8). 342 total tests.
- [x] **Test coverage for new routes** — water/notes/shared/friends/game/social + seed data correctness
- [x] **OpenFoodFacts fallback search** — already implemented
- [x] **Turkish food dataset** — 65 authentic Turkish dishes seeded (PR9)
- [ ] **datetime.utcnow() deprecation warnings** — entries.py, water.py, notes.py, shared.py use deprecated `datetime.utcnow()`. Replace with `datetime.now(timezone.utc)` (Python 3.12+).
- [ ] **Auto-seed Turkish meals on startup** — seed_meals() / seed_turkish_meals() are not called from app.py startup; new deployments require a manual `python seed_data/meals.py` run.
