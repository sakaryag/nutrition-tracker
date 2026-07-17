import sys, os
sys.path.insert(0, r'C:\Users\z004mvzt\nutrition-tracker')
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(r'C:\Users\z004mvzt\nutrition-tracker\.env'))

import pandas as pd
from app import create_app
from models import db
from models.saved_food import SavedFood

app = create_app()

csv_file = Path(r'C:\Users\z004mvzt\nutrition-tracker\seed_data\cleaned_combined_meals.csv')
df = pd.read_csv(csv_file)
print(f"Rows to import: {len(df)}")

imported = 0
skipped = 0
batch = []

with app.app_context():
    existing_names = {r.name.lower() for r in SavedFood.query.filter_by(food_type='meal').all()}
    print(f"Existing meal records in DB: {len(existing_names)}")

    for i, row in df.iterrows():
        name = str(row['name']).strip()
        if name.lower() in existing_names:
            skipped += 1
            continue
        existing_names.add(name.lower())

        try:
            food = SavedFood(
                name=name,
                brand=None,
                category=str(row['category']) if pd.notna(row.get('category')) else None,
                protein=float(row['protein']),
                fat=float(row['fat']),
                carbs=float(row['carbs']),
                calories=float(row['calories']),
                fiber=None,
                sugar=None,
                default_serving=1.0,
                serving_unit='serving',
                food_type='meal',
                source=str(row['source']),
                is_archived=False,
            )
            batch.append(food)
        except Exception as e:
            print(f"Skip row {i}: {e}")
            continue

        if len(batch) >= 500:
            db.session.add_all(batch)
            db.session.commit()
            imported += len(batch)
            print(f"  Committed {imported} so far...")
            batch = []

    if batch:
        db.session.add_all(batch)
        db.session.commit()
        imported += len(batch)

    total_meals = SavedFood.query.filter_by(food_type='meal').count()
    print(f"\nImport done. Imported: {imported}, Skipped (dups): {skipped}")
    print(f"Total meal-type foods in DB: {total_meals}")