#!/usr/bin/env python3
"""
fix_serving_data.py
Calls Claude Haiku to get correct serving info for all 751 foods in foods.csv.
Then rewrites the CSV with corrected default_serving, serving_unit, and adds g_per_unit.
Also saves seed_data/serving_fixes.json as backup.
"""
import csv, json, os, sys
import urllib.request
import time

CSV_PATH = r"C:\Users\z004mvzt\nutrition-tracker\seed_data\foods.csv"
JSON_OUT = r"C:\Users\z004mvzt\nutrition-tracker\seed_data\serving_fixes.json"
BATCH_SIZE = 150
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

VALID_UNITS = {"g", "ml", "oz", "cup", "tbsp", "tsp", "glass", "piece", "slice", "serving"}
COUNT_UNITS = {"piece", "slice", "serving"}

def claude_batch(foods_list):
    """foods_list: list of (name, current_unit, current_serving) tuples"""
    lines = "\n".join(f"{name} | {unit} | {serving}" for name, unit, serving in foods_list)
    
    prompt = f"""For each food below, provide the correct serving information.

Rules:
- serving_unit must be one of: g, ml, cup, tbsp, tsp, glass, piece, slice, serving
- default_serving is the typical single serving amount in that unit
- g_per_unit is grams per 1 piece/slice/serving (only for piece/slice/serving units, else null)

Examples:
- "Bread, white" -> serving_unit: slice, default_serving: 1, g_per_unit: 30
- "Egg, whole" -> serving_unit: piece, default_serving: 1, g_per_unit: 50
- "Milk, whole" -> serving_unit: ml, default_serving: 200, g_per_unit: null
- "Olive oil" -> serving_unit: tbsp, default_serving: 1, g_per_unit: null
- "Chicken breast" -> serving_unit: g, default_serving: 150, g_per_unit: null
- "Cookie" -> serving_unit: piece, default_serving: 1, g_per_unit: 15
- "Oats" -> serving_unit: g, default_serving: 80, g_per_unit: null
- "Rice, cooked" -> serving_unit: g, default_serving: 150, g_per_unit: null
- "Apple" -> serving_unit: piece, default_serving: 1, g_per_unit: 180
- "Banana" -> serving_unit: piece, default_serving: 1, g_per_unit: 120
- "Orange" -> serving_unit: piece, default_serving: 1, g_per_unit: 180
- "Potato" -> serving_unit: g, default_serving: 150, g_per_unit: null
- "Yogurt" -> serving_unit: g, default_serving: 150, g_per_unit: null
- "Butter" -> serving_unit: tbsp, default_serving: 1, g_per_unit: null
- "Sugar" -> serving_unit: tsp, default_serving: 1, g_per_unit: null
- "Coffee, brewed" -> serving_unit: ml, default_serving: 240, g_per_unit: null
- "Pizza" -> serving_unit: slice, default_serving: 1, g_per_unit: 100
- "Pancake" -> serving_unit: piece, default_serving: 1, g_per_unit: 70

Foods (name | current_unit | current_serving):
{lines}

Respond ONLY with JSON:
{{"food_name": {{"serving_unit": "x", "default_serving": N, "g_per_unit": N_or_null}}, ...}}
"""
    
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 8192,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers=headers)
    resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
    text = resp["content"][0]["text"]
    start = text.find('{')
    end = text.rfind('}') + 1
    return json.loads(text[start:end])


def main():
    # Read CSV
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Read {len(rows)} foods from CSV")
    
    # Build batches
    foods_info = [(row['name'], row['serving_unit'], row['default_serving']) for row in rows]
    
    all_results = {}
    
    # Load existing results if available (resume support)
    if os.path.exists(JSON_OUT):
        with open(JSON_OUT, encoding='utf-8') as f:
            all_results = json.load(f)
        print(f"Loaded {len(all_results)} existing results from {JSON_OUT}")
    
    # Process in batches
    for i in range(0, len(foods_info), BATCH_SIZE):
        batch = foods_info[i:i+BATCH_SIZE]
        
        # Check which ones we still need
        needed = [(name, unit, serving) for name, unit, serving in batch if name not in all_results]
        
        if not needed:
            print(f"Batch {i//BATCH_SIZE + 1}: all {len(batch)} already done, skipping")
            continue
        
        print(f"Batch {i//BATCH_SIZE + 1}: processing {len(needed)} foods (of {len(batch)} in batch)...")
        
        try:
            results = claude_batch(needed)
            all_results.update(results)
            
            # Save after each batch
            with open(JSON_OUT, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            
            print(f"  -> Got {len(results)} results. Total: {len(all_results)}")
        except Exception as e:
            print(f"  ERROR in batch: {e}")
            # Save what we have and continue
            with open(JSON_OUT, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        # Small delay between batches
        if i + BATCH_SIZE < len(foods_info):
            time.sleep(1)
    
    print(f"\nGot serving data for {len(all_results)} foods total")
    
    # Rewrite CSV with corrected data
    # Build new rows
    new_rows = []
    not_found = []
    
    for row in rows:
        name = row['name']
        if name in all_results:
            fix = all_results[name]
            unit = fix.get('serving_unit', row['serving_unit'])
            serving = fix.get('default_serving', row['default_serving'])
            g_per = fix.get('g_per_unit', None)
            
            # Validate unit
            if unit not in VALID_UNITS:
                print(f"WARNING: invalid unit '{unit}' for '{name}', keeping original")
                unit = row['serving_unit']
                serving = row['default_serving']
                g_per = None
            
            # g_per_unit only makes sense for count units
            if unit not in COUNT_UNITS:
                g_per = None
            
            row['serving_unit'] = unit
            row['default_serving'] = str(serving)
            row['g_per_unit'] = str(g_per) if g_per is not None else ''
        else:
            not_found.append(name)
            row['g_per_unit'] = ''
        
        new_rows.append(row)
    
    if not_found:
        print(f"\nWARNING: {len(not_found)} foods not found in API results:")
        for n in not_found[:20]:
            print(f"  - {n}")
    
    # Write updated CSV
    fieldnames = list(rows[0].keys())
    if 'g_per_unit' not in fieldnames:
        fieldnames.append('g_per_unit')
    
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_rows)
    
    print(f"\nCSV rewritten with {len(new_rows)} rows")
    print(f"JSON backup saved to {JSON_OUT}")


if __name__ == '__main__':
    main()