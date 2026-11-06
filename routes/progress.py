import math
from datetime import date, datetime, timedelta
from flask import Blueprint, jsonify, request, current_app, session
from models import db
from models.weight_log import WeightLog, BodyGoal
from routes.auth import current_user_id

progress_bp = Blueprint('progress', __name__, url_prefix='/api/progress')

WEIGHT_MIN, WEIGHT_MAX = 20.0, 400.0
HEIGHT_MIN, HEIGHT_MAX = 80.0, 250.0
RANGE_DAYS = {'week': 7, 'month': 30}


@progress_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


def _owned(model, uid):
    # IS NULL for the auth-disabled profile so anonymous rows never mix with real users.
    col = model.user_id
    return model.query.filter(col.is_(None) if uid is None else col == uid)


def _number(value, lo, hi, field):
    if isinstance(value, bool) or value is None or value == '':
        raise ValueError(f'{field} is required')
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{field} must be a number')
    if not math.isfinite(num) or num < lo or num > hi:
        raise ValueError(f'{field} must be between {lo:g} and {hi:g}')
    return round(num, 1)


def bmi_for(weight_kg, height_cm):
    if not weight_kg or not height_cm:
        return None
    return round(weight_kg / ((height_cm / 100.0) ** 2), 1)


def bmi_category(bmi):
    if bmi is None:
        return None
    if bmi < 18.5:
        return 'underweight'
    if bmi < 25:
        return 'healthy'
    if bmi < 30:
        return 'overweight'
    return 'obese'


def progress_pct(start, current, goal):
    """Share of the start→goal distance covered; direction-agnostic (loss or gain)."""
    if start is None or current is None or goal is None:
        return None
    total = start - goal
    if abs(total) < 1e-9:
        return 100
    pct = (start - current) / total * 100
    return int(round(max(0.0, min(100.0, pct))))


def progress_status(pct):
    if pct is None:
        return None
    if pct >= 40:
        return 'good'
    if pct >= 15:
        return 'on_track'
    return 'keep_going'


@progress_bp.route('', methods=['GET'])
def get_progress():
    rng = request.args.get('range', 'month')
    if rng not in ('week', 'month', 'all'):
        return jsonify({'error': 'range must be week, month or all'}), 400

    uid = current_user_id()
    goal = _owned(BodyGoal, uid).first()
    base = _owned(WeightLog, uid)
    first = base.order_by(WeightLog.log_date.asc()).first()
    latest = base.order_by(WeightLog.log_date.desc()).first()

    q = _owned(WeightLog, uid)
    if rng in RANGE_DAYS:
        q = q.filter(WeightLog.log_date >= date.today() - timedelta(days=RANGE_DAYS[rng] - 1))
    logs = q.order_by(WeightLog.log_date.asc()).all()

    goal_w = goal.goal_weight_kg if goal else None
    height = goal.height_cm if goal else None
    current = latest.weight_kg if latest else None
    start = first.weight_kg if first else None
    bmi = bmi_for(current, height)
    pct = progress_pct(start, current, goal_w)
    return jsonify({
        'goal_weight_kg': goal_w,
        'height_cm': height,
        'current_weight_kg': current,
        'start_weight_kg': start,
        'bmi': bmi,
        'bmi_category': bmi_category(bmi),
        'progress_pct': pct,
        'progress_status': progress_status(pct),
        'range': rng,
        'logs': [log.to_dict() for log in logs],
    })


@progress_bp.route('/weight', methods=['POST'])
def log_weight():
    data = request.get_json(silent=True) or {}
    try:
        weight = _number(data.get('weight_kg'), WEIGHT_MIN, WEIGHT_MAX, 'weight_kg')
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    date_str = data.get('date')
    if date_str:
        try:
            log_date = datetime.strptime(str(date_str), '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400
        if log_date > date.today():
            return jsonify({'error': 'date cannot be in the future'}), 400
    else:
        log_date = date.today()

    uid = current_user_id()
    log = _owned(WeightLog, uid).filter(WeightLog.log_date == log_date).first()
    created = log is None
    if created:
        log = WeightLog(user_id=uid, log_date=log_date, weight_kg=weight)
        db.session.add(log)
    else:
        log.weight_kg = weight
    db.session.commit()
    return jsonify(log.to_dict()), 201 if created else 200


@progress_bp.route('/weight/<int:log_id>', methods=['DELETE'])
def delete_weight(log_id):
    log = _owned(WeightLog, current_user_id()).filter(WeightLog.id == log_id).first()
    if log is None:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(log)
    db.session.commit()
    return jsonify({'deleted': log_id})


@progress_bp.route('/goal', methods=['PUT'])
def update_goal():
    data = request.get_json(silent=True) or {}
    if 'goal_weight_kg' not in data and 'height_cm' not in data:
        return jsonify({'error': 'Provide goal_weight_kg and/or height_cm'}), 400

    updates = {}
    try:
        if 'goal_weight_kg' in data:
            v = data['goal_weight_kg']
            updates['goal_weight_kg'] = None if v is None else _number(v, WEIGHT_MIN, WEIGHT_MAX, 'goal_weight_kg')
        if 'height_cm' in data:
            v = data['height_cm']
            updates['height_cm'] = None if v is None else _number(v, HEIGHT_MIN, HEIGHT_MAX, 'height_cm')
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    uid = current_user_id()
    goal = _owned(BodyGoal, uid).first()
    if goal is None:
        goal = BodyGoal(user_id=uid)
        db.session.add(goal)
    for k, v in updates.items():
        setattr(goal, k, v)
    db.session.commit()
    return jsonify({'goal_weight_kg': goal.goal_weight_kg, 'height_cm': goal.height_cm})
