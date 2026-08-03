from flask import Blueprint, jsonify, request, current_app, session
from datetime import date, timedelta
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


@summary_bp.route('/stats', methods=['GET'])
def stats_summary():
    """GET /api/summary/stats?start=YYYY-MM-DD&end=YYYY-MM-DD

    Returns aggregated statistics for a date range including averages,
    compliance percentages, streaks, and per-day detail.
    """
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    if not start_str or not end_str:
        return jsonify({'error': 'start and end query params are required'}), 400

    try:
        start_date = date.fromisoformat(start_str)
        end_date = date.fromisoformat(end_str)
    except ValueError:
        return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400

    if start_date > end_date:
        return jsonify({'error': 'start must be on or before end'}), 400

    uid = current_user_id()

    # --- Fetch all entries in range grouped by date ---
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

    # Build lookup: date_str -> totals
    by_date = {}
    for row in rows:
        by_date[row.entry_date.isoformat()] = {
            'protein': round(row.protein, 2),
            'fat': round(row.fat, 2),
            'carbs': round(row.carbs, 2),
            'calories': round(row.calories, 2),
        }

    # --- Build daily list covering every calendar day in range ---
    total_days = (end_date - start_date).days + 1
    daily = []
    d = start_date
    while d <= end_date:
        ds = d.isoformat()
        target = _get_target(d, uid)
        totals = by_date.get(ds, {'protein': 0.0, 'fat': 0.0, 'carbs': 0.0, 'calories': 0.0})
        daily.append({
            'date': ds,
            'protein': totals['protein'],
            'fat': totals['fat'],
            'carbs': totals['carbs'],
            'calories': totals['calories'],
            'target_protein': target['protein'],
            'target_fat': target['fat'],
            'target_carbs': target['carbs'],
            'target_calories': target['calories'],
        })
        d += timedelta(days=1)

    # --- Days logged ---
    days_logged = len(by_date)

    # --- Averages (only over logged days to avoid pulling down averages by empty days) ---
    if days_logged > 0:
        avg_protein  = round(sum(v['protein']  for v in by_date.values()) / days_logged, 1)
        avg_fat      = round(sum(v['fat']      for v in by_date.values()) / days_logged, 1)
        avg_carbs    = round(sum(v['carbs']    for v in by_date.values()) / days_logged, 1)
        avg_calories = round(sum(v['calories'] for v in by_date.values()) / days_logged, 1)
    else:
        avg_protein = avg_fat = avg_carbs = avg_calories = 0.0

    # --- Compliance: % of logged days where macro >= 90% of target ---
    COMPLIANCE_THRESHOLD = 0.90
    compliance_hits = {'protein': 0, 'fat': 0, 'carbs': 0, 'calories': 0}
    for day in daily:
        if day['date'] not in by_date:
            continue  # un-logged days don't count toward compliance
        for macro in ('protein', 'fat', 'carbs', 'calories'):
            target_val = day[f'target_{macro}']
            if target_val > 0 and day[macro] >= target_val * COMPLIANCE_THRESHOLD:
                compliance_hits[macro] += 1

    def _pct(hits):
        return round((hits / days_logged * 100)) if days_logged > 0 else 0

    compliance = {
        'protein_pct':  _pct(compliance_hits['protein']),
        'fat_pct':      _pct(compliance_hits['fat']),
        'carbs_pct':    _pct(compliance_hits['carbs']),
        'calories_pct': _pct(compliance_hits['calories']),
    }

    # --- Streak calculation: consecutive days going backward from today with >= 1 entry ---
    # Fetch ALL dated entries for this user (not just the query range) for accurate streaks
    all_q = db.session.query(FoodEntry.entry_date).distinct()
    if uid is not None:
        all_q = all_q.filter(FoodEntry.user_id == uid)
    all_logged = set(r.entry_date for r in all_q.all())

    today = date.today()
    current_streak = 0
    check = today
    while check in all_logged:
        current_streak += 1
        check -= timedelta(days=1)
    # If today has no entry, also check if yesterday started a streak
    if current_streak == 0:
        check = today - timedelta(days=1)
        while check in all_logged:
            current_streak += 1
            check -= timedelta(days=1)

    # Longest streak across all history
    longest_streak = 0
    if all_logged:
        sorted_days = sorted(all_logged)
        run = 1
        for i in range(1, len(sorted_days)):
            if (sorted_days[i] - sorted_days[i - 1]).days == 1:
                run += 1
                longest_streak = max(longest_streak, run)
            else:
                run = 1
        longest_streak = max(longest_streak, run)

    return jsonify({
        'avg_protein':  avg_protein,
        'avg_fat':      avg_fat,
        'avg_carbs':    avg_carbs,
        'avg_calories': avg_calories,
        'days_logged':  days_logged,
        'total_days_in_range': total_days,
        'compliance':   compliance,
        'current_streak':  current_streak,
        'longest_streak':  longest_streak,
        'daily': daily,
    })