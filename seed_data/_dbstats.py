import sys; sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from app import create_app
from models.saved_food import SavedFood
from sqlalchemy import func
app = create_app()
with app.app_context():
    rows = (SavedFood.query
        .with_entities(SavedFood.source, SavedFood.food_type, func.count())
        .group_by(SavedFood.source, SavedFood.food_type)
        .all())
    print('Source           | Type       | Count')
    print('-'*45)
    for src, ft, cnt in rows:
        src_s = src if src else 'none'
        print(f'{src_s:<16} | {ft:<10} | {cnt}')
    print('-'*45)
    total = SavedFood.query.count()
    print(f'Total: {total}')