#!/usr/bin/env python3
"""
apply_serving_fixes.py
Applies serving_fixes.json to foods.csv and also runs update_csv_from_json inline.
"""
import csv, json, os

CSV_PATH = r"C:\Users\z004mvzt\nutrition-tracker\seed_data\foods.csv"
JSON_PATH = r"C:\Users\z004mvzt\nutrition-tracker\seed_data\serving_fixes.json"

VALID_UNITS = {"g", "ml", "oz", "cup", "tbsp", "tsp", "glass", "piece", "slice", "serving"}
COUNT_UNITS = {"piece", "slice", "serving"}

def main():
    # Load the fixes
    with open(JSON_PATH, encoding='utf-8') as f:
        fixes = json.load(f)
    print(f"Loaded {len(fixes)} fixes from JSON")
    
    # Read current CSV
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    print(f"Read {len(rows)} rows from CSV")
    print(f"Columns: {fieldnames}")
    
    # Ensure g_per_unit column exists
    if 'g_per_unit' not in fieldnames:
        fieldnames = list(fieldnames) + ['g_per_unit']
    
    # Apply fixes
    updated = 0
    not_found = []
    
    for row in rows:
        name = row['name']
        if name in fixes:
            fix = fixes[name]
            unit = fix.get('serving_unit', row.get('serving_unit', 'g'))
            serving = fix.get('default_serving', row.get('default_serving', 100))
            g_per = fix.get('g_per_unit', None)
            
            # Validate unit
            if unit not in VALID_UNITS:
                print(f"WARNING: invalid unit '{unit}' for '{name}', keeping original")
                unit = row.get('serving_unit', 'g')
                g_per = None
            
            # g_per_unit only for count units
            if unit not in COUNT_UNITS:
                g_per = None
            
            row['serving_unit'] = unit
            row['default_serving'] = str(serving) if serving is not None else '100'
            row['g_per_unit'] = str(g_per) if g_per is not None else ''
            updated += 1
        else:
            not_found.append(name)
            if 'g_per_unit' not in row:
                row['g_per_unit'] = ''
    
    if not_found:
        print(f"\nNot found in fixes ({len(not_found)} items):")
        for n in not_found[:30]:
            print(f"  - {n}")
    
    # Write updated CSV
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\nUpdated {updated} rows in CSV")
    print("Done!")
    
    # Show sample results
    print("\nSample results:")
    sample_names = [
        'Egg, whole, raw', 'Bread, whole wheat', 'Milk, whole, 3.7% fat',
        'Chicken breast, boneless skinless, cooked', 'Olive oil, extra virgin',
        'Banana', 'Cookie, chocolate chip', 'Pizza, supreme'
    ]
    for row in rows:
        if row['name'] in sample_names:
            print(f"  {row['name']}: {row['default_serving']} {row['serving_unit']} (g_per_unit={row.get('g_per_unit', '')})")


if __name__ == '__main__':
    main()