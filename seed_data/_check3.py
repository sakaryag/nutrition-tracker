import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\Users\z004mvzt\nutrition-tracker')
from app import create_app
from models.saved_food import SavedFood

app = create_app()
with app.app_context():
    # Epicurious protein=0 — show sample
    ep = SavedFood.query.filter(
        SavedFood.source == 'epicurious',
        SavedFood.protein == 0.0
    ).limit(20).all()
    print(f"Epicurious protein=0 (sample of 20):")
    for f in ep:
        print(f"  {f.name[:60]} fat={f.fat} carbs={f.carbs} cal={f.calories}")
    
    print()
    # TR protein=0
    tr = SavedFood.query.filter(
        SavedFood.source == 'tr',
        SavedFood.protein == 0.0
    ).all()
    print(f"TR protein=0 ({len(tr)} total):")
    for f in tr:
        print(f"  {f.name[:60]} fat={f.fat} carbs={f.carbs} cal={f.calories}")