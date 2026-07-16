# NutriTrack — TODO & Future Features

## Bugs (known)
- [ ] **Unit dropdown not scaling macros correctly** — changing unit in meal template items does not proportionally rescale macros. The serving number updates but macro values stay stale. Needs proper base-macro tracking per item row. (Added 2026-07)
- [ ] **Meal dataset missing** — the Meals filter in template search returns empty; no whole-dish entries are seeded yet. Needs a real nutritional dataset for meals. (Added 2026-07)

## Language Support
- [ ] **Turkish UI translation** — add i18n support so all labels, buttons, toasts, and placeholders can be shown in Turkish. Suggested approach: a `static/js/i18n.js` module with `tr` and `en` dictionaries, a language toggle in Settings, and `data-i18n="key"` attributes on all translatable HTML elements.
- [ ] **Turkish meal dataset** — curate or source a dataset of common Turkish dishes (mercimek çorbası, manti, iskender, döner, karnıyarık, börek, menemen, pilav, köfte, dolma…) with accurate per-100g macros. Consider OpenFoodFacts Turkey data or USDA SR Legacy as a base.
- [ ] **Country-specific meal datasets** — extend the meal seeding infrastructure to support per-country datasets (e.g. Italian, Turkish, Mexican) selectable in Settings.

## Deploy
- [ ] Push to GitHub repo `https://github.com/sakaryag/nutrition-tracker`
- [ ] Deploy to Railway / Render / Fly.io
- [ ] Set `DATABASE_URL` to a PostgreSQL instance
- [ ] Set `AUTH_ENABLED=true` and `SECRET_KEY` to a secure random value in production
- [ ] Docker setup is ready: `docker compose up --build`

## Multi-user data isolation
- [ ] Add `user_id` FK to `food_entry`, `daily_target`, `saved_food` (custom only)
- [ ] Filter all queries by `session['user_id']` when auth is enabled
- [ ] Migrate existing data to a default user

## Barcode scanner
- [ ] Add barcode input field (camera or manual entry)
- [ ] Look up via OpenFoodFacts API (`https://world.openfoodfacts.org/api/v2/product/{barcode}.json`)
- [ ] Auto-fill name, macros, serving from API response
- [ ] Option to save scanned food to custom library

## Weekly / monthly reports
- [ ] Average daily intake over a period
- [ ] Compliance rate: % of days hitting each macro target
- [ ] Streaks: consecutive days of logging
- [ ] Visual charts: weekly bar chart, monthly heatmap

## PWA support
- [ ] Add `manifest.json` with app name, icons, theme color
- [ ] Add service worker for offline caching of static assets
- [ ] Cache API responses for offline viewing of recent data
- [ ] "Add to Home Screen" prompt on mobile

## Meal templates (enhancements)
- [ ] Log a template to a specific past date (currently only logs to today)
- [ ] Duplicate a template
- [ ] Sort/reorder template items via drag and drop
- [ ] Template categories / tags

## Food library (enhancements)
- [ ] Clone a USDA food to edit its macros/serving
- [ ] Import foods from CSV
- [ ] Fuzzy search (handle typos)
- [ ] Recent search history

## Dashboard (enhancements)
- [ ] Water intake tracker
- [ ] Notes / mood field per day
- [ ] Copy yesterday's entries to today
