"""
Kaggle meal dataset seeder.

Downloads two Kaggle datasets and imports them as food_type='meal' entries
into the SavedFood table.

Requirements:
  pip install kagglehub[pandas-datasets] pandas

Kaggle API key:
  1. Go to https://www.kaggle.com/settings -> API -> Create New Token
  2. Save the downloaded kaggle.json to:
       Windows: C:\Users\<you>\.kaggle\kaggle.json
       macOS/Linux: ~/.kaggle/kaggle.json
  3. Or set env vars: KAGGLE_USERNAME and KAGGLE_KEY

Usage (from project root, with venv active):
  python seed_data/seed_meals_kaggle.py

Run once — already-imported meals are skipped on re-run.
"""

import sys
import os

# Allow running from project root or seed_data/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import kagglehub
    from kagglehub import KaggleDatasetAdapter
    import pandas as pd
except ImportError:
    print("ERROR: Required packages missing.")
    print("Run:  pip install kagglehub[pandas-datasets] pandas")
    sys.exit(1)

from app import create_app
from models import db
from models.saved_food import SavedFood


# ---------------------------------------------------------------------------
# Column mapping helpers
# ---------------------------------------------------------------------------

def _float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _str(val, default=''):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return str(val).strip()


def _calories(protein, fat, carbs, provided=None):
    if provided and provided > 0:
        return provided
    return round(protein * 4 + fat * 9 + carbs * 4, 1)


# ---------------------------------------------------------------------------
# Turkish Recipes dataset  (bit104/turkish-recipes-structured)
# ---------------------------------------------------------------------------
# TODO: After first run, inspect printed columns and adjust the mapping below.
# The dataset likely has recipe names and ingredients but may lack macro data.
# If macros are absent, entries will be seeded with 0s and you can fill them
# manually via My Foods -> Edit, or find a richer dataset.

TURKISH_COLUMN_MAP = {
    # Adjust these keys to match actual column names printed on first run
    'name':     ['name', 'recipe_name', 'title', 'yemek_adi', 'tarif_adi'],
    'category': ['category', 'kategori', 'type', 'cuisine'],
    'protein':  ['protein', 'protein_g', 'protein(g)'],
    'fat':      ['fat', 'fat_g', 'fat(g)', 'yag'],
    'carbs':    ['carbs', 'carbohydrates', 'carbs_g', 'karbonhidrat'],
    'calories': ['calories', 'kcal', 'energy', 'calorie'],
    'serving':  ['serving_size', 'serving', 'portion'],
}


def _find_col(df, candidates):
    cols_lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in cols_lower:
            return cols_lower[c.lower()]
    return None


def import_turkish_recipes(app):
    print("\n--- Turkish Recipes (bit104/turkish-recipes-structured) ---")
    try:
        df = kagglehub.load_dataset(
            KaggleDatasetAdapter.PANDAS,
            "bit104/turkish-recipes-structured",
            "",
        )
    except Exception as e:
        print(f"  Download failed: {e}")
        return 0

    print(f"  Columns: {list(df.columns)}")
    print(f"  Rows: {len(df)}")
    print(f"  Preview:\n{df.head(3).to_string()}\n")

    name_col     = _find_col(df, TURKISH_COLUMN_MAP['name'])
    category_col = _find_col(df, TURKISH_COLUMN_MAP['category'])
    protein_col  = _find_col(df, TURKISH_COLUMN_MAP['protein'])
    fat_col      = _find_col(df, TURKISH_COLUMN_MAP['fat'])
    carbs_col    = _find_col(df, TURKISH_COLUMN_MAP['carbs'])
    cal_col      = _find_col(df, TURKISH_COLUMN_MAP['calories'])
    serving_col  = _find_col(df, TURKISH_COLUMN_MAP['serving'])

    if not name_col:
        print("  ERROR: Could not find a name column. Check TURKISH_COLUMN_MAP.")
        return 0

    count = 0
    with app.app_context():
        for _, row in df.iterrows():
            name = _str(row.get(name_col))
            if not name:
                continue
            if SavedFood.query.filter_by(name=name, food_type='meal').first():
                continue  # skip duplicates

            protein  = _float(row.get(protein_col))  if protein_col  else 0.0
            fat      = _float(row.get(fat_col))       if fat_col      else 0.0
            carbs    = _float(row.get(carbs_col))     if carbs_col    else 0.0
            provided = _float(row.get(cal_col))       if cal_col      else 0.0
            calories = _calories(protein, fat, carbs, provided)
            category = _str(row.get(category_col), 'Turkish') if category_col else 'Turkish'
            serving  = _float(row.get(serving_col), 100.0)    if serving_col  else 100.0

            db.session.add(SavedFood(
                name=name,
                brand=None,
                category=category,
                protein=protein,
                fat=fat,
                carbs=carbs,
                calories=calories,
                serving_size=serving or 100.0,
                serving_unit='g',
                source='usda',
                food_type='meal',
                is_archived=False,
            ))
            count += 1

        db.session.commit()
    print(f"  Imported {count} Turkish recipes.")
    return count


# ---------------------------------------------------------------------------
# 3A2M Cooking Recipe dataset  (nazmussakibrupol/3a2m-cooking-recipe-dataset)
# ---------------------------------------------------------------------------

RECIPE_COLUMN_MAP = {
    'name':     ['name', 'recipe_name', 'title', 'recipe'],
    'category': ['category', 'cuisine', 'type', 'meal_type', 'course'],
    'protein':  ['protein', 'protein_g', 'protein(g)'],
    'fat':      ['fat', 'fat_g', 'fat(g)', 'total_fat'],
    'carbs':    ['carbs', 'carbohydrates', 'carbs_g', 'total_carbs'],
    'calories': ['calories', 'kcal', 'energy', 'calorie', 'total_calories'],
    'serving':  ['serving_size', 'serving', 'servings', 'portion'],
}


def import_3a2m_recipes(app):
    print("\n--- 3A2M Cooking Recipes (nazmussakibrupol/3a2m-cooking-recipe-dataset) ---")
    try:
        df = kagglehub.load_dataset(
            KaggleDatasetAdapter.PANDAS,
            "nazmussakibrupol/3a2m-cooking-recipe-dataset",
            "",
        )
    except Exception as e:
        print(f"  Download failed: {e}")
        return 0

    print(f"  Columns: {list(df.columns)}")
    print(f"  Rows: {len(df)}")
    print(f"  Preview:\n{df.head(3).to_string()}\n")

    name_col     = _find_col(df, RECIPE_COLUMN_MAP['name'])
    category_col = _find_col(df, RECIPE_COLUMN_MAP['category'])
    protein_col  = _find_col(df, RECIPE_COLUMN_MAP['protein'])
    fat_col      = _find_col(df, RECIPE_COLUMN_MAP['fat'])
    carbs_col    = _find_col(df, RECIPE_COLUMN_MAP['carbs'])
    cal_col      = _find_col(df, RECIPE_COLUMN_MAP['calories'])
    serving_col  = _find_col(df, RECIPE_COLUMN_MAP['serving'])

    if not name_col:
        print("  ERROR: Could not find a name column. Check RECIPE_COLUMN_MAP.")
        return 0

    count = 0
    with app.app_context():
        for _, row in df.iterrows():
            name = _str(row.get(name_col))
            if not name:
                continue
            if SavedFood.query.filter_by(name=name, food_type='meal').first():
                continue

            protein  = _float(row.get(protein_col))  if protein_col  else 0.0
            fat      = _float(row.get(fat_col))       if fat_col      else 0.0
            carbs    = _float(row.get(carbs_col))     if carbs_col    else 0.0
            provided = _float(row.get(cal_col))       if cal_col      else 0.0
            calories = _calories(protein, fat, carbs, provided)
            category = _str(row.get(category_col), 'Recipe') if category_col else 'Recipe'
            serving  = _float(row.get(serving_col), 100.0)   if serving_col  else 100.0

            db.session.add(SavedFood(
                name=name,
                brand=None,
                category=category,
                protein=protein,
                fat=fat,
                carbs=carbs,
                calories=calories,
                serving_size=serving or 100.0,
                serving_unit='g',
                source='usda',
                food_type='meal',
                is_archived=False,
            ))
            count += 1

        db.session.commit()
    print(f"  Imported {count} recipes.")
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        pass  # ensures DB is ready

    total = 0
    total += import_turkish_recipes(app)
    total += import_3a2m_recipes(app)
    print(f"\nDone. Total meals imported: {total}")
    print("They are now searchable in NutriTrack under the Meals filter.")
