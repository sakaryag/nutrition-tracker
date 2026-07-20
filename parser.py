"""
Rule-based fallback food parser.
Returns the same JSON schema used by the Claude integration.
"""
import re

# Basic nutrition estimates per 100g for common foods (protein, fat, carbs, calories)
_FOOD_DB = {
    'egg':          {'protein': 13.0, 'fat': 11.0, 'carbs': 1.1,  'calories': 155,  'unit': 'piece', 'default_qty': 1},
    'chicken':      {'protein': 31.0, 'fat': 3.6,  'carbs': 0.0,  'calories': 165,  'unit': 'g',     'default_qty': 150},
    'rice':         {'protein': 2.7,  'fat': 0.3,  'carbs': 28.0, 'calories': 130,  'unit': 'g',     'default_qty': 150},
    'bread':        {'protein': 9.0,  'fat': 3.2,  'carbs': 49.0, 'calories': 265,  'unit': 'slice',  'default_qty': 2},
    'milk':         {'protein': 3.4,  'fat': 3.6,  'carbs': 4.8,  'calories': 61,   'unit': 'ml',    'default_qty': 250},
    'banana':       {'protein': 1.1,  'fat': 0.3,  'carbs': 23.0, 'calories': 89,   'unit': 'piece', 'default_qty': 1},
    'apple':        {'protein': 0.3,  'fat': 0.2,  'carbs': 14.0, 'calories': 52,   'unit': 'piece', 'default_qty': 1},
    'oat':          {'protein': 17.0, 'fat': 7.0,  'carbs': 66.0, 'calories': 389,  'unit': 'g',     'default_qty': 50},
    'oats':         {'protein': 17.0, 'fat': 7.0,  'carbs': 66.0, 'calories': 389,  'unit': 'g',     'default_qty': 50},
    'yogurt':       {'protein': 10.0, 'fat': 0.4,  'carbs': 3.6,  'calories': 59,   'unit': 'g',     'default_qty': 150},
    'pasta':        {'protein': 5.0,  'fat': 1.1,  'carbs': 25.0, 'calories': 131,  'unit': 'g',     'default_qty': 150},
    'salmon':       {'protein': 25.0, 'fat': 13.0, 'carbs': 0.0,  'calories': 208,  'unit': 'g',     'default_qty': 150},
    'tuna':         {'protein': 30.0, 'fat': 1.0,  'carbs': 0.0,  'calories': 128,  'unit': 'g',     'default_qty': 100},
    'potato':       {'protein': 2.0,  'fat': 0.1,  'carbs': 17.0, 'calories': 77,   'unit': 'g',     'default_qty': 150},
    'broccoli':     {'protein': 2.8,  'fat': 0.4,  'carbs': 7.0,  'calories': 34,   'unit': 'g',     'default_qty': 100},
    'cheese':       {'protein': 25.0, 'fat': 33.0, 'carbs': 1.3,  'calories': 402,  'unit': 'g',     'default_qty': 30},
    'butter':       {'protein': 0.9,  'fat': 81.0, 'carbs': 0.1,  'calories': 717,  'unit': 'g',     'default_qty': 10},
    'olive oil':    {'protein': 0.0,  'fat': 100,  'carbs': 0.0,  'calories': 884,  'unit': 'ml',    'default_qty': 10},
    'coffee':       {'protein': 0.3,  'fat': 0.0,  'carbs': 0.0,  'calories': 2,    'unit': 'ml',    'default_qty': 240},
    'orange juice': {'protein': 0.7,  'fat': 0.2,  'carbs': 10.0, 'calories': 45,   'unit': 'ml',    'default_qty': 200},
    'toast':        {'protein': 9.0,  'fat': 3.2,  'carbs': 49.0, 'calories': 265,  'unit': 'slice', 'default_qty': 2},
    'beef':         {'protein': 26.0, 'fat': 15.0, 'carbs': 0.0,  'calories': 250,  'unit': 'g',     'default_qty': 150},
    'pork':         {'protein': 27.0, 'fat': 14.0, 'carbs': 0.0,  'calories': 242,  'unit': 'g',     'default_qty': 150},
    'turkey':       {'protein': 29.0, 'fat': 5.0,  'carbs': 0.0,  'calories': 165,  'unit': 'g',     'default_qty': 150},
    'shrimp':       {'protein': 24.0, 'fat': 0.9,  'carbs': 0.2,  'calories': 99,   'unit': 'g',     'default_qty': 100},
    'lentil':       {'protein': 9.0,  'fat': 0.4,  'carbs': 20.0, 'calories': 116,  'unit': 'g',     'default_qty': 150},
    'lentils':      {'protein': 9.0,  'fat': 0.4,  'carbs': 20.0, 'calories': 116,  'unit': 'g',     'default_qty': 150},
    'almond':       {'protein': 21.0, 'fat': 50.0, 'carbs': 22.0, 'calories': 579,  'unit': 'g',     'default_qty': 30},
    'almonds':      {'protein': 21.0, 'fat': 50.0, 'carbs': 22.0, 'calories': 579,  'unit': 'g',     'default_qty': 30},
}

_MEAL_KEYWORDS = {
    'breakfast': 'Breakfast',
    'lunch':     'Lunch',
    'dinner':    'Dinner',
    'supper':    'Dinner',
    'snack':     'Snack',
    'brunch':    'Breakfast',
}

_UNIT_MAP = {
    'gram': 'g', 'grams': 'g', 'g': 'g',
    'ml': 'ml', 'millilitre': 'ml', 'milliliter': 'ml',
    'piece': 'piece', 'pieces': 'piece',
    'slice': 'slice', 'slices': 'slice',
    'cup': 'cup', 'cups': 'cup',
    'tbsp': 'tbsp', 'tablespoon': 'tbsp', 'tablespoons': 'tbsp',
    'tsp': 'tsp', 'teaspoon': 'tsp', 'teaspoons': 'tsp',
    'serving': 'serving', 'servings': 'serving',
    'glass': 'glass',
}


def _scale(base_per_100g: float, quantity: float, unit: str, food_default_unit: str) -> float:
    """Scale a per-100g value to the given quantity+unit."""
    if unit in ('g', 'ml'):
        return round(base_per_100g * quantity / 100, 1)
    # for piece/slice/serving use the food's default qty as the serving weight
    return round(base_per_100g * quantity / 100 * 100, 1)  # treat 1 piece ≈ 100g if unknown


def parse(text: str) -> dict:
    """
    Parse a natural-language food entry string.
    Returns a dict matching the chat JSON schema.
    """
    lower = text.lower()

    # Detect meal
    meal = 'Snack'
    for kw, label in _MEAL_KEYWORDS.items():
        if kw in lower:
            meal = label
            break

    # Try to match: "I had/ate/had N unit of FOOD"
    # Pattern examples: "2 eggs", "150g chicken", "a bowl of rice", "had 50 grams of oats"
    qty_unit_food = re.search(
        r'(\d+\.?\d*)\s*'
        r'(grams?|g\b|ml\b|millilitres?|milliliters?|pieces?|slices?|cups?|tbsps?|tsps?|tablespoons?|teaspoons?|servings?|glasses?)?\s*'
        r'(?:of\s+)?([a-z ]{2,30})',
        lower
    )

    matched_food = None
    quantity = None
    unit = 'serving'

    if qty_unit_food:
        quantity = float(qty_unit_food.group(1))
        raw_unit = (qty_unit_food.group(2) or '').strip()
        unit = _UNIT_MAP.get(raw_unit, 'serving') if raw_unit else 'serving'
        candidate = qty_unit_food.group(3).strip()
        # Try to match candidate against food DB
        for food_key in _FOOD_DB:
            if food_key in candidate:
                matched_food = food_key
                break

    # If no qty match, scan the whole text for a food name
    if not matched_food:
        for food_key in sorted(_FOOD_DB.keys(), key=len, reverse=True):
            if food_key in lower:
                matched_food = food_key
                break

    if not matched_food:
        return {
            'action': 'clarify',
            'message': "I couldn't identify the food. Could you be more specific? e.g. \"I had 150g chicken for lunch\"."
        }

    food = _FOOD_DB[matched_food]
    if quantity is None:
        quantity = food['default_qty']
        unit = food['unit']

    # Scale macros from per-100g base
    if unit in ('g', 'ml'):
        factor = quantity / 100
    else:
        # Approximate: treat default_qty as grams for 1 unit
        factor = (quantity * food['default_qty']) / 100

    return {
        'action': 'add_food',
        'name': matched_food.title(),
        'quantity': quantity,
        'unit': unit,
        'calories': round(food['calories'] * factor, 1),
        'protein_g': round(food['protein'] * factor, 1),
        'carbs_g': round(food['carbs'] * factor, 1),
        'fat_g': round(food['fat'] * factor, 1),
        'meal': meal,
        'note': 'Estimated by built-in database (no AI key configured)',
    }
