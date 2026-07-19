from flask import Blueprint, jsonify, request, current_app, session
from datetime import date
from models import db
from models.food_entry import FoodEntry
from models.daily_target import DailyTarget
from routes.auth import current_user_id
from sqlalchemy import func

summary_bp = Blueprint('summary', __name__, url_prefix='/api/summary')


@summary_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


def _get_target(target_date: date, uid) -> dict:
    q = DailyTarget.query.filter(DailyTarget.effective_from <= target_date)
    if uid is not None:
        q = q.filter(DailyTarget.user_id == uid)
    target = q.order_by(DailyTarget.effective_from.desc()).first()
    if target:
        return {
            'id': target.id,
            'protein': target.protein,
            'fat': target.fat,
            'carbs': target.carbs,
            'calories': target.calories,
            'effective_from': target.effective_from.isoformat(),
        }
    return {
        'id': None,
        'protein': current_app.config.get('DEFAULT_PROTEIN_TARGET', 150),
        'fat': current_app.config.get('DEFAULT_FAT_TARGET', 65),
        'carbs': current_app.config.get('DEFAULT_CARBS_TARGET', 250),
        'calories': current_app.config.get('DEFAULT_CALORIES_TARGET', 2200),
        'effective_from': None,
    }


def _totals_for_date(target_date: date, uid) -> dict:
    q = db.session.query(
        func.coalesce(func.sum(FoodEntry.protein), 0.0).label('protein'),
        func.coalesce(func.sum(FoodEntry.fat), 0.0).label('fat'),
        func.coalesce(func.sum(FoodEntry.carbs), 0.0).label('carbs'),
        func.coalesce(func.sum(FoodEntry.calories), 0.0).label('calories'),
    ).filter(FoodEntry.entry_date == target_date)
    if uid is not None:
        q = q.filter(FoodEntry.user_id == uid)
    row = q.one()
    return {
        'protein': round(row.protein, 2),
        'fat': round(row.fat, 2),
        'carbs': round(row.carbs, 2),
        'calories': round(row.calories, 2),
    }


@summary_bp.route('', methods=['GET'])
def daily_summary():
    """GET /api/summary?date=YYYY-MM-DD"""
    date_str = request.args.get('date')
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400
    else:
        target_date = date.today()

    uid = current_user_id()
    totals = _totals_for_date(target_date, uid)
    target = _get_target(target_date, uid)
    remaining = {
        'protein': round(target['protein'] - totals['protein'], 2),
        'fat': round(target['fat'] - totals['fat'], 2),
        'carbs': round(target['carbs'] - totals['carbs'], 2),
        'calories': round(target['calories'] - totals['calories'], 2),
    }
    return jsonify({
        'date': target_date.isoformat(),
        'totals': totals,
        'target': target,
        'remaining': remaining,
    })


@summary_bp.route('/range', methods=['GET'])
def range_summary():
    """GET /api/summary/range?start=YYYY-MM-DD&end=YYYY-MM-DD"""
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    if not start_str or not end_str:
        return jsonify({'error': 'start and end query params are required'}), 400

    try:
        start_date = date.fromisoformat(start_str)
        end_date = date.fromisoformat(end_str)
    except ValueError:
        return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400

    uid = current_user_id()
    q = db.session.query(
        FoodEntry.entry_date,
        func.coalesce(func.sum(FoodEntry.protein), 0.0).label('protein'),
        func.coalesce(func.sum(FoodEntry.fat), 0.0).label('fat'),
        func.coalesce(func.sum(FoodEntry.carbs), 0.0).label('carbs'),
        func.coalesce(func.sum(FoodEntry.calories), 0.0).label('calories'),
    ).filter(FoodEntry.entry_date >= start_date, FoodEntry.entry_date <= end_date)
    if uid is not None:
        q = q.filter(FoodEntry.user_id == uid)
    rows = q.group_by(FoodEntry.entry_date).order_by(FoodEntry.entry_date).all()
    return jsonify([
        {
            'date': row.entry_date.isoformat(),
            'protein': round(row.protein, 2),
            'fat': round(row.fat, 2),
            'carbs': round(row.carbs, 2),
            'calories': round(row.calories, 2),
        }
        for row in rows
    ])