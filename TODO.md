# NutriTrack — TODO & Future Features

## Bugs (known)
- [ ] **Unit dropdown not scaling macros correctly** — changing unit in meal template items does not proportionally rescale macros. The serving number updates but macro values stay stale. Needs proper base-macro tracking per item row. (Added 2026-07)
- [ ] **Meal dataset missing** — the Meals filter in template search returns empty; no whole-dish entries are seeded yet. Needs a real nutritional dataset for meals. (Added 2026-07)

## Language Support
- [ ] **Turkish UI translation** — add i18n support so all labels, buttons, toasts, and placeholders can be shown in Turkish. Suggested approach: a `static/js/i18n.js` module with `tr` and `en` dictionaries, a language toggle in Settings, and `data-i18n="key"` attributes on all translatable HTML elements.
- [ ] **Turkish meal dataset** — curate or source a dataset of common Turkish dishes (mercimek çorbası, manti, iskender, döner, karnıyarık, börek, menemen, pilav, köfte, dolma…) with accurate per-100g macros. Consider OpenFoodFacts Turkey data or USDA SR Legacy as a base.
- [ ] **Country-specific meal datasets** — extend the meal seeding infrastructure to support per-country datasets (e.g. Italian, Turkish, Mexican) selectable in Settings.

## Dataset & Food Library

> **Top recommendation:** Use a two-layer strategy: (1) Bundle a small curated CSV (<2 MB) of the 3,000-5,000 most common foods sourced from USDA public-domain data directly in the repository under data/foods.csv — this gives zero-setup, offline, instant lookup for the majority of tracking needs. (2) Integrate the OpenFoodFacts API as a live fallback for foods not found in the local dataset — no API key needed, just a User-Agent header, with 3M+ product coverage. For recipe data specifically, add optional Hugging Face Datasets Hub queries against `datahiveai/recipes-with-nutrition` (no auth, REST API) for users who want recipe import. This combination covers 95%+ of use cases with zero user-facing setup, no account required, and no bundled secrets.

- [ ] **Data layer: bundle seed foods CSV** — Download USDA FoodData Central Foundation Foods dataset (public domain, fdc.nal.usda.gov/download-datasets), filter to top ~3,000-5,000 common foods, export as `data/foods.csv` (~1-2 MB). Fields: food_name, calories_kcal, protein_g, fat_g, carbs_g, fiber_g, sugar_g, sodium_mg per 100 g serving.
- [ ] **Data layer: OpenFoodFacts API fallback** — Implement `search_openfoodfacts(query: str)` using `GET https://search.openfoodfacts.org/search?q={query}&json=true` with `User-Agent: NutritionTracker/1.0 (contact@example.com)` header. Map response `nutriments` fields to internal NutritionInfo model. Use as fallback when food not found in bundled CSV.
- [ ] **Data layer: HuggingFace recipe lookup (optional)** — Implement recipe search against `datahiveai/recipes-with-nutrition` via `GET https://datasets-server.huggingface.co/search?dataset=datahiveai/recipes-with-nutrition&config=default&split=train&query={name}`. No auth needed. Note CC BY-NC 4.0 license — ensure app's license is compatible.
- [ ] **USDA FoodData Central API (optional/advanced)** — Document in README that users can optionally supply a free USDA API key (api.data.gov/signup) as `USDA_API_KEY` env var to enable higher-quality USDA lookups via `https://api.nal.usda.gov/fdc/v1/foods/search`. Implement as an opt-in provider, not required for basic use.
- [ ] **Data update script** — Add `scripts/update_foods_csv.py` to periodically regenerate `data/foods.csv` from the latest USDA public download, so the bundled data can be refreshed with a single command before cutting a new release.
- [ ] Integrate OpenFoodFacts API for real-time food search (no auth, free, 3M+ products)
- [ ] Integrate USDA FoodData Central API for authoritative ingredient data
- [ ] Explore Hugging Face Datasets Hub for hosting cleaned meal CSVs

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
