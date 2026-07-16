from flask import Blueprint, jsonify, request, current_app, session
from datetime import date, datetime
from models import db
from models.meal_template import MealTemplate
from models.meal_template_item import MealTemplateItem
from models.food_entry import FoodEntry

meal_templates_bp = Blueprint('meal_templates', __name__, url_prefix='/api/meal-templates')


@meal_templates_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


@meal_templates_bp.route('', methods=['GET'])
def list_templates():
    templates = MealTemplate.query.order_by(MealTemplate.name).all()
    return jsonify([t.to_dict() for t in templates])


@meal_templates_bp.route('', methods=['POST'])
def create_template():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400

    template = MealTemplate(
        name=name,
        meal_type=data.get('meal_type', 'Snack'),
    )
    db.session.add(template)
    db.session.flush()

    for item_data in data.get('items', []):
        food_name = item_data.get('food_name', '').strip()
        if not food_name:
            continue
        try:
            protein = float(item_data['protein'])
            fat = float(item_data['fat'])
            carbs = float(item_data['carbs'])
        except (KeyError, TypeError, ValueError):
            continue
        raw_cal = item_data.get('calories')
        calories = float(raw_cal) if raw_cal is not None else (protein * 4) + (fat * 9) + (carbs * 4)
        item = MealTemplateItem(
            template_id=template.id,
            food_name=food_name,
            saved_food_id=item_data.get('saved_food_id'),
            protein=protein,
            fat=fat,
            carbs=carbs,
            calories=calories,
            serving_size=float(item_data['serving_size']) if item_data.get('serving_size') is not None else None,
            serving_unit=item_data.get('serving_unit', 'g'),
        )
        db.session.add(item)

    db.session.commit()
    return jsonify(template.to_dict()), 201


@meal_templates_bp.route('/<int:template_id>', methods=['GET'])
def get_template(template_id):
    template = db.session.get(MealTemplate, template_id)
    if template is None:
        return jsonify({'error': 'Template not found'}), 404
    return jsonify(template.to_dict())


@meal_templates_bp.route('/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    template = db.session.get(MealTemplate, template_id)
    if template is None:
        return jsonify({'error': 'Template not found'}), 404

    data = request.get_json(silent=True) or {}
    if 'name' in data:
        template.name = data['name'].strip()
    if 'meal_type' in data:
        template.meal_type = data['meal_type']

    if 'items' in data:
        MealTemplateItem.query.filter_by(template_id=template.id).delete()
        for item_data in data['items']:
            food_name = item_data.get('food_name', '').strip()
            if not food_name:
                continue
            try:
                protein = float(item_data['protein'])
                fat = float(item_data['fat'])
                carbs = float(item_data['carbs'])
            except (KeyError, TypeError, ValueError):
                continue
            raw_cal = item_data.get('calories')
            calories = float(raw_cal) if raw_cal is not None else (protein * 4) + (fat * 9) + (carbs * 4)
            item = MealTemplateItem(
                template_id=template.id,
                food_name=food_name,
                saved_food_id=item_data.get('saved_food_id'),
                protein=protein,
                fat=fat,
                carbs=carbs,
                calories=calories,
                serving_size=float(item_data['serving_size']) if item_data.get('serving_size') is not None else None,
                serving_unit=item_data.get('serving_unit', 'g'),
            )
            db.session.add(item)

    db.session.commit()
    return jsonify(template.to_dict())


@meal_templates_bp.route('/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    template = db.session.get(MealTemplate, template_id)
    if template is None:
        return jsonify({'error': 'Template not found'}), 404
    db.session.delete(template)
    db.session.commit()
    return jsonify({'deleted': template_id})


@meal_templates_bp.route('/<int:template_id>/log', methods=['POST'])
def log_template(template_id):
    template = db.session.get(MealTemplate, template_id)
    if template is None:
        return jsonify({'error': 'Template not found'}), 404

    data = request.get_json(silent=True) or {}
    raw_date = data.get('date')
    if raw_date:
        try:
            entry_date = date.fromisoformat(raw_date)
        except ValueError:
            entry_date = date.today()
    else:
        entry_date = date.today()

    now = datetime.utcnow()
    entries = []
    for item in template.items:
        entry = FoodEntry(
            food_name=item.food_name,
            protein=item.protein,
            fat=item.fat,
            carbs=item.carbs,
            calories=item.calories,
            meal_type=template.meal_type,
            serving_size=item.serving_size,
            serving_unit=item.serving_unit,
            saved_food_id=item.saved_food_id,
            entry_date=entry_date,
            entry_time=now.time(),
        )
        db.session.add(entry)
        entries.append(entry)

    db.session.commit()
    return jsonify({
        'logged': len(entries),
        'template': template.name,
        'entries': [e.to_dict() for e in entries],
    }), 201