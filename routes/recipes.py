from flask import Blueprint, jsonify, request, current_app, session
from datetime import date, datetime, timezone
from models import db
from models.recipe import Recipe
from models.recipe_ingredient import RecipeIngredient
from models.saved_food import SavedFood
from models.food_entry import FoodEntry
from routes.auth import current_user_id

recipes_bp = Blueprint('recipes', __name__, url_prefix='/api/recipes')


@recipes_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


def _compute_ingredient_macros(food, quantity, unit):
    """Scale SavedFood macros to the given quantity.

    Food macros are stored per 100 g/ml. For piece/slice/serving units,
    the food's g_per_unit field gives the gram weight of one unit so we
    can convert back to the per-100 g basis.
    """
    if food is None:
        return None, None, None, None
    if unit in ('piece', 'slice', 'serving') and food.g_per_unit:
        scale = quantity * food.g_per_unit / 100.0
    else:
        scale = quantity / 100.0
    return (
        round((food.protein or 0) * scale, 1),
        round((food.fat or 0) * scale, 1),
        round((food.carbs or 0) * scale, 1),
        round((food.calories or 0) * scale, 1),
    )


def _apply_ingredients(recipe, ingredients_data):
    """Replace all ingredients on a recipe. ingredients_data is a list of dicts."""
    RecipeIngredient.query.filter_by(recipe_id=recipe.id).delete()
    for i, ing_data in enumerate(ingredients_data):
        saved_food_id = ing_data.get('saved_food_id') or ing_data.get('food_id')
        food = db.session.get(SavedFood, saved_food_id) if saved_food_id else None
        qty = float(ing_data.get('quantity', 100))
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


def _own_recipe(recipe_id):
    """Fetch recipe and verify ownership. Returns (recipe, error_response)."""
    uid = current_user_id()
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None or (uid is not None and recipe.owner_id != uid):
        return None, (jsonify({'error': 'Recipe not found'}), 404)
    return recipe, None


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@recipes_bp.route('', methods=['GET'])
def list_recipes():
    uid = current_user_id()
    q = request.args.get('q', '').strip()
    query = Recipe.query.filter_by(is_archived=False)
    if uid is not None:
        query = query.filter_by(owner_id=uid)
    if q:
        query = query.filter(Recipe.name.ilike(f'%{q}%'))
    return jsonify([r.to_dict() for r in query.order_by(Recipe.name).all()])


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
        prep_notes=(data.get('prep_notes') or data.get('description') or '').strip() or None,
        prep_notes_tr=data.get('prep_notes_tr', '').strip() or None,
        category_tags=data.get('category_tags'),
        servings=max(1, int(data.get('servings', 1) or 1)),
    )
    db.session.add(recipe)
    db.session.flush()
    if data.get('ingredients'):
        _apply_ingredients(recipe, data['ingredients'])
    else:
        recipe.recalculate_totals()  # initialise totals to 0
    db.session.commit()
    return jsonify(recipe.to_dict()), 201


@recipes_bp.route('/<int:recipe_id>', methods=['GET'])
def get_recipe(recipe_id):
    recipe, err = _own_recipe(recipe_id)
    if err:
        return err
    return jsonify(recipe.to_dict())


@recipes_bp.route('/<int:recipe_id>', methods=['PUT'])
def update_recipe(recipe_id):
    recipe, err = _own_recipe(recipe_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        recipe.name = data['name'].strip()
    if 'name_tr' in data:
        recipe.name_tr = data['name_tr'].strip() or None
    if 'prep_notes' in data:
        recipe.prep_notes = data['prep_notes'].strip() or None
    if 'description' in data:
        recipe.prep_notes = data['description'].strip() or None
    if 'prep_notes_tr' in data:
        recipe.prep_notes_tr = data['prep_notes_tr'].strip() or None
    if 'category_tags' in data:
        recipe.category_tags = data['category_tags']
    if 'servings' in data:
        recipe.servings = max(1, int(data['servings'] or 1))
    if 'is_archived' in data:
        recipe.is_archived = bool(data['is_archived'])
    if 'ingredients' in data:
        _apply_ingredients(recipe, data['ingredients'])
    db.session.commit()
    return jsonify(recipe.to_dict())


@recipes_bp.route('/<int:recipe_id>', methods=['DELETE'])
def delete_recipe(recipe_id):
    recipe, err = _own_recipe(recipe_id)
    if err:
        return err
    db.session.delete(recipe)
    db.session.commit()
    return jsonify({'deleted': recipe_id})


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

@recipes_bp.route('/<int:recipe_id>/log', methods=['POST'])
def log_recipe(recipe_id):
    """Log each ingredient as a separate FoodEntry for a given date."""
    recipe, err = _own_recipe(recipe_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    raw_date = data.get('date')
    try:
        entry_date = date.fromisoformat(raw_date) if raw_date else date.today()
    except ValueError:
        entry_date = date.today()

    meal_type = data.get('meal_type', 'Snack')
    uid = current_user_id()
    now = datetime.now(timezone.utc)
    entries = []
    for ing in recipe.ingredients:
        food_name = (
            ing.food_name_override
            or (ing.saved_food.name if ing.saved_food else None)
            or 'Unknown'
        )
        entry = FoodEntry(
            food_name=food_name,
            protein=ing.protein or 0,
            fat=ing.fat or 0,
            carbs=ing.carbs or 0,
            calories=ing.calories or 0,
            meal_type=meal_type,
            serving_size=ing.quantity,
            serving_unit=ing.unit,
            saved_food_id=ing.saved_food_id,
            user_id=uid,
            entry_date=entry_date,
            entry_time=now.time(),
        )
        db.session.add(entry)
        entries.append(entry)

    db.session.commit()
    return jsonify({
        'logged': len(entries),
        'recipe': recipe.name,
        'entries': [e.to_dict() for e in entries],
    }), 201


@recipes_bp.route('/<int:recipe_id>/save-as-food', methods=['POST'])
def save_recipe_as_food(recipe_id):
    """Save the recipe's total macros as a custom SavedFood (appears in food search)."""
    recipe, err = _own_recipe(recipe_id)
    if err:
        return err

    # Update if a custom food with the same name already exists
    existing = SavedFood.query.filter_by(name=recipe.name, source='custom').first()
    if existing:
        existing.protein = round(recipe.total_protein or 0, 1)
        existing.fat = round(recipe.total_fat or 0, 1)
        existing.carbs = round(recipe.total_carbs or 0, 1)
        existing.calories = round(recipe.total_calories or 0, 1)
        db.session.commit()
        return jsonify({'food': existing.to_dict(), 'updated': True}), 200

    food = SavedFood(
        name=recipe.name,
        source='custom',
        protein=round(recipe.total_protein or 0, 1),
        fat=round(recipe.total_fat or 0, 1),
        carbs=round(recipe.total_carbs or 0, 1),
        calories=round(recipe.total_calories or 0, 1),
        food_type='meal',
        default_serving=100,
        serving_unit='g',
    )
    db.session.add(food)
    db.session.commit()
    return jsonify({'food': food.to_dict(), 'created': True}), 201
