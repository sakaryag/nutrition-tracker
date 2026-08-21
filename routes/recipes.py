from flask import Blueprint, jsonify, request, current_app, session
from models import db
from models.recipe import Recipe
from models.recipe_ingredient import RecipeIngredient
from models.saved_food import SavedFood
from routes.auth import current_user_id

recipes_bp = Blueprint('recipes', __name__, url_prefix='/api/recipes')


@recipes_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


def _compute_ingredient_macros(food, quantity, unit):
    """Scale SavedFood macros to the given quantity (grams assumed when unit='g')."""
    if food is None:
        return None, None, None, None
    scale = quantity / 100.0  # food macros stored per 100g
    return (
        round((food.protein or 0) * scale, 1),
        round((food.fat or 0) * scale, 1),
        round((food.carbs or 0) * scale, 1),
        round((food.calories or 0) * scale, 1),
    )


def _apply_ingredients(recipe, ingredients_data):
    """Replace all ingredients on a recipe. ingredients_data is a list of dicts."""
    # Delete existing
    RecipeIngredient.query.filter_by(recipe_id=recipe.id).delete()
    for i, ing_data in enumerate(ingredients_data):
        saved_food_id = ing_data.get('saved_food_id')
        food = db.session.get(SavedFood, saved_food_id) if saved_food_id else None
        qty = float(ing_data.get('quantity', 0))
        unit = ing_data.get('unit', 'g')
        protein, fat, carbs, calories = _compute_ingredient_macros(food, qty, unit)
        ing = RecipeIngredient(
            recipe_id=recipe.id,
            saved_food_id=saved_food_id,
            food_name_override=ing_data.get('food_name_override') or (food.name if food else None),
            quantity=qty,
            unit=unit,
            sort_order=i,
            protein=protein,
            fat=fat,
            carbs=carbs,
            calories=calories,
        )
        db.session.add(ing)
    db.session.flush()
    recipe.recalculate_totals()


@recipes_bp.route('', methods=['GET'])
def list_recipes():
    uid = current_user_id()
    q = request.args.get('q', '').strip()
    query = Recipe.query.filter_by(owner_id=uid, is_archived=False)
    if q:
        query = query.filter(Recipe.name.ilike(f'%{q}%'))
    recipes = query.order_by(Recipe.name).all()
    return jsonify([r.to_dict() for r in recipes])


@recipes_bp.route('', methods=['POST'])
def create_recipe():
    uid = current_user_id()
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    recipe = Recipe(
        name=name,
        name_tr=data.get('name_tr', '').strip() or None,
        owner_id=uid,
        prep_notes=data.get('prep_notes', '').strip() or None,
        prep_notes_tr=data.get('prep_notes_tr', '').strip() or None,
        category_tags=data.get('category_tags'),
    )
    db.session.add(recipe)
    db.session.flush()
    if data.get('ingredients'):
        _apply_ingredients(recipe, data['ingredients'])
    db.session.commit()
    return jsonify(recipe.to_dict()), 201


@recipes_bp.route('/<int:recipe_id>', methods=['GET'])
def get_recipe(recipe_id):
    uid = current_user_id()
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None or recipe.owner_id != uid:
        return jsonify({'error': 'Recipe not found'}), 404
    return jsonify(recipe.to_dict())


@recipes_bp.route('/<int:recipe_id>', methods=['PUT'])
def update_recipe(recipe_id):
    uid = current_user_id()
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None or recipe.owner_id != uid:
        return jsonify({'error': 'Recipe not found'}), 404
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        recipe.name = data['name'].strip()
    if 'name_tr' in data:
        recipe.name_tr = data['name_tr'].strip() or None
    if 'prep_notes' in data:
        recipe.prep_notes = data['prep_notes'].strip() or None
    if 'prep_notes_tr' in data:
        recipe.prep_notes_tr = data['prep_notes_tr'].strip() or None
    if 'category_tags' in data:
        recipe.category_tags = data['category_tags']
    if 'is_archived' in data:
        recipe.is_archived = bool(data['is_archived'])
    if 'ingredients' in data:
        _apply_ingredients(recipe, data['ingredients'])
    db.session.commit()
    return jsonify(recipe.to_dict())


@recipes_bp.route('/<int:recipe_id>', methods=['DELETE'])
def delete_recipe(recipe_id):
    uid = current_user_id()
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None or recipe.owner_id != uid:
        return jsonify({'error': 'Recipe not found'}), 404
    db.session.delete(recipe)
    db.session.commit()
    return jsonify({'deleted': recipe_id})
