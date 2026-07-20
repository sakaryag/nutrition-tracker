import csv
import os
import click
from flask import current_app
from flask.cli import with_appcontext
from models import db
from models.saved_food import SavedFood


def seed_db() -> None:
    """Bulk-insert USDA foods from CSV into saved_food table.

    Idempotent: deletes any existing usda entries before re-inserting, so
    this can be called safely on every startup even with a persistent DB.
    """
    csv_path = os.path.join(os.path.dirname(__file__), 'foods.csv')

    rows = []
    with open(csv_path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            def _float(val: str):
                val = val.strip()
                if val == '':
                    return None
                try:
                    return float(val)
                except ValueError:
                    return None

            usda_fdc_id = int(row['usda_fdc_id']) if row['usda_fdc_id'].strip() else None
            protein = _float(row['protein']) or 0.0
            fat = _float(row['fat']) or 0.0
            carbs = _float(row['carbs']) or 0.0
            calories = _float(row['calories'])
            if calories is None:
                calories = (protein * 4) + (fat * 9) + (carbs * 4)
            fiber = _float(row['fiber'])
            sugar = _float(row['sugar'])
            default_serving = _float(row['default_serving']) or 100.0

            rows.append(
                SavedFood(
                    usda_fdc_id=usda_fdc_id,
                    name=row['name'].strip(),
                    brand=row['brand'].strip() or None,
                    category=row['category'].strip() or None,
                    protein=protein,
                    fat=fat,
                    carbs=carbs,
                    calories=calories,
                    fiber=fiber,
                    sugar=sugar,
                    default_serving=default_serving,
                    serving_unit=row['serving_unit'].strip() or 'g',
                    source='usda',
                    is_archived=False,
                )
            )

    # Delete any existing USDA records to allow clean re-seed
    SavedFood.query.filter_by(source='usda').delete()
    db.session.commit()

    db.session.bulk_save_objects(rows)
    db.session.commit()
    current_app.logger.info('Seeded %d USDA foods.', len(rows))


@click.command('seed')
@with_appcontext
def seed_command() -> None:
    """Seed the database with USDA food data."""
    seed_db()
    click.echo('Seed complete.')