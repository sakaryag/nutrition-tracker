import sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ku = os.getenv("KAGGLE_USERNAME")
kk = os.getenv("KAGGLE_KEY")
if ku and kk:
    os.environ["KAGGLE_USERNAME"] = ku
    os.environ["KAGGLE_KEY"] = kk

try:
    import kagglehub
    import pandas as pd
    import json
except ImportError:
    print("Run: pip install kagglehub[pandas-datasets] pandas")
    sys.exit(1)

from app import create_app
from models import db
from models.saved_food import SavedFood

def _float(val, default=0.0):
    try:
        return float(val)
    except Exception:
        return default

def _str(val, default=""):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return str(val).strip()

def _kcal(p, f, c, cal=None):
    if cal and cal > 0:
        return round(cal, 1)
    return round(p * 4 + f * 9 + c * 4, 1)

def import_turkish(app):
    print("\n--- Turkish Recipes (bit104/turkish-recipes-structured) ---")
    path = kagglehub.dataset_download("bit104/turkish-recipes-structured")
    json_file = os.path.join(path, "recipes_groq_cleaned.json")
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)
    print(f"  Records: {len(data)}")

    # Turkish dataset columns: tarif_adi (name), kategori (category), porsiyon (serving)
    # No macro data — imported with 0s so user can search by name and fill macros later
    count = 0
    with app.app_context():
        for item in data:
            name = _str(item.get("tarif_adi") or item.get("name") or item.get("title"))
            if not name:
                continue
            if SavedFood.query.filter_by(name=name, food_type="meal").first():
                continue
            cat = _str(item.get("kategori") or item.get("category") or "Turkish")
            db.session.add(SavedFood(
                name=name, brand=None, category=cat,
                protein=0.0, fat=0.0, carbs=0.0, calories=0.0,
                default_serving=250.0, serving_unit="g",
                source="usda", food_type="meal", is_archived=False,
            ))
            count += 1
        db.session.commit()
    print(f"  Imported {count} Turkish recipes (macros not in dataset — fill via My Foods).")
    return count

if __name__ == "__main__":
    app = create_app()
    total = import_turkish(app)
    print(f"\nDone. Total meals imported: {total}")
    print("Note: Turkish recipes have no macro data in the dataset.")
    print("Search for them in Meal Templates -> Meals, then edit macros via My Foods.")