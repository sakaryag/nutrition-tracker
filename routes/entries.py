from flask import Blueprint, jsonify, request, current_app, session
from datetime import date, datetime
from models import db
from models.food_entry import FoodEntry
from models.saved_food import SavedFood
from sqlalchemy import func

entries_bp = Blueprint('entries', __name__, url_prefix='/api/entries')


@entries_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


def _auto_calories(protein: float, fat: float, carbs: float) -> float:
    return (protein * 4) + (fat * 9) + (carbs * 4)


@entries_bp.route('', methods=['GET'])
def list_entries():
    """GET /api/entries?date=YYYY-MM-DD"""
    date_str = request.args.get('date')
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400
    else:
        target_date = date.today()

    entries = (
        FoodEntry.query
        .filter_by(entry_date=target_date)
        .order_by(FoodEntry.entry_time)
        .all()
    )
    return jsonify([e.to_dict() for e in entries])


@entries_bp.route('', methods=['POST'])
def create_entry():
    """POST /api/entries"""
    data = request.get_json(silent=True) or {}

    food_name = data.get('food_name', '').strip()
    if not food_name:
        return jsonify({'error': 'food_name is required'}), 400

    try:
        protein = float(data['protein'])
        fat = float(data['fat'])
        carbs = float(data['carbs'])
    except (KeyError, TypeError, ValueError):
        return jsonify({'error': 'protein, fat, and carbs are required numeric fields'}), 400

    raw_cal = data.get('calories')
    calories = float(raw_cal) if raw_cal is not None else _auto_calories(protein, fat, carbs)

    meal_type = data.get('meal_type', 'Snack')
    serving_size = data.get('serving_size')
    serving_unit = data.get('serving_unit', 'g')
    saved_food_id = data.get('saved_food_id')

    now = datetime.utcnow()
    raw_date = data.get('entry_date')
    if raw_date:
        try:
            entry_date = date.fromisoformat(raw_date)
        except ValueError:
            entry_date = now.date()
    else:
        entry_date = now.date()

    entry = FoodEntry(
        food_name=food_name,
        protein=protein,
        fat=fat,
        carbs=carbs,
        calories=calories,
        meal_type=meal_type,
        serving_size=float(serving_size) if serving_size is not None else None,
        serving_unit=serving_unit,
        saved_food_id=int(saved_food_id) if saved_food_id is not None else None,
        entry_date=entry_date,
        entry_time=now.time(),
    )
    db.session.add(entry)

    # Auto-save custom food: if the entry is not already linked to a saved food,
    # check whether one with this name exists; if not, create it automatically.
    food_auto_saved = False
    if not entry.saved_food_id:
        existing = (
            SavedFood.query
            .filter(func.lower(SavedFood.name) == food_name.lower())
            .first()
        )
        if existing is None:
            new_food = SavedFood(
                name=food_name,
                source='custom',
                protein=protein,
                fat=fat,
                carbs=carbs,
                calories=calories,
                default_serving=float(serving_size) if serving_size is not None else 100.0,
                serving_unit=serving_unit,
                is_archived=False,
            )
            db.session.add(new_food)
            db.session.flush()          # populate new_food.id before commit
            entry.saved_food_id = new_food.id
            food_auto_saved = True

    db.session.commit()
    result = entry.to_dict()
    result['food_auto_saved'] = food_auto_saved
    return jsonify(result), 201


@entries_bp.route('/<int:entry_id>', methods=['PUT'])
def update_entry(entry_id: int):
    """PUT /api/entries/<id>"""
    entry = db.session.get(FoodEntry, entry_id)
    if entry is None:
        return jsonify({'error': 'Entry not found'}), 404

    data = request.get_json(silent=True) or {}

    if 'food_name' in data:
        entry.food_name = data['food_name']
    if 'protein' in data:
        entry.protein = float(data['protein'])
    if 'fat' in data:
        entry.fat = float(data['fat'])
    if 'carbs' in data:
        entry.carbs = float(data['carbs'])
    if 'calories' in data and data['calories'] is not None:
        entry.calories = float(data['calories'])
    elif 'protein' in data or 'fat' in data or 'carbs' in data:
        if 'calories' not in data:
            entry.calories = _auto_calories(entry.protein, entry.fat, entry.carbs)
    if 'meal_type' in data:
        entry.meal_type = data['meal_type']
    if 'serving_size' in data:
        entry.serving_size = float(data['serving_size']) if data['serving_size'] is not None else None
    if 'serving_unit' in data:
        entry.serving_unit = data['serving_unit']
    if 'saved_food_id' in data:
        entry.saved_food_id = int(data['saved_food_id']) if data['saved_food_id'] is not None else None

    # If this entry is linked to a custom saved food, keep its macros in sync.
    if entry.saved_food_id:
        linked_food = db.session.get(SavedFood, entry.saved_food_id)
        if linked_food and linked_food.source == 'custom':
            if 'protein' in data:
                linked_food.protein = entry.protein
            if 'fat' in data:
                linked_food.fat = entry.fat
            if 'carbs' in data:
                linked_food.carbs = entry.carbs
            if 'calories' in data:
                linked_food.calories = entry.calories
            if 'serving_size' in data:
                linked_food.default_serving = entry.serving_size
            if 'serving_unit' in data:
                linked_food.serving_unit = entry.serving_unit

    db.session.commit()
    return jsonify(entry.to_dict())


@entries_bp.route('/<int:entry_id>', methods=['DELETE'])
def delete_entry(entry_id: int):
    """DELETE /api/entries/<id>"""
    entry = db.session.get(FoodEntry, entry_id)
    if entry is None:
        return jsonify({'error': 'Entry not found'}), 404

    db.session.delete(entry)
    db.session.commit()
    return jsonify({'deleted': entry_id})


@entries_bp.route('/recent', methods=['GET'])
def recent_entries():
    """GET /api/entries/recent — 20 most recently used unique food names."""
    subq = (
        db.session.query(
            FoodEntry.food_name,
            func.max(FoodEntry.id).label('max_id'),
        )
        .group_by(FoodEntry.food_name)
        .subquery()
    )

    rows = (
        db.session.query(FoodEntry)
        .join(subq, FoodEntry.id == subq.c.max_id)
        .order_by(FoodEntry.entry_date.desc(), FoodEntry.entry_time.desc())
        .limit(20)
        .all()
    )
    return jsonify([e.to_dict() for e in rows])