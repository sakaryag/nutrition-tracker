"""tests/test_seed_data.py

Regression tests for:
  1. _patch_food_data() — verifies it corrects known-bad calorie/macro values
  2. meal_type field — verifies it round-trips through POST /api/entries -> GET /api/entries
"""
import pytest
from datetime import date

from models import db
from models.saved_food import SavedFood
from models.food_entry import FoodEntry


# ---------------------------------------------------------------------------
# Helper: insert a SavedFood with wrong values then run the patch
# ---------------------------------------------------------------------------

def _insert_bad_food(fdc_id, name, protein, fat, carbs, calories, serving_unit="g", default_serving=100):
    food = SavedFood(
        usda_fdc_id=str(fdc_id),
        name=name,
        source="usda",
        food_type="ingredient",
        protein=protein, fat=fat, carbs=carbs, calories=calories,
        default_serving=default_serving,
        serving_unit=serving_unit,
    )
    db.session.add(food)
    db.session.commit()
    return food


def _run_patch(app):
    from app import _patch_food_data
    _patch_food_data(app)


# ---------------------------------------------------------------------------
# PR1: food data correctness — _patch_food_data corrects known-bad values
# ---------------------------------------------------------------------------

class TestPatchFoodData:
    def test_peanut_butter_creamy_corrected(self, client, db_session, app):
        # Insert with old wrong values (per-tbsp macros stored as per-100g)
        _insert_bad_food(170527, "Peanut butter, creamy",
                         protein=15.4, fat=32.0, carbs=15.4, calories=376,
                         serving_unit="tbsp", default_serving=32)
        _run_patch(app)
        food = SavedFood.query.filter_by(usda_fdc_id="170527").first()
        assert food is not None
        assert food.calories == pytest.approx(598, abs=10)
        assert food.protein == pytest.approx(22.2, abs=1.0)
        assert food.fat == pytest.approx(51.4, abs=1.0)
        assert food.serving_unit == "g"

    def test_peanut_butter_chunky_corrected(self, client, db_session, app):
        _insert_bad_food(170528, "Peanut butter, chunky",
                         protein=15.4, fat=32.0, carbs=15.4, calories=376,
                         serving_unit="tbsp", default_serving=32)
        _run_patch(app)
        food = SavedFood.query.filter_by(usda_fdc_id="170528").first()
        assert food.calories == pytest.approx(589, abs=10)
        assert food.serving_unit == "g"

    def test_medjool_dates_corrected(self, client, db_session, app):
        # Old: 280 kcal per piece (per-100g value stored as per-piece)
        _insert_bad_food(170335, "Date, Medjool",
                         protein=1.8, fat=0.2, carbs=75.0, calories=280,
                         serving_unit="piece", default_serving=1)
        _run_patch(app)
        food = SavedFood.query.filter_by(usda_fdc_id="170335").first()
        assert food.calories == pytest.approx(277, abs=10)
        assert food.default_serving == pytest.approx(24, abs=5)
        assert food.serving_unit == "g"

    def test_grape_jelly_corrected(self, client, db_session, app):
        # Old: 28g carbs per tbsp (impossible — tbsp is ~20g total)
        _insert_bad_food(170717, "Jelly, grape",
                         protein=0.4, fat=0.0, carbs=28.0, calories=107,
                         serving_unit="tbsp", default_serving=20)
        _run_patch(app)
        food = SavedFood.query.filter_by(usda_fdc_id="170717").first()
        assert food.calories == pytest.approx(250, abs=15)
        assert food.carbs == pytest.approx(69, abs=5)
        assert food.serving_unit == "g"

    def test_english_muffin_corrected(self, client, db_session, app):
        # Old: 230 kcal per piece (per-100g stored as per-piece)
        _insert_bad_food(170202, "English muffin",
                         protein=8.3, fat=1.5, carbs=42.0, calories=230,
                         serving_unit="piece", default_serving=1)
        _run_patch(app)
        food = SavedFood.query.filter_by(usda_fdc_id="170202").first()
        assert food.calories == pytest.approx(223, abs=10)
        assert food.default_serving == pytest.approx(57, abs=5)
        assert food.serving_unit == "g"

    def test_patch_is_idempotent(self, client, db_session, app):
        """Running patch twice should not change already-correct values."""
        _insert_bad_food(170527, "Peanut butter, creamy",
                         protein=15.4, fat=32.0, carbs=15.4, calories=376,
                         serving_unit="tbsp", default_serving=32)
        _run_patch(app)
        food_after_first = SavedFood.query.filter_by(usda_fdc_id="170527").first()
        cal_after_first = food_after_first.calories
        _run_patch(app)
        food_after_second = SavedFood.query.filter_by(usda_fdc_id="170527").first()
        assert food_after_second.calories == cal_after_first

    def test_patch_skips_missing_foods(self, client, db_session, app):
        """Patch should not raise if a food is not in the DB."""
        # DB is empty for this food — patch should silently do nothing
        _run_patch(app)  # no 170527 inserted
        food = SavedFood.query.filter_by(usda_fdc_id="170527").first()
        assert food is None  # still missing, no error


# ---------------------------------------------------------------------------
# PR2: meal_type round-trips through entry API
# ---------------------------------------------------------------------------

class TestEntryMealType:
    def test_meal_type_present_in_get_response(self, client, db_session):
        rv = client.post("/api/entries", json={
            "food_name": "Oatmeal",
            "protein": 5.0, "fat": 3.0, "carbs": 27.0,
            "entry_date": "2024-06-01",
            "meal_type": "breakfast",
        })
        assert rv.status_code == 201

        rv2 = client.get("/api/entries?date=2024-06-01")
        assert rv2.status_code == 200
        entries = rv2.get_json()
        assert len(entries) >= 1
        assert "meal_type" in entries[0]
        assert entries[0]["meal_type"] == "breakfast"

    def test_meal_type_null_when_omitted(self, client, db_session):
        rv = client.post("/api/entries", json={
            "food_name": "Mystery food",
            "protein": 10.0, "fat": 5.0, "carbs": 20.0,
            "entry_date": "2024-06-02",
        })
        assert rv.status_code == 201
        rv2 = client.get("/api/entries?date=2024-06-02")
        entries = rv2.get_json()
        # meal_type key must exist; value may be None or empty string
        assert "meal_type" in entries[0]

    def test_all_meal_types_accepted(self, client, db_session):
        for mt in ("breakfast", "lunch", "dinner", "snack"):
            rv = client.post("/api/entries", json={
                "food_name": f"Food-{mt}",
                "protein": 10.0, "fat": 5.0, "carbs": 20.0,
                "entry_date": "2024-06-03",
                "meal_type": mt,
            })
            assert rv.status_code == 201

        rv2 = client.get("/api/entries?date=2024-06-03")
        entries = rv2.get_json()
        returned_types = {e["meal_type"] for e in entries}
        for mt in ("breakfast", "lunch", "dinner", "snack"):
            assert mt in returned_types