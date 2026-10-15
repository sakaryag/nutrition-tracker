"""
apply_foods_csv.py — import foods_strict_full_pass.csv into the live DB.

Usage:
    python scripts/apply_foods_csv.py [--csv PATH] [--dry-run]

Behaviour:
  - Reads the CSV (skips # comment lines at the top).
  - For each row whose usda_fdc_id already exists in saved_food:
      Updates protein, fat, carbs, calories, fiber, sugar,
      default_serving, serving_unit, g_per_unit, name, name_tr.
  - For rows whose usda_fdc_id does NOT exist: inserts a new USDA row.
  - --dry-run prints what would change without touching the DB.

Nutrition values are stored per 100 g / 100 ml as per the data model spec.
"""

import sys, os, csv, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from models import db
from models.saved_food import SavedFood

CSV_DEFAULT = os.path.join(os.path.dirname(__file__), '..', 'foods_strict_full_pass.csv')

FLOAT_COLS = ['protein', 'fat', 'carbs', 'calories', 'fiber', 'sugar',
              'default_serving', 'g_per_unit']


def parse_csv(path):
    with open(path, encoding='utf-8') as f:
        lines = [l for l in f if not l.startswith('#')]
    reader = csv.DictReader(lines)
    rows = []
    for r in reader:
        for col in FLOAT_COLS:
            try:
                r[col] = float(r[col]) if r[col] else 0.0
            except (ValueError, TypeError):
                r[col] = 0.0
        r['usda_fdc_id'] = int(r['usda_fdc_id']) if r.get('usda_fdc_id') else None
        rows.append(r)
    return rows


def run(csv_path, dry_run=False):
    app = create_app()
    with app.app_context():
        rows = parse_csv(csv_path)
        print(f'CSV rows: {len(rows)}')

        # Build lookup by usda_fdc_id — always query fresh to avoid stale cache
        def _get_food(fdc_id):
            return SavedFood.query.filter_by(usda_fdc_id=fdc_id).first()

        existing_ids = {f.usda_fdc_id for f in SavedFood.query.filter(
            SavedFood.usda_fdc_id.isnot(None)
        ).with_entities(SavedFood.usda_fdc_id).all()}
        print(f'DB rows with usda_fdc_id: {len(existing_ids)}')

        updated = inserted = skipped = 0

        for r in rows:
            fdc_id = r['usda_fdc_id']
            if fdc_id is None:
                skipped += 1
                continue

            food = _get_food(fdc_id) if fdc_id in existing_ids else None
            if food:
                # Update existing row
                changed = []
                def _set(attr, val):
                    if getattr(food, attr) != val:
                        changed.append(f'{attr}: {getattr(food, attr)!r} -> {val!r}')
                        if not dry_run:
                            setattr(food, attr, val)

                _set('protein',         r['protein'])
                _set('fat',             r['fat'])
                _set('carbs',           r['carbs'])
                _set('calories',        r['calories'])
                _set('fiber',           r['fiber'])
                _set('sugar',           r['sugar'])
                _set('default_serving', r['default_serving'])
                _set('serving_unit',    r['serving_unit'])
                _set('g_per_unit',      r['g_per_unit'])
                _set('name',            r['name'])
                _set('name_tr',         r['name_tr'] or food.name_tr)

                if changed:
                    updated += 1
                    print(f'UPDATE {fdc_id} "{r["name"][:45]}"')
                    for c in changed:
                        print(f'  {c}')
            else:
                # Check once more with fresh query (guards against UNIQUE race)
                food = _get_food(fdc_id)
                if food:
                    existing_ids.add(fdc_id)
                    # Fall through to update path
                    changed = []
                    def _set2(attr, val):
                        if getattr(food, attr) != val:
                            changed.append(f'{attr}: {getattr(food, attr)!r} -> {val!r}')
                            if not dry_run:
                                setattr(food, attr, val)
                    _set2('protein', r['protein']); _set2('fat', r['fat'])
                    _set2('carbs', r['carbs']); _set2('calories', r['calories'])
                    _set2('fiber', r['fiber']); _set2('sugar', r['sugar'])
                    _set2('default_serving', r['default_serving'])
                    _set2('serving_unit', r['serving_unit'])
                    _set2('g_per_unit', r['g_per_unit'])
                    if changed:
                        updated += 1
                        print(f'UPDATE (was missing) {fdc_id} "{r["name"][:45]}"')
                else:
                    inserted += 1
                    print(f'INSERT {fdc_id} "{r["name"][:45]}"')
                    if not dry_run:
                        new_food = SavedFood(
                            usda_fdc_id    = fdc_id,
                            name           = r['name'],
                            name_tr        = r['name_tr'] or r['name'],
                            brand          = r.get('brand') or 'generic',
                            category       = r.get('category') or 'General',
                            source         = 'usda',
                            food_type      = r.get('food_type') or 'ingredient',
                            protein        = r['protein'],
                            fat            = r['fat'],
                            carbs          = r['carbs'],
                            calories       = r['calories'],
                            fiber          = r['fiber'],
                            sugar          = r['sugar'],
                            default_serving= r['default_serving'],
                            serving_unit   = r['serving_unit'],
                            g_per_unit     = r['g_per_unit'],
                        )
                        db.session.add(new_food)

        if not dry_run:
            db.session.commit()
            print(f'\nDone. Updated: {updated}  Inserted: {inserted}  Skipped: {skipped}')
        else:
            print(f'\nDRY RUN. Would update: {updated}  Insert: {inserted}  Skip: {skipped}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', default=CSV_DEFAULT)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    run(args.csv, dry_run=args.dry_run)
