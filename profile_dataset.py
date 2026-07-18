import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load Kaggle credentials
load_dotenv(Path(r'C:\Users\z004mvzt\nutrition-tracker\.env'))
os.environ['KAGGLE_USERNAME'] = os.getenv('KAGGLE_USERNAME', '')
os.environ['KAGGLE_KEY'] = os.getenv('KAGGLE_KEY', '')

print(f"Kaggle username: {os.environ.get('KAGGLE_USERNAME', 'NOT SET')}", file=sys.stderr)

import kagglehub
import pandas as pd

# Download dataset
print("Downloading dataset...", file=sys.stderr)
path = kagglehub.dataset_download('himanshikushwaha/global-cuisine-meals-with-diet-labels')
print(f"Downloaded to: {path}", file=sys.stderr)

# List all files
all_files = list(Path(path).rglob('*'))
print(f"All files found:", file=sys.stderr)
for f in all_files:
    print(f"  {f}", file=sys.stderr)

# Collect CSV/JSON files
data_files = [f for f in all_files if f.suffix.lower() in ('.csv', '.json') and f.is_file()]

report = {
    "dataset": "global-cuisine",
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
best_file_info = None

for fpath in data_files:
    file_size = fpath.stat().st_size
    print(f"\nProcessing file: {fpath.name} ({file_size} bytes)", file=sys.stderr)

    try:
        if fpath.suffix.lower() == '.csv':
            df = pd.read_csv(fpath)
        else:
            df = pd.read_json(fpath)
    except Exception as e:
        print(f"  Error loading {fpath.name}: {e}", file=sys.stderr)
        continue

    total_rows = len(df)
    columns = list(df.columns)
    print(f"  Rows: {total_rows}, Columns: {columns}", file=sys.stderr)

    # Profile each column
    col_profiles = {}
    for col in columns:
        series = df[col]
        non_null = series.notna().sum()
        null_pct = round((1 - non_null / total_rows) * 100, 2) if total_rows > 0 else 0.0
        sample_vals = series.dropna().head(3).tolist()
        col_profiles[col] = {
            "dtype": str(series.dtype),
            "non_null_count": int(non_null),
            "null_percentage": f"{null_pct}%",
            "sample_values": [str(v) for v in sample_vals]
        }

    # Identify key columns
    def find_col(df, candidates):
        cols_lower = {c.lower(): c for c in df.columns}
        for cand in candidates:
            if cand.lower() in cols_lower:
                return cols_lower[cand.lower()]
        # partial match
        for cand in candidates:
            for col in df.columns:
                if cand.lower() in col.lower():
                    return col
        return None

    name_col = find_col(df, ['name', 'meal', 'title', 'food', 'item', 'dish'])
    cal_col = find_col(df, ['calories', 'calorie', 'kcal', 'energy'])
    prot_col = find_col(df, ['protein', 'proteins'])
    fat_col = find_col(df, ['fat', 'fats', 'total_fat'])
    carb_col = find_col(df, ['carbs', 'carbohydrates', 'carb', 'carbohydrate'])
    cat_col = find_col(df, ['category', 'diet', 'cuisine', 'type', 'label', 'diet_label', 'diet_type'])

    print(f"  name_col={name_col}, cal_col={cal_col}, prot_col={prot_col}, fat_col={fat_col}, carb_col={carb_col}, cat_col={cat_col}", file=sys.stderr)

    # Usability checks
    macro_cols = [c for c in [cal_col, prot_col, fat_col] if c is not None]
    if len(macro_cols) == 3:
        mask_macros = (
            df[cal_col].notna() & (pd.to_numeric(df[cal_col], errors='coerce') > 0) &
            df[prot_col].notna() & (pd.to_numeric(df[prot_col], errors='coerce') > 0) &
            df[fat_col].notna() & (pd.to_numeric(df[fat_col], errors='coerce') > 0)
        )
        rows_all_macros = int(mask_macros.sum())

        if name_col is not None:
            mask_name_macros = mask_macros & df[name_col].notna()
            rows_name_macros = int(mask_name_macros.sum())
        else:
            rows_name_macros = 0
    else:
        rows_all_macros = 0
        rows_name_macros = 0

    # Null rates for key cols
    null_rates = {}
    for label, col in [('calories', cal_col), ('protein', prot_col), ('fat', fat_col), ('carbs', carb_col), ('name', name_col)]:
        if col is not None:
            null_pct = round(df[col].isna().mean() * 100, 2)
            null_rates[label] = f"{null_pct}%"
        else:
            null_rates[label] = "column not found"

    # Sample names
    sample_names = []
    if name_col is not None:
        sample_names = df[name_col].dropna().head(3).tolist()
        sample_names = [str(s) for s in sample_names]

    file_info = {
        "filename": fpath.name,
        "size_bytes": file_size,
        "total_rows": total_rows,
        "columns_found": columns,
        "column_profiles": col_profiles,
        "identified_cols": {
            "name_col": name_col,
            "calories_col": cal_col,
            "protein_col": prot_col,
            "fat_col": fat_col,
            "carbs_col": carb_col,
            "category_col": cat_col,
        },
        "rows_all_macros_nonzero": rows_all_macros,
        "rows_name_and_macros": rows_name_macros,
        "null_rates": null_rates,
        "sample_names": sample_names
    }
    report["files"].append(file_info)

    # Score: prefer files with more usable rows
    score = rows_name_macros
    if score > best_score:
        best_score = score
        best_file_info = file_info

# Build summary report
if best_file_info:
    report["best_file"] = best_file_info["filename"]
    report["total_rows"] = best_file_info["total_rows"]
    report["usable_rows"] = best_file_info["rows_name_and_macros"]
    report["columns"] = best_file_info["identified_cols"]
    report["null_rates"] = best_file_info["null_rates"]
    report["sample_names"] = best_file_info["sample_names"]

    cols = best_file_info["identified_cols"]
    null_r = best_file_info["null_rates"]
    macro_ok = all(null_r.get(k, "100%") != "column not found" for k in ["calories", "protein", "fat"])
    verdict = (
        f"The dataset '{best_file_info['filename']}' contains {best_file_info['total_rows']} total rows. "
        f"Of these, {best_file_info['rows_all_macros_nonzero']} rows have all three macronutrients (calories, protein, fat) non-null and >0, "
        f"and {best_file_info['rows_name_and_macros']} rows additionally have a meal name. "
        f"Key nutritional columns {'were' if macro_ok else 'were NOT'} identified. "
        f"Null rates: calories={null_r.get('calories','?')}, protein={null_r.get('protein','?')}, "
        f"fat={null_r.get('fat','?')}, carbs={null_r.get('carbs','?')}. "
        f"This dataset {'appears highly usable' if best_file_info['rows_name_and_macros'] > 100 else 'may have limited usability'} "
        f"for a nutrition tracker application."
    )
    report["verdict"] = verdict

print("\n\n===JSON_REPORT_START===")
print(json.dumps(report, indent=2))
print("===JSON_REPORT_END===")
