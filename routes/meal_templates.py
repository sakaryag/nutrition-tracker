from flask import Blueprint, jsonify, request, current_app, session
from datetime import date, datetime
from models import db
from models.meal_template import MealTemplate
from models.meal_template_item import MealTemplateItem
from models.food_entry import FoodEntry
from routes.auth import current_user_id

meal_templates_bp = Blueprint('meal_templates', __name__, url_prefix='/api/meal-templates')


@meal_templates_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


@meal_templates_bp.route('', methods=['GET'])
def list_templates():
    uid = current_user_id()
    q = MealTemplate.query
    if uid is not None:
        q = q.filter_by(user_id=uid)
    return jsonify([t.to_dict() for t in q.order_by(MealTemplate.name).all()])


@meal_templates_bp.route('', methods=['POST'])
def create_template():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400

    template = MealTemplate(
        name=name,
        meal_type=data.get('meal_type', 'Snack'),
        user_id=current_user_id(),
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


def _own_template(template_id):
    """Fetch template and verify ownership. Returns (template, error_response)."""
    uid = current_user_id()
    template = db.session.get(MealTemplate, template_id)
    if template is None or (uid is not None and template.user_id != uid):
        return None, (jsonify({'error': 'Template not found'}), 404)
    return template, None


@meal_templates_bp.route('/<int:template_id>', methods=['GET'])
def get_template(template_id):
    template, err = _own_template(template_id)
    if err:
        return err
    return jsonify(template.to_dict())


@meal_templates_bp.route('/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    template, err = _own_template(template_id)
    if err:
        return err

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
    template, err = _own_template(template_id)
    if err:
        return err
    db.session.delete(template)
    db.session.commit()
    return jsonify({'deleted': template_id})


@meal_templates_bp.route('/<int:template_id>/log', methods=['POST'])
def log_template(template_id):
    template, err = _own_template(template_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    raw_date = data.get('date')
    if raw_date:
        try:
            entry_date = date.fromisoformat(raw_date)
        except ValueError:
            entry_date = date.today()
    else:
        entry_date = date.today()

    uid = current_user_id()
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
            user_id=uid,
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


@meal_templates_bp.route('/<int:template_id>/log-single', methods=['POST'])
def log_template_single(template_id):
    """Log a template as one combined entry (total macros summed)."""
    template, err = _own_template(template_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    raw_date = data.get('date')
    try:
        entry_date = date.fromisoformat(raw_date) if raw_date else date.today()
    except ValueError:
        entry_date = date.today()

    meal_type = data.get('meal_type') or template.meal_type

    total_protein = sum(i.protein for i in template.items)
    total_fat = sum(i.fat for i in template.items)
    total_carbs = sum(i.carbs for i in template.items)
    total_calories = sum(i.calories for i in template.items)
    total_serving = sum((i.serving_size or 0) for i in template.items)

    now = datetime.utcnow()
    entry = FoodEntry(
        food_name=template.name,
        protein=round(total_protein, 1),
        fat=round(total_fat, 1),
        carbs=round(total_carbs, 1),
        calories=round(total_calories, 1),
        meal_type=meal_type,
        serving_size=round(total_serving, 1) if total_serving else None,
        serving_unit='g',
        saved_food_id=None,
        entry_date=entry_date,
        entry_time=now.time(),
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({'logged': 1, 'template': template.name, 'entry': entry.to_dict()}), 201