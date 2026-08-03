from flask import Blueprint, jsonify, request, current_app, session
from datetime import date, datetime
from models import db
from models.water_log import WaterLog
from routes.auth import current_user_id

water_bp = Blueprint('water', __name__, url_prefix='/api/water')

DAILY_GOAL_ML = 2000


@water_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


@water_bp.route('', methods=['GET'])
def get_water():
    """GET /api/water?date=YYYY-MM-DD
    Returns {total_ml, goal_ml, logs: [{id, amount_ml, logged_at}]}
    """
    date_str = request.args.get('date')
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400
    else:
        target_date = date.today()

    uid = current_user_id()
    q = WaterLog.query.filter_by(log_date=target_date)
    if uid is not None:
        q = q.filter_by(user_id=uid)
    logs = q.order_by(WaterLog.logged_at).all()
    total_ml = sum(log.amount_ml for log in logs)
    return jsonify({
        'total_ml': total_ml,
        'goal_ml': DAILY_GOAL_ML,
        'logs': [{'id': log.id, 'amount_ml': log.amount_ml, 'logged_at': log.logged_at.isoformat() if log.logged_at else None} for log in logs],
    })


@water_bp.route('', methods=['POST'])
def add_water():
    """POST /api/water  body: {date: 'YYYY-MM-DD', amount_ml: float}"""
    data = request.get_json(silent=True) or {}
    date_str = data.get('date')
    amount_ml = data.get('amount_ml')

    if not amount_ml or float(amount_ml) <= 0:
        return jsonify({'error': 'amount_ml must be a positive number'}), 400

    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400
    else:
        target_date = date.today()

    uid = current_user_id()
    log = WaterLog(
        user_id=uid,
        log_date=target_date,
        amount_ml=float(amount_ml),
        logged_at=datetime.utcnow(),
    )
    db.session.add(log)
    db.session.commit()
    return jsonify(log.to_dict()), 201


@water_bp.route('/<int:log_id>', methods=['DELETE'])
def delete_water(log_id):
    """DELETE /api/water/<id>"""
    uid = current_user_id()
    q = WaterLog.query.filter_by(id=log_id)
    if uid is not None:
        q = q.filter_by(user_id=uid)
    log = q.first_or_404()
    db.session.delete(log)
    db.session.commit()
    return jsonify({'deleted': True})
