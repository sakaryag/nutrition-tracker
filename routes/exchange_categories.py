from flask import Blueprint, jsonify, request, current_app, session
from models import db
from models.food_exchange_category import FoodExchangeCategory
from models.exchange_category_member import ExchangeCategoryMember
from models.saved_food import SavedFood
from routes.auth import current_user_id

exchange_categories_bp = Blueprint('exchange_categories', __name__, url_prefix='/api/exchange-categories')


@exchange_categories_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


def _apply_members(category, members_data):
    """Replace all members on a category."""
    ExchangeCategoryMember.query.filter_by(category_id=category.id).delete()
    for i, m in enumerate(members_data):
        saved_food_id = m.get('saved_food_id')
        member = ExchangeCategoryMember(
            category_id=category.id,
            saved_food_id=saved_food_id,
            food_name_override=m.get('food_name_override') or None,
            equivalent_qty=float(m.get('equivalent_qty', 0)),
            equivalent_unit=m.get('equivalent_unit', 'g'),
            sort_order=i,
        )
        db.session.add(member)


@exchange_categories_bp.route('', methods=['GET'])
def list_categories():
    uid = current_user_id()
    q = request.args.get('q', '').strip()
    query = FoodExchangeCategory.query.filter_by(owner_id=uid)
    if q:
        query = query.filter(FoodExchangeCategory.name.ilike(f'%{q}%'))
    categories = query.order_by(FoodExchangeCategory.name).all()
    return jsonify([c.to_dict() for c in categories])


@exchange_categories_bp.route('', methods=['POST'])
def create_category():
    uid = current_user_id()
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    # Enforce uniqueness per owner
    existing = FoodExchangeCategory.query.filter_by(owner_id=uid, name=name).first()
    if existing:
        return jsonify({'error': 'A category with that name already exists'}), 409
    cat = FoodExchangeCategory(
        name=name,
        name_tr=data.get('name_tr', '').strip() or None,
        owner_id=uid,
        description=data.get('description', '').strip() or None,
    )
    db.session.add(cat)
    db.session.flush()
    if data.get('members'):
        _apply_members(cat, data['members'])
    db.session.commit()
    return jsonify(cat.to_dict()), 201


@exchange_categories_bp.route('/<int:cat_id>', methods=['GET'])
def get_category(cat_id):
    uid = current_user_id()
    cat = db.session.get(FoodExchangeCategory, cat_id)
    if cat is None or cat.owner_id != uid:
        return jsonify({'error': 'Category not found'}), 404
    return jsonify(cat.to_dict())


@exchange_categories_bp.route('/<int:cat_id>', methods=['PUT'])
def update_category(cat_id):
    uid = current_user_id()
    cat = db.session.get(FoodExchangeCategory, cat_id)
    if cat is None or cat.owner_id != uid:
        return jsonify({'error': 'Category not found'}), 404
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        cat.name = data['name'].strip()
    if 'name_tr' in data:
        cat.name_tr = data['name_tr'].strip() or None
    if 'description' in data:
        cat.description = data['description'].strip() or None
    if 'members' in data:
        _apply_members(cat, data['members'])
    db.session.commit()
    return jsonify(cat.to_dict())


@exchange_categories_bp.route('/<int:cat_id>', methods=['DELETE'])
def delete_category(cat_id):
    uid = current_user_id()
    cat = db.session.get(FoodExchangeCategory, cat_id)
    if cat is None or cat.owner_id != uid:
        return jsonify({'error': 'Category not found'}), 404
    db.session.delete(cat)
    db.session.commit()
    return jsonify({'deleted': cat_id})
