import sys, csv, io
sys.stdout.reconfigure(encoding='utf-8')

CSV_PATH = r'C:\Users\z004mvzt\nutrition-tracker\seed_data\foods.csv'

# Re-read as raw to get 13-column rows before DictReader truncates
with open(CSV_PATH, encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    raw_header = next(reader)
    raw_rows = list(reader)

print("Header columns:", len(raw_header), raw_header)
# Check how many columns the shifted rows have
shifted_col_counts = set()
for r in raw_rows:
    try:
        float(r[4])  # protein column index
    except (ValueError, IndexError):
        shifted_col_counts.add(len(r))
print("Shifted row column counts:", shifted_col_counts)
# Show a full raw shifted row
for r in raw_rows:
    if len(r) > 12:
        print("Sample 13-col row:", r[:15])
        break