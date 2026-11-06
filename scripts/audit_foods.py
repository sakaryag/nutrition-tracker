"""
Food data audit script for NutriTrack.

Exports all foods from seed_data/foods.csv and optionally cross-references
each USDA food against the live USDA FoodData Central API to flag discrepancies.

Usage:
    python scripts/audit_foods.py                    # export only, no API calls
    python scripts/audit_foods.py --fetch            # fetch USDA data (DEMO_KEY, slow ~82 min)
    python scripts/audit_foods.py --fetch --key KEY  # fetch with real key (fast, ~2 min)
    python scripts/audit_foods.py --fetch --key KEY --threshold 5  # flag >5% diff

Output:
    food_audit.csv  (in project root)

Columns:
    usda_fdc_id, name, name_tr, brand, category, source,
    our_protein, our_fat, our_carbs, our_calories, our_fiber, our_sugar,
    default_serving, serving_unit, g_per_unit,
    usda_protein, usda_fat, usda_carbs, usda_calories, usda_fiber, usda_sugar,
    protein_diff_pct, fat_diff_pct, carbs_diff_pct, calories_diff_pct,
    needs_review, review_reason

USDA FDC Nutrient IDs used:
    1003 = Protein (g)
    1004 = Total lipid / Fat (g)
    1005 = Carbohydrate, by difference (g)
    1008 = Energy (kcal)
    1079 = Fiber, total dietary (g)
    2000 = Sugars, total (g)
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CSV_IN = ROOT / "seed_data" / "foods.csv"
CSV_OUT = ROOT / "food_audit.csv"

FDC_BASE = "https://api.nal.usda.gov/fdc/v1"
BATCH_SIZE = 20

NUTRIENT_IDS = {
    "protein": 1003,
    "fat": 1004,
    "carbs": 1005,
    "calories": 1008,
    "fiber": 1079,
    "sugar": 2000,
}

OUT_COLS = [
    "usda_fdc_id", "name", "name_tr", "brand", "category", "source",
    "our_protein", "our_fat", "our_carbs", "our_calories", "our_fiber", "our_sugar",
    "default_serving", "serving_unit", "g_per_unit",
    "usda_protein", "usda_fat", "usda_carbs", "usda_calories", "usda_fiber", "usda_sugar",
    "protein_diff_pct", "fat_diff_pct", "carbs_diff_pct", "calories_diff_pct",
    "needs_review", "review_reason",
]


def _fix_tr(s):
    """Fix double-encoded UTF-8 Turkish characters in name_tr column.

    The foods.csv Turkish names were written by reading UTF-8 bytes as cp1252
    then saving them as UTF-8 again. Round-tripping through cp1252 recovers
    the original Unicode characters.
    """
    if not s:
        return s
    try:
        return s.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s  # already correct or unrecoverable


def load_foods():
    """Load all rows from foods.csv, fixing double-encoded Turkish names."""
    rows = []
    with open(CSV_IN, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["name_tr"] = _fix_tr(row.get("name_tr", ""))
            rows.append(row)
    return rows


def _nutrient_value(food_data, nutrient_id):
    """Extract a nutrient amount (per 100g) from FDC food response."""
    for n in food_data.get("foodNutrients", []):
        nid = n.get("nutrient", {}).get("id") or n.get("nutrientId")
        if nid == nutrient_id:
            return n.get("amount") or n.get("value")
    return None


def fetch_usda_batch(fdc_ids, api_key):
    """
    Fetch up to BATCH_SIZE foods from FDC API.
    Returns dict: {fdc_id (int) -> {protein, fat, carbs, calories, fiber, sugar}}
    """
    url = f"{FDC_BASE}/foods"
    params = {"api_key": api_key}
    payload = {"fdcIds": fdc_ids}

    try:
        resp = requests.post(url, json=payload, params=params, timeout=30)
        if resp.status_code == 429:
            print("  [rate limited] sleeping 120s ...", flush=True)
            time.sleep(120)
            resp = requests.post(url, json=payload, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [WARN] FDC request failed: {e}", flush=True)
        return {}

    results = {}
    for food in resp.json():
        fid = food.get("fdcId")
        if fid is None:
            continue
        results[fid] = {
            k: _nutrient_value(food, nid)
            for k, nid in NUTRIENT_IDS.items()
        }
    return results


def pct_diff(our, usda):
    """Return signed % difference (our vs usda), or None if either is missing."""
    try:
        our_f = float(our)
        usda_f = float(usda)
    except (TypeError, ValueError):
        return None
    if usda_f == 0:
        return None if our_f == 0 else 100.0
    return round((our_f - usda_f) / usda_f * 100, 1)


def build_row(food, usda_vals, threshold):
    """Merge food CSV row with USDA fetched values into output dict."""
    row = {
        "usda_fdc_id": food.get("usda_fdc_id", ""),
        "name": food.get("name", ""),
        "name_tr": food.get("name_tr", ""),
        "brand": food.get("brand", ""),
        "category": food.get("category", ""),
        "source": "usda" if food.get("usda_fdc_id") else "custom",
        "our_protein": food.get("protein", ""),
        "our_fat": food.get("fat", ""),
        "our_carbs": food.get("carbs", ""),
        "our_calories": food.get("calories", ""),
        "our_fiber": food.get("fiber", ""),
        "our_sugar": food.get("sugar", ""),
        "default_serving": food.get("default_serving", ""),
        "serving_unit": food.get("serving_unit", ""),
        "g_per_unit": food.get("g_per_unit", ""),
    }

    if usda_vals:
        row["usda_protein"] = _fmt(usda_vals.get("protein"))
        row["usda_fat"] = _fmt(usda_vals.get("fat"))
        row["usda_carbs"] = _fmt(usda_vals.get("carbs"))
        row["usda_calories"] = _fmt(usda_vals.get("calories"))
        row["usda_fiber"] = _fmt(usda_vals.get("fiber"))
        row["usda_sugar"] = _fmt(usda_vals.get("sugar"))

        diffs = {
            "protein": pct_diff(row["our_protein"], row["usda_protein"]),
            "fat": pct_diff(row["our_fat"], row["usda_fat"]),
            "carbs": pct_diff(row["our_carbs"], row["usda_carbs"]),
            "calories": pct_diff(row["our_calories"], row["usda_calories"]),
        }

        row["protein_diff_pct"] = _fmt(diffs["protein"])
        row["fat_diff_pct"] = _fmt(diffs["fat"])
        row["carbs_diff_pct"] = _fmt(diffs["carbs"])
        row["calories_diff_pct"] = _fmt(diffs["calories"])

        flagged = [k for k, d in diffs.items() if d is not None and abs(d) > threshold]
        row["needs_review"] = "YES" if flagged else "no"
        row["review_reason"] = "; ".join(
            f"{k} {diffs[k]:+.1f}%" for k in flagged
        ) if flagged else ""
    else:
        for col in ["usda_protein", "usda_fat", "usda_carbs", "usda_calories",
                    "usda_fiber", "usda_sugar", "protein_diff_pct", "fat_diff_pct",
                    "carbs_diff_pct", "calories_diff_pct"]:
            row[col] = ""
        row["needs_review"] = "no_fdc_data"
        row["review_reason"] = ""

    return row


def _fmt(val):
    """Format numeric value for CSV (round floats to 2 dp)."""
    if val is None:
        return ""
    try:
        return f"{float(val):.2f}"
    except (TypeError, ValueError):
        return str(val)


def main():
    parser = argparse.ArgumentParser(description="Audit NutriTrack food data vs USDA FDC")
    parser.add_argument("--fetch", action="store_true",
                        help="Fetch real USDA values via FDC API (slow with DEMO_KEY)")
    parser.add_argument("--key", default=os.environ.get("USDA_API_KEY", "DEMO_KEY"),
                        metavar="API_KEY",
                        help="USDA FDC API key (default: DEMO_KEY or USDA_API_KEY env var)")
    parser.add_argument("--threshold", type=float, default=10.0,
                        help="Flag rows where any macro differs by more than this %% (default: 10)")
    parser.add_argument("--out", default=str(CSV_OUT),
                        help=f"Output CSV path (default: {CSV_OUT})")
    args = parser.parse_args()

    print(f"Loading foods from {CSV_IN} ...", flush=True)
    foods = load_foods()
    print(f"  {len(foods)} rows loaded", flush=True)

    usda_lookup = {}  # fdc_id (int) -> {protein, fat, ...}

    if args.fetch:
        usda_ids = []
        for f in foods:
            fid = f.get("usda_fdc_id", "").strip()
            if fid:
                usda_ids.append(int(fid))

        print(f"\nFetching USDA data for {len(usda_ids)} foods in batches of {BATCH_SIZE}...", flush=True)
        is_demo = args.key == "DEMO_KEY"
        if is_demo:
            estimated_min = (len(usda_ids) // BATCH_SIZE + 1) * 2
            print(f"  Using DEMO_KEY (30 req/hour). Estimated time: ~{estimated_min} minutes.", flush=True)
            print("  Tip: set USDA_API_KEY env var or pass --key for a free real key → ~2 min instead.", flush=True)
            print("  Sign up free: https://api.data.gov/signup/", flush=True)
            print("  Press Ctrl+C to cancel and export current data only.\n", flush=True)

        batches = [usda_ids[i:i + BATCH_SIZE] for i in range(0, len(usda_ids), BATCH_SIZE)]
        for i, batch in enumerate(batches, 1):
            print(f"  Batch {i}/{len(batches)} ({len(batch)} foods) ...", flush=True)
            result = fetch_usda_batch(batch, args.key)
            usda_lookup.update(result)

            if i < len(batches):
                # DEMO_KEY: 30/hour → 1 per 122s to be safe
                # Real key: 1000/hour → no meaningful sleep needed
                sleep_sec = 122 if is_demo else 0.5
                time.sleep(sleep_sec)

        print(f"  Fetched data for {len(usda_lookup)} foods from USDA FDC\n", flush=True)
    else:
        print("  (Skipping USDA API fetch — run with --fetch to compare against real values)\n", flush=True)

    print(f"Building audit rows ...", flush=True)
    out_rows = []
    needs_review_count = 0

    for food in foods:
        fid_str = food.get("usda_fdc_id", "").strip()
        usda_vals = usda_lookup.get(int(fid_str)) if fid_str else None
        row = build_row(food, usda_vals, args.threshold)
        out_rows.append(row)
        if row["needs_review"] == "YES":
            needs_review_count += 1

    out_path = Path(args.out)
    # If the target is locked (e.g. open in Excel), try an incremented name.
    for attempt in range(10):
        candidate = out_path if attempt == 0 else out_path.with_stem(out_path.stem + f"_{attempt}")
        try:
            with open(candidate, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=OUT_COLS)
                writer.writeheader()
                writer.writerows(out_rows)
            out_path = candidate
            break
        except PermissionError:
            if attempt == 0:
                print(f"  [WARN] {candidate} is locked (open in Excel?). Trying alternate name...", flush=True)
    else:
        print("ERROR: Could not write output — close the file in Excel and retry.", flush=True)
        sys.exit(1)

    print(f"Written: {out_path}", flush=True)
    print(f"  Total rows:      {len(out_rows)}", flush=True)
    if args.fetch:
        print(f"  Needs review:    {needs_review_count} (>{args.threshold:.0f}% diff on any macro)", flush=True)
        flagged = [r for r in out_rows if r["needs_review"] == "YES"]
        if flagged:
            print(f"\nFlagged foods:", flush=True)
            for r in flagged:
                print(f"  [{r['usda_fdc_id']:>7}] {r['name'][:40]:<40}  {r['review_reason']}", flush=True)
    print("\nDone. Open food_audit.csv in Excel / Google Sheets to review.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Partial results (if any) not saved.", flush=True)
        sys.exit(1)
