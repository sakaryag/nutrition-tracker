import sys, csv, io
sys.stdout.reconfigure(encoding='utf-8')

CSV_PATH = r'C:\Users\z004mvzt\nutrition-tracker\seed_data\foods.csv'

def to_float(v):
    v = v.strip()
    if v == '': return ''
    try:
        return str(float(v))
    except ValueError:
        return ''

with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

fixed = 0
for r in rows:
    try:
        float(r['protein'])
    except ValueError:
        # shifted: protein col has category string
        # real values: fat=protein, carbs=fat, calories=carbs, fiber=calories
        # category is already in the 'protein' column but the real category is 'generic'
        real_protein = r['fat']
        real_fat     = r['carbs']
        real_carbs   = r['calories']
        real_calories= r['fiber']
        real_fiber   = r['sugar']
        real_sugar   = r['default_serving']
        # serving and unit get pushed off the end (lost) — use defaults
        r['category']        = r['protein']   # the category string that was misplaced
        r['protein']         = real_protein
        r['fat']             = real_fat
        r['carbs']           = real_carbs
        r['calories']        = real_calories
        r['fiber']           = real_fiber
        r['sugar']           = real_sugar if to_float(real_sugar) != '' else ''
        # default_serving and serving_unit are now missing; keep whatever came before
        # (they'll be defaults when re-seeded, but we're fixing DB directly)
        fixed += 1

print(f"Fixed {fixed} rows")

# Write corrected CSV
output = io.StringIO(newline='')
writer = csv.DictWriter(output, fieldnames=fieldnames)
writer.writeheader()
writer.writerows(rows)
csv_content = output.getvalue()

# Write with UTF-8 no-BOM
with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    f.write(csv_content)
print("CSV rewritten.")

# Verify bread
for r in rows:
    if 'bread' in r['name'].lower() or 'Bread' in r['name']:
        print(f"  {r['name']} ({r['category']}) P={r['protein']} F={r['fat']} C={r['carbs']} kcal={r['calories']}")
        break