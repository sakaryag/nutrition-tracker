from flask import Blueprint, jsonify, request, current_app, session
from datetime import date
from models import db
from models.daily_target import DailyTarget

targets_bp = Blueprint('targets', __name__, url_prefix='/api/targets')


@targets_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


@targets_bp.route('', methods=['GET'])
def get_target():
    """GET /api/targets"""
    today = date.today()
    target = (
        DailyTarget.query
        .filter(DailyTarget.effective_from <= today)
        .order_by(DailyTarget.effective_from.desc())
        .first()
    )
    if target:
        return jsonify(target.to_dict())
    return jsonify({
        'id': None,
        'protein': current_app.config.get('DEFAULT_PROTEIN_TARGET', 150),
        'fat': current_app.config.get('DEFAULT_FAT_TARGET', 65),
        'carbs': current_app.config.get('DEFAULT_CARBS_TARGET', 250),
        'calories': current_app.config.get('DEFAULT_CALORIES_TARGET', 2200),
        'effective_from': None,
    })


@targets_bp.route('', methods=['POST'])
def create_target():
    """POST /api/targets"""
    data = request.get_json(silent=True) or {}
    try:
        protein = float(data['protein'])
        fat = float(data['fat'])
        carbs = float(data['carbs'])
        calories = float(data['calories'])
    except (KeyError, TypeError, ValueError):
        return jsonify({'error': 'protein, fat, carbs, and calories are required numeric fields'}), 400

    target = DailyTarget(
        protein=protein,
        fat=fat,
        carbs=carbs,
        calories=calories,
        effective_from=date.today(),
    )
    db.session.add(target)
    db.session.commit()
    return jsonify(target.to_dict()), 201


# ---------------------------------------------------------------------------
# Macro preset definitions
# ---------------------------------------------------------------------------
_PRESETS: dict[str, dict[str, float]] = {
    'balanced':    {'protein_pct': 30.0, 'fat_pct': 30.0, 'carbs_pct': 40.0},
    'high_protein':{'protein_pct': 40.0, 'fat_pct': 25.0, 'carbs_pct': 35.0},
    'low_carb':    {'protein_pct': 35.0, 'fat_pct': 40.0, 'carbs_pct': 25.0},
    'keto':        {'protein_pct': 25.0, 'fat_pct': 65.0, 'carbs_pct': 10.0},
}

_ACTIVITY_MULTIPLIERS: dict[str, float] = {
    'sedentary':  1.2,
    'light':      1.375,
    'moderate':   1.55,
    'active':     1.725,
    'very_active':1.9,
}

_GOAL_MULTIPLIERS: dict[str, float] = {
    'maintain': 1.0,
    'cut':      0.8,
    'bulk':     1.15,
}


@targets_bp.route('/calculate', methods=['POST'])
def calculate_tdee():
    """POST /api/targets/calculate — Mifflin-St Jeor TDEE + macro split."""
    data = request.get_json(silent=True) or {}

    # --- validate required fields ---
    errors: list[str] = []

    gender = data.get('gender', '').lower()
    if gender not in ('male', 'female'):
        errors.append("gender must be 'male' or 'female'")

    try:
        age = float(data['age'])
        if age < 1:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        errors.append('age must be a positive number')
        age = 0.0

    try:
        weight_kg = float(data['weight_kg'])
        if weight_kg <= 0:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        errors.append('weight_kg must be a positive number')
        weight_kg = 0.0

    try:
        height_cm = float(data['height_cm'])
        if height_cm <= 0:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        errors.append('height_cm must be a positive number')
        height_cm = 0.0

    activity_level = data.get('activity_level', '')
    if activity_level not in _ACTIVITY_MULTIPLIERS:
        errors.append(f"activity_level must be one of: {', '.join(_ACTIVITY_MULTIPLIERS)}")

    goal = data.get('goal', '')
    if goal not in _GOAL_MULTIPLIERS:
        errors.append(f"goal must be one of: {', '.join(_GOAL_MULTIPLIERS)}")

    preset = data.get('preset', '')
    valid_presets = list(_PRESETS.keys()) + ['custom']
    if preset not in valid_presets:
        errors.append(f"preset must be one of: {', '.join(valid_presets)}")

    # validate custom split when preset == 'custom'
    split: dict[str, float] = {}
    if preset == 'custom':
        custom = data.get('custom_split') or {}
        try:
            p = float(custom['protein_pct'])
            f = float(custom['fat_pct'])
            c = float(custom['carbs_pct'])
            if abs(p + f + c - 100) > 0.5:
                errors.append('custom_split percentages must sum to 100')
            split = {'protein_pct': p, 'fat_pct': f, 'carbs_pct': c}
        except (KeyError, TypeError, ValueError):
            errors.append('custom_split must contain protein_pct, fat_pct, carbs_pct')
    elif preset in _PRESETS:
        split = _PRESETS[preset]

    if errors:
        return jsonify({'error': '; '.join(errors)}), 400

    # --- BMR (Mifflin-St Jeor) ---
    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    bmr += 5 if gender == 'male' else -161

    # --- TDEE & goal-adjusted calories ---
    tdee = bmr * _ACTIVITY_MULTIPLIERS[activity_level]
    calories = tdee * _GOAL_MULTIPLIERS[goal]

    # --- convert split percentages to grams ---
    protein_g = round((calories * split['protein_pct'] / 100) / 4)
    fat_g     = round((calories * split['fat_pct']     / 100) / 9)
    carbs_g   = round((calories * split['carbs_pct']   / 100) / 4)

    return jsonify({
        'bmr':     round(bmr),
        'tdee':    round(tdee),
        'calories':round(calories),
        'protein': protein_g,
        'fat':     fat_g,
        'carbs':   carbs_g,
        'preset':  preset,
        'split':   split,
        'goal':    goal,
    })