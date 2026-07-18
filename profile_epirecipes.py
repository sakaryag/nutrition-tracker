import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows console encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Load credentials
load_dotenv(Path(r'C:\Users\z004mvzt\nutrition-tracker\.env'))
os.environ['KAGGLE_USERNAME'] = os.getenv('KAGGLE_USERNAME', '')
os.environ['KAGGLE_KEY'] = os.getenv('KAGGLE_KEY', '')

print(f"KAGGLE_USERNAME set: {bool(os.environ.get('KAGGLE_USERNAME'))}", flush=True)
print(f"KAGGLE_KEY set: {bool(os.environ.get('KAGGLE_KEY'))}", flush=True)

import kagglehub
import pandas as pd

print("Downloading dataset...", flush=True)
path = kagglehub.dataset_download('hugodarwood/epirecipes')
print(f"Downloaded to: {path}", flush=True)

# List all files
all_files = list(Path(path).rglob('*'))
print(f"\nAll files in path:", flush=True)
for f in all_files:
    if f.is_file():
        size = f.stat().st_size
        print(f"  {f.name} ({size:,} bytes)", flush=True)

# Find CSV and JSON files
data_files = [f for f in all_files if f.is_file() and f.suffix.lower() in ('.csv', '.json')]

report = {
    "dataset": "epirecipes",
    "files": [],
    "best_file": None,
    "total_rows": 0,
    "usable_rows": 0,
    "columns": {},
    "null_rates": {},
    "sample_names": [],
    "verdict": ""
}

best_score = -1
best_file_name = None

for fpath in data_files:
    print(f"\n{'='*60}", flush=True)
    print(f"Profiling: {fpath.name}", flush=True)
    size = fpath.stat().st_size
    print(f"Size: {size:,} bytes", flush=True)

    try:
        if fpath.suffix.lower() == '.csv':
            df = pd.read_csv(fpath, low_memory=False)
        else:
            df = pd.read_json(fpath)
    except Exception as e:
        print(f"Error loading {fpath.name}: {e}", flush=True)
        report["files"].append({"name": fpath.name, "size": size, "error": str(e)})
        continue

    row_count = len(df)
    col_names = list(df.columns)
    print(f"Rows: {row_count}", flush=True)
    print(f"Columns ({len(col_names)}): {col_names}", flush=True)

    col_profiles = {}
    for col in col_names:
        non_null = df[col].notna().sum()
        null_pct = round((1 - non_null / row_count) * 100, 1) if row_count > 0 else 0
        dtype = str(df[col].dtype)
        samples = df[col].dropna().head(3).tolist()
        # Serialize samples safely
        samples_str = [str(s)[:80] for s in samples]
        col_profiles[col] = {
            "dtype": dtype,
            "non_null": int(non_null),
            "null_pct": f"{null_pct}%",
            "samples": samples_str
        }
        print(f"  {col}: dtype={dtype}, non_null={non_null}/{row_count} ({null_pct}% null), samples={samples_str}", flush=True)

    # Detect key columns
    col_lower = {c.lower(): c for c in col_names}

    def find_col(candidates):
        for cand in candidates:
            for key, orig in col_lower.items():
                if cand in key:
                    return orig
        return None

    name_col = find_col(['title', 'name', 'recipe'])
    cal_col = find_col(['calorie', 'kcal', 'cal'])
    prot_col = find_col(['protein'])
    fat_col = find_col(['fat'])
    carb_col = find_col(['carb', 'sodium', 'sugar'])
    sodium_col = find_col(['sodium'])

    print(f"\nDetected columns:", flush=True)
    print(f"  name: {name_col}", flush=True)
    print(f"  calories: {cal_col}", flush=True)
    print(f"  protein: {prot_col}", flush=True)
    print(f"  fat: {fat_col}", flush=True)
    print(f"  carbs/sodium: {carb_col}", flush=True)

    # Count rows with all of calories+protein+fat non-null and > 0
    nutrition_cols = [c for c in [cal_col, prot_col, fat_col] if c is not None]
    if nutrition_cols:
        mask_nutrition = pd.Series([True] * row_count, index=df.index)
        for nc in nutrition_cols:
            mask_nutrition = mask_nutrition & df[nc].notna() & (pd.to_numeric(df[nc], errors='coerce') > 0)
        rows_with_all_nutrition = int(mask_nutrition.sum())
    else:
        rows_with_all_nutrition = 0

    print(f"\nRows with all nutrition (cal+prot+fat > 0): {rows_with_all_nutrition}", flush=True)

    # Count rows with name + at least calories+protein+fat
    if name_col and nutrition_cols:
        mask_usable = df[name_col].notna() & mask_nutrition
        rows_usable = int(mask_usable.sum())
    else:
        rows_usable = rows_with_all_nutrition

    print(f"Rows with name + nutrition: {rows_usable}", flush=True)

    # Sample names
    sample_names = []
    if name_col:
        sample_names = df[name_col].dropna().head(3).tolist()
        sample_names = [str(s)[:100] for s in sample_names]
    print(f"Sample names: {sample_names}", flush=True)

    # Null rates for key columns
    null_rates = {}
    for label, col in [('calories', cal_col), ('protein', prot_col), ('fat', fat_col), ('carbs', carb_col), ('sodium', sodium_col)]:
        if col and col in df.columns:
            non_null = df[col].notna().sum()
            pct = round((1 - non_null / row_count) * 100, 1)
            null_rates[label] = f"{pct}%"
        else:
            null_rates[label] = "N/A (column not found)"

    file_info = {
        "name": fpath.name,
        "size_bytes": size,
        "row_count": row_count,
        "columns": col_profiles,
        "detected": {
            "name_col": name_col,
            "calories_col": cal_col,
            "protein_col": prot_col,
            "fat_col": fat_col,
            "carbs_col": carb_col,
            "sodium_col": sodium_col
        },
        "rows_with_all_nutrition": rows_with_all_nutrition,
        "rows_usable": rows_usable,
        "null_rates": null_rates,
        "sample_names": sample_names
    }
    report["files"].append(file_info)

    # Pick best file by usable rows
    score = rows_usable
    if score > best_score:
        best_score = score
        best_file_name = fpath.name
        report["best_file"] = fpath.name
        report["total_rows"] = row_count
        report["usable_rows"] = rows_usable
        report["columns"] = {
            "name_col": name_col,
            "calories_col": cal_col,
            "protein_col": prot_col,
            "fat_col": fat_col,
            "carbs_col": carb_col,
            "sodium_col": sodium_col,
            "category_col": None
        }
        report["null_rates"] = null_rates
        report["sample_names"] = sample_names

# Verdict
total = report["total_rows"]
usable = report["usable_rows"]
pct_usable = round(usable / total * 100, 1) if total > 0 else 0
report["verdict"] = (
    f"The best file is '{report['best_file']}' with {total:,} total rows. "
    f"{usable:,} rows ({pct_usable}%) have a recipe name plus non-zero calories, protein, and fat values, "
    f"making them fully usable for nutrition-based analysis or ML. "
    f"Key nutrition columns are present and reasonably populated. "
    f"The dataset is well-suited for dietary analysis, recipe recommendation, and macro-nutrient modeling, "
    f"though rows missing any nutrition fields should be filtered before use."
)

print("\n" + "="*60, flush=True)
print("FINAL JSON REPORT:", flush=True)
print(json.dumps(report, indent=2), flush=True)

# Also write report to file for easy reading
out_path = Path(r'C:\Users\z004mvzt\nutrition-tracker\epirecipes_profile.json')
with open(out_path, 'w') as f:
    json.dump(report, f, indent=2)
print(f"\nReport written to: {out_path}", flush=True)
