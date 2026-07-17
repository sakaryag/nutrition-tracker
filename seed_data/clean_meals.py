import os, sys, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(r'C:\Users\z004mvzt\nutrition-tracker\.env'))
os.environ['KAGGLE_USERNAME'] = os.getenv('KAGGLE_USERNAME', '')
os.environ['KAGGLE_KEY'] = os.getenv('KAGGLE_KEY', '')

import kagglehub
import pandas as pd

# ── 1. Load & clean Global Cuisine (has real carbs — higher quality) ──────
print("Downloading global-cuisine...")
gc_path = kagglehub.dataset_download('himanshikushwaha/global-cuisine-meals-with-diet-labels')
gc_file = Path(gc_path) / 'nutrition.csv'
gc = pd.read_csv(gc_file)
print(f"Global Cuisine raw rows: {len(gc)}")

gc = gc.rename(columns={
    'Dish Name':         'name',
    'Protein (g)':      'protein',
    'Fat (g)':          'fat',
    'Carbohydrates (g)':'carbs',
    'Calories (kcal)':  'calories',
    'Diet':             'category',
})

# Drop nulls on required cols
gc = gc.dropna(subset=['name','protein','fat','carbs'])
# Calculate calories from macros when null/zero
gc['calories'] = gc.apply(
    lambda r: r['protein']*4 + r['fat']*9 + r['carbs']*4
    if (pd.isna(r['calories']) or r['calories'] <= 0) else r['calories'],
    axis=1
)
# Filters
gc = gc[(gc['calories'] > 0) & (gc['calories'] < 5000)]
gc = gc[(gc['protein'] >= 0) & (gc['fat'] >= 0) & (gc['carbs'] >= 0)]
gc['name'] = gc['name'].astype(str).str.strip()
gc = gc[(gc['name'].str.len() >= 3) & (gc['name'].str.len() <= 150)]
# Dedup
gc['_key'] = gc['name'].str.lower()
gc = gc.drop_duplicates(subset=['_key'])
gc['source'] = 'global-cuisine'
print(f"Global Cuisine after cleaning: {len(gc)} rows")

# ── 2. Load & clean Epicurious ────────────────────────────────────────────
print("Downloading epirecipes...")
epi_path = kagglehub.dataset_download('hugodarwood/epirecipes')
epi_file = Path(epi_path) / 'full_format_recipes.json'
with open(epi_file, 'r', encoding='utf-8') as f:
    epi_raw = json.load(f)

epi = pd.DataFrame(epi_raw)
print(f"Epirecipes raw rows: {len(epi)}")

# Rename
epi = epi.rename(columns={'title':'name','categories':'category'})
# Drop nulls on required cols
epi = epi.dropna(subset=['name','calories','protein','fat'])
# Filters
epi = epi[(epi['calories'] > 0) & (epi['calories'] < 5000)]
epi = epi[(epi['protein'] >= 0) & (epi['fat'] >= 0)]
# Derive carbs
epi['carbs'] = (epi['calories'] - epi['protein']*4 - epi['fat']*9) / 4
epi = epi[epi['carbs'] >= 0]  # drop negative carbs (inconsistent data)
# Category: flatten list to first element
def flatten_cat(c):
    if isinstance(c, list):
        return c[0] if c else None
    return str(c) if pd.notna(c) else None
epi['category'] = epi['category'].apply(flatten_cat)
# Name cleanup
epi['name'] = epi['name'].astype(str).str.strip()
epi = epi[(epi['name'].str.len() >= 3) & (epi['name'].str.len() <= 150)]
# Dedup
epi['_key'] = epi['name'].str.lower()
epi = epi.drop_duplicates(subset=['_key'])
# Cap at 5000
epi = epi.sample(n=min(5000, len(epi)), random_state=42)
epi['source'] = 'epicurious'
print(f"Epirecipes after cleaning: {len(epi)} rows")

# ── 3. Merge & global dedup (global-cuisine wins on collision) ────────────
keep_cols = ['name','category','protein','fat','carbs','calories','_key','source']
gc_slim  = gc[keep_cols].copy()
epi_slim = epi[keep_cols].copy()

# Stack: global-cuisine first so it wins dedup
combined = pd.concat([gc_slim, epi_slim], ignore_index=True)
combined = combined.drop_duplicates(subset=['_key'], keep='first')
combined = combined.drop(columns=['_key'])
print(f"Combined after global dedup: {len(combined)} rows")
print(combined[['name','protein','fat','carbs','calories','source']].head(3).to_string())

# Save cleaned CSVs
out_dir = Path(r'C:\Users\z004mvzt\nutrition-tracker\seed_data')
combined.to_csv(out_dir / 'cleaned_combined_meals.csv', index=False, encoding='utf-8')
print("Saved cleaned_combined_meals.csv")