# NutriTrack — Dataset Sources

This document describes every dataset integrated into NutriTrack, how to re-import it, and any notes about data quality.

---

## 1. USDA FoodData Central (primary ingredient database)

| Property | Value |
|---|---|
| Source | U.S. Department of Agriculture — FoodData Central SR Legacy |
| Format | CSV (bundled in `seed_data/`) |
| Records | ~6,000 ingredients |
| Language | English (`name` column) |
| Per-100g | Yes |
| Macros | Protein, Fat, Carbs, Calories, Fiber, Sugar |
| Seeded by | `seed_data/seed.py` (`seed_db()` — runs automatically on first startup) |
| Source field | `'usda'` |
| Food type | `'ingredient'` |

Re-seed: `flask seed` or delete `nutritrack.db` and restart.

---

## 2. Epicurious Recipes (~5,000 meals)

| Property | Value |
|---|---|
| Kaggle slug | `hugodarwood/epicurious-recipes-with-rating-and-nutrition` |
| Records | 5,000 (top by calories completeness after filtering) |
| Language | English |
| Per-100g | No — values are per-recipe; imported as-is with `default_serving=100g` |
| Macros | Protein, Fat, Calories (Carbs **derived**: `(cal - prot*4 - fat*9)/4`) |
| Seeded by | `seed_data/clean_meals.py` → `seed_data/import_meals.py` |
| Source field | `'epicurious'` (via `cleaned_combined_meals.csv`) |
| Food type | `'meal'` |
| Notes | Rows with negative derived carbs dropped (inconsistent source data) |

Re-seed:
```powershell
# Download from Kaggle (requires .env with KAGGLE_USERNAME + KAGGLE_KEY)
python seed_data/clean_meals.py    # builds cleaned_combined_meals.csv
python seed_data/import_meals.py   # imports into DB
```

---

## 3. Global Cuisine Dataset (~194 international meals)

| Property | Value |
|---|---|
| Kaggle slug | `paultimothymooney/ethnic-and-regional-food-nutrition-dataset` |
| Records | 194 usable rows (merged with Epicurious; global-cuisine wins on name collision) |
| Language | English |
| Per-100g | Yes |
| Macros | Protein, Fat, Carbs, Calories |
| Seeded by | `seed_data/clean_meals.py` → `seed_data/import_meals.py` |
| Source field | `'global_cuisine'` (via `cleaned_combined_meals.csv`) |
| Food type | `'meal'` |

---

## 4. Adile Sultan Turkish Dishes (authentic Turkish meals)

| Property | Value |
|---|---|
| Source | https://adilesultanevyemekleri.com/besin-degerleri/ |
| Records | 136 dishes |
| Language | Turkish (`name` = `name_tr` — both columns have Turkish name) |
| Per-100g | Yes |
| Macros | Protein, Fat, Carbs, Calories |
| Seeded by | `seed_data/seed_tr.py` |
| Source field | `'tr'` |
| Food type | `'meal'` |
| Categories | Çorba, Etli Yemek, Tavuklu Yemek, Etli Sebzeli, Sebzeli Yemek, Makarna, Pilav, Pilav Üstü, Salata, Yan Ürün, Zeytinyağlı, Tatlı, Ek Lezzet |

Re-seed:
```powershell
python seed_data/seed_tr.py
```

Note: `name` and `name_tr` are identical (Turkish). English translations were not added because the foods are already in the `name_tr` column used when the UI is in Turkish mode.

---

## 5. Yemek Veri Tabani — Turkish Ingredient Database (Kaggle)

| Property | Value |
|---|---|
| Kaggle slug | `berkebykkpr/yemek-veri-tabani` |
| Kaggle API | `kagglehub.dataset_download('berkebykkpr/yemek-veri-tabani')` |
| Records | 467 total, 413 imported (54 skipped as duplicates) |
| Language | Turkish (`name` = `name_tr` — both columns have Turkish name) |
| Per-100g | Yes (all rows are per 100g) |
| Macros | Protein, Fat, Carbs, Calories, Sugar, Fiber |
| Seeded by | `seed_data/import_tr_kaggle.py` |
| Source field | `'tr'` |
| Food type | `'ingredient'` |
| CSV path | `~/.cache/kagglehub/datasets/berkebykkpr/yemek-veri-tabani/versions/1/Yemek_Veri_Tabani.csv` |

Re-seed (requires Kaggle credentials in `.env`):
```powershell
python seed_data/import_tr_kaggle.py
```

Sample entries: Acur, Ahududu, Alabalık, Antep Fıstığı, Avokado, Ayran, Beyaz Peynir...

---

## Summary

| # | Source | Records | Type | Language | Notes |
|---|---|---|---|---|---|
| 1 | USDA FoodData Central | ~6,000 | ingredient | EN | Primary seed, bundled |
| 2 | Epicurious (Kaggle) | 5,000 | meal | EN | Carbs derived |
| 3 | Global Cuisine (Kaggle) | 194 | meal | EN | Merged with Epicurious |
| 4 | Adile Sultan website | 136 | meal | TR | Authentic Turkish dishes |
| 5 | Yemek Veri Tabani (Kaggle) | 413 | ingredient | TR | Turkish ingredients |
| | **Total** | **~11,743** | | | |

---

## Adding More Datasets

To add a new dataset:

1. Write a script in `seed_data/` that reads the source and maps columns to:
   - `name` (English) — required
   - `name_tr` (Turkish) — optional but recommended
   - `protein`, `fat`, `carbs`, `calories` — per 100g or per serving
   - `default_serving`, `serving_unit` — portion reference
   - `food_type` — `'ingredient'` or `'meal'`
   - `source` — short slug identifying the dataset

2. Use the idempotent pattern: check `existing` names before inserting to avoid duplicates on re-run.

3. Add the dataset to this file.

---

## Kaggle Credentials

Required only for datasets 2, 3, and 5 (Kaggle downloads). Add to `.env`:

```
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_KEY=your_kaggle_api_key
```

Get your key at https://www.kaggle.com/settings (Account → API → Create New Token).