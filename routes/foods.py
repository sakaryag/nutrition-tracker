from flask import Blueprint, jsonify, request, current_app, session
from models import db
from models.saved_food import SavedFood

foods_bp = Blueprint('foods', __name__, url_prefix='/api/foods')


@foods_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


@foods_bp.route('', methods=['GET'])
def search_foods():
    """GET /api/foods?q=search&food_type=ingredient|meal"""
    q = request.args.get('q', '').strip()
    source = request.args.get('source', '').strip()
    food_type = request.args.get('food_type', '').strip()
    query = SavedFood.query.filter_by(is_archived=False)
    if source:
        query = query.filter_by(source=source)
    if food_type:
        query = query.filter_by(food_type=food_type)
    if q:
        query = query.filter(SavedFood.name.ilike(f'%{q}%'))
    foods = query.order_by(SavedFood.name).limit(50).all()
    return jsonify([f.to_dict() for f in foods])


@foods_bp.route('', methods=['POST'])
def create_food():
    """POST /api/foods"""
    data = request.get_json(silent=True) or {}

    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400

    try:
        protein = float(data['protein'])
        fat = float(data['fat'])
        carbs = float(data['carbs'])
    except (KeyError, TypeError, ValueError):
        return jsonify({'error': 'protein, fat, and carbs are required numeric fields'}), 400

    raw_cal = data.get('calories')
    calories = float(raw_cal) if raw_cal is not None else (protein * 4) + (fat * 9) + (carbs * 4)
    brand = data.get('brand', '')
    fiber = data.get('fiber')
    sugar = data.get('sugar')
    default_serving = data.get('default_serving', 100)
    serving_unit = data.get('serving_unit', 'g')
    food_type = data.get('food_type', 'ingredient')
    if food_type not in ('ingredient', 'meal'):
        food_type = 'ingredient'

    food = SavedFood(
        name=name,
        brand=brand.strip() if brand else None,
        protein=protein,
        fat=fat,
        carbs=carbs,
        calories=calories,
        fiber=float(fiber) if fiber is not None else None,
        sugar=float(sugar) if sugar is not None else None,
        default_serving=float(default_serving),
        serving_unit=serving_unit,
        food_type=food_type,
        source='custom',
        is_archived=False,
    )
    db.session.add(food)
    db.session.commit()
    return jsonify(food.to_dict()), 201


@foods_bp.route('/<int:food_id>', methods=['PUT'])
def update_food(food_id: int):
    """PUT /api/foods/<id>"""
    food = db.session.get(SavedFood, food_id)
    if food is None:
        return jsonify({'error': 'Food not found'}), 404
    if food.source == 'usda':
        return jsonify({'error': 'USDA foods cannot be edited. Clone the food first.'}), 403

    data = request.get_json(silent=True) or {}
    if 'name' in data:
        food.name = data['name']
    if 'brand' in data:
        food.brand = data['brand']
    if 'protein' in data:
        food.protein = float(data['protein'])
    if 'fat' in data:
        food.fat = float(data['fat'])
    if 'carbs' in data:
        food.carbs = float(data['carbs'])
    if 'calories' in data and data['calories'] is not None:
        food.calories = float(data['calories'])
    elif 'protein' in data or 'fat' in data or 'carbs' in data:
        if 'calories' not in data:
            food.calories = (food.protein * 4) + (food.fat * 9) + (food.carbs * 4)
    if 'fiber' in data:
        food.fiber = float(data['fiber']) if data['fiber'] is not None else None
    if 'sugar' in data:
        food.sugar = float(data['sugar']) if data['sugar'] is not None else None
    if 'default_serving' in data:
        food.default_serving = float(data['default_serving'])
    if 'serving_unit' in data:
        food.serving_unit = data['serving_unit']
    if 'food_type' in data and data['food_type'] in ('ingredient', 'meal'):
        food.food_type = data['food_type']

    db.session.commit()
    return jsonify(food.to_dict())


@foods_bp.route('/<int:food_id>', methods=['DELETE'])
def delete_food(food_id: int):
    """DELETE /api/foods/<id>"""
    food = db.session.get(SavedFood, food_id)
    if food is None:
        return jsonify({'error': 'Food not found'}), 404
    if food.source == 'usda':
        return jsonify({'error': 'USDA foods cannot be deleted. Clone the food first.'}), 403

    food.is_archived = True
    db.session.commit()
    return jsonify({'archived': food_id})


@foods_bp.route('/<int:food_id>/clone', methods=['POST'])
def clone_food(food_id: int):
    """POST /api/foods/<id>/clone"""
    food = db.session.get(SavedFood, food_id)
    if food is None:
        return jsonify({'error': 'Food not found'}), 404

    clone = SavedFood(
        name=food.name,
        brand=food.brand,
        category=food.category,
        protein=food.protein,
        fat=food.fat,
        carbs=food.carbs,
        calories=food.calories,
        fiber=food.fiber,
        sugar=food.sugar,
        default_serving=food.default_serving,
        serving_unit=food.serving_unit,
        food_type=food.food_type,
        source='custom',
        is_archived=False,
    )
    db.session.add(clone)
    db.session.commit()
    return jsonify(clone.to_dict()), 201