import csv

CSV_PATH = r"C:\Users\z004mvzt\nutrition-tracker\seed_data\foods.csv"

with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Total rows: {len(rows)}")
print("Columns:", list(rows[0].keys()))
print()

samples = [
    "Egg, whole, raw", "Bread, whole wheat", "Milk, whole, 3.7% fat",
    "Banana", "Cookie, chocolate chip", "Pizza, supreme",
    "Olive oil, extra virgin", "Apple, Gala", "Butter, salted",
    "Brown sugar", "Coffee, brewed, black"
]
for row in rows:
    if row["name"] in samples:
        print(row["name"] + ": " + row["default_serving"] + " " + row["serving_unit"] + " g_per=" + row["g_per_unit"])

print()
unit_counts = {}
for row in rows:
    u = row["serving_unit"]
    unit_counts[u] = unit_counts.get(u, 0) + 1
print("Unit distribution:")
for u, c in sorted(unit_counts.items(), key=lambda x: -x[1]):
    print("  " + u + ": " + str(c))

count_with_g = sum(1 for row in rows if row["g_per_unit"])
print("Foods with g_per_unit set: " + str(count_with_g))