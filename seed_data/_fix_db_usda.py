import sys, csv
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\Users\z004mvzt\nutrition-tracker')
from app import create_app
from models import db
from models.saved_food import SavedFood

CSV_PATH = r'C:\Users\z004mvzt\nutrition-tracker\seed_data\foods.csv'

def to_float(v):
    try:
        return float(str(v).strip())
    except (ValueError, TypeError):
        return None

app = create_app()
with app.app_context():
    # Build FDC-id lookup from corrected CSV
    with open(CSV_PATH, encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        csv_rows = {int(r['usda_fdc_id']): r for r in reader if r['usda_fdc_id'].strip()}

    # Fix DB rows where protein=0 and source=usda
    foods = SavedFood.query.filter(
        SavedFood.source == 'usda',
        SavedFood.protein == 0.0
    ).all()
    
    fixed = 0
    skipped = 0
    for food in foods:
        if not food.usda_fdc_id or food.usda_fdc_id not in csv_rows:
            skipped += 1
            continue
        r = csv_rows[food.usda_fdc_id]
        p = to_float(r['protein'])
        f_ = to_float(r['fat'])
        c = to_float(r['carbs'])
        k = to_float(r['calories'])
        if p is None:
            skipped += 1
            continue
        food.protein  = p
        food.fat      = f_ if f_ is not None else food.fat
        food.carbs    = c if c is not None else food.carbs
        food.calories = k if k is not None else food.calories
        # also update category if CSV has it now
        cat = r.get('category', '').strip()
        if cat and cat != 'generic':
            food.category = cat
        fixed += 1
    
    db.session.commit()
    remaining = SavedFood.query.filter(SavedFood.source == 'usda', SavedFood.protein == 0.0).count()
    print(f"Fixed: {fixed}, Skipped (no FDC match): {skipped}")
    print(f"USDA protein=0 remaining: {remaining}")
    
    # Verify bread
    bread = SavedFood.query.filter(SavedFood.name.ilike('%bread%')).first()
    if bread:
        print(f"Sample - {bread.name}: P={bread.protein} F={bread.fat} C={bread.carbs} kcal={bread.calories}")