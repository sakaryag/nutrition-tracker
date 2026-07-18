import sys; sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from app import create_app
from models.saved_food import SavedFood
app = create_app()
with app.app_context():
    total = SavedFood.query.count()
    zero_prot = SavedFood.query.filter(SavedFood.protein == 0).count()
    print(f"Total: {total}, Protein=0: {zero_prot} ({100*zero_prot//total}%)")
    print()
    # By source
    from sqlalchemy import func
    rows = (SavedFood.query
        .with_entities(SavedFood.source, func.count())
        .filter(SavedFood.protein == 0)
        .group_by(SavedFood.source).all())
    for src, cnt in rows:
        print(f"  source={src}: {cnt} foods with protein=0")
    print()
    # Show some examples
    samples = SavedFood.query.filter(
        SavedFood.protein == 0,
        SavedFood.food_type == 'ingredient'
    ).limit(20).all()
    print("Sample ingredients with protein=0:")
    for f in samples:
        print(f"  [{f.source}] {f.name} — fat={f.fat} carbs={f.carbs} cal={f.calories}")
    print()
    # Bread search
    breads = SavedFood.query.filter(SavedFood.name.ilike('%bread%')).all()
    print("Bread results:")
    for f in breads[:10]:
        print(f"  [{f.source}] {f.name} — protein={f.protein} fat={f.fat} carbs={f.carbs} cal={f.calories}")
    # Turkish bread
    tr_breads = SavedFood.query.filter(
        (SavedFood.name.ilike('%ekmek%')) | (SavedFood.name_tr.ilike('%ekmek%'))
    ).all()
    print("Ekmek results:")
    for f in tr_breads[:10]:
        print(f"  [{f.source}] {f.name} — protein={f.protein} fat={f.fat} carbs={f.carbs} cal={f.calories}")