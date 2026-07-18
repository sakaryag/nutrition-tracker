import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\Users\z004mvzt\nutrition-tracker')
from app import create_app
from models.saved_food import SavedFood

app = create_app()
with app.app_context():
    foods = SavedFood.query.filter(
        SavedFood.source == 'usda',
        SavedFood.protein == 0.0
    ).order_by(SavedFood.calories.desc()).all()
    print(f"Remaining USDA protein=0 ({len(foods)} total):")
    for f in foods:
        print(f"  [{f.usda_fdc_id}] {f.name} — fat={f.fat} carbs={f.carbs} cal={f.calories} cat={f.category}")