import sys, os
sys.path.insert(0, r'C:\Users\z004mvzt\nutrition-tracker')
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
from app import create_app
from models import db
from models.saved_food import SavedFood

CSV = r'C:\Users\z004mvzt\.cache\kagglehub\datasets\berkebykkpr\yemek-veri-tabani\versions\1\Yemek_Veri_Tabani.csv'
df = pd.read_csv(CSV, encoding='utf-8-sig')
df.columns = ['name_tr', 'portion_g', 'calories', 'fat', 'carbs', 'protein', 'sugar', 'fiber']

app = create_app()
with app.app_context():
    existing = {f.name.lower() for f in SavedFood.query.with_entities(SavedFood.name).all()}
    existing_tr = {(f.name_tr or '').lower() for f in SavedFood.query.with_entities(SavedFood.name_tr).all()}
    added = 0
    skipped = 0
    batch = []
    for _, row in df.iterrows():
        name_tr = str(row['name_tr']).strip()
        if not name_tr or name_tr == 'nan':
            skipped += 1
            continue
        if name_tr.lower() in existing or name_tr.lower() in existing_tr:
            skipped += 1
            continue
        existing.add(name_tr.lower())
        existing_tr.add(name_tr.lower())
        
        cal  = float(row['calories']) if str(row['calories']) not in ('nan', '-', '') else None
        fat  = float(row['fat'])      if str(row['fat'])      not in ('nan', '-', '') else 0.0
        carbs= float(row['carbs'])    if str(row['carbs'])    not in ('nan', '-', '') else 0.0
        prot = float(row['protein'])  if str(row['protein'])  not in ('nan', '-', '') else 0.0
        sugar= float(row['sugar'])    if str(row['sugar'])    not in ('nan', '-', '') else None
        fiber= float(row['fiber'])    if str(row['fiber'])    not in ('nan', '-', '') else None
        if cal is None:
            cal = prot * 4 + fat * 9 + carbs * 4
        
        batch.append(SavedFood(
            name=name_tr,
            name_tr=name_tr,
            protein=prot,
            fat=fat,
            carbs=carbs,
            calories=cal,
            sugar=sugar,
            fiber=fiber,
            default_serving=100.0,
            serving_unit='g',
            food_type='ingredient',
            source='tr',
            is_archived=False,
        ))
    db.session.add_all(batch)
    db.session.commit()
    added = len(batch)
    total_tr = SavedFood.query.filter_by(source='tr').count()
    print(f"Kaggle dataset: Added {added}, Skipped {skipped} (dups/blanks)")
    print(f"Total source=tr in DB: {total_tr}")
    print(f"Total foods in DB: {SavedFood.query.count()}")