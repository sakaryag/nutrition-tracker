"""routes/game.py — /api/game blueprint: score, leaderboard, badges, stats."""
import json
from datetime import datetime, date, timedelta

from flask import Blueprint, jsonify, request, current_app, session

from models import db
from models.user import User
from models.food_entry import FoodEntry
from models.daily_target import DailyTarget
from models.water_log import WaterLog
from models.daily_note import DailyNote
from models.user_badge import UserBadge
from routes.auth import current_user_id

game_bp = Blueprint('game', __name__, url_prefix='/api/game')

# ---------------------------------------------------------------------------
# Badge catalog
# ---------------------------------------------------------------------------
BADGE_CATALOG = {
    'streak_7': {
        'badge_name': '7-Day Streak',
        'description': 'Logged food every day for 7 days in a row.',
        'icon_class': 'badge-streak',
    },
    'perfect_week': {
        'badge_name': 'Perfect Week',
        'description': 'Hit all macro targets every day in a calendar week.',
        'icon_class': 'badge-perfect-week',
    },
    'protein_king': {
        'badge_name': 'Protein King',
        'description': 'Hit the protein target for 5 consecutive days.',
        'icon_class': 'badge-protein',
    },
    'hydration_hero': {
        'badge_name': 'Hydration Hero',
        'description': 'Logged water and hit the water goal for 3 consecutive days.',
        'icon_class': 'badge-water',
    },
    'early_bird': {
        'badge_name': 'Early Bird',
        'description': 'Logged breakfast before 8 am for 3 days in a row.',
        'icon_class': 'badge-early-bird',
    },
    'consistent': {
        'badge_name': 'Consistent',
        'description': 'Logged food for 30 days total.',
        'icon_class': 'badge-consistent',
    },
}


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------
@game_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_active_target(user_id, for_date=None):
    """Return the DailyTarget effective on for_date, or None."""
    if for_date is None:
        for_date = date.today()
    return (
        DailyTarget.query
        .filter(DailyTarget.user_id == user_id, DailyTarget.effective_from <= for_date)
        .order_by(DailyTarget.effective_from.desc())
        .first()
    )


def _compute_score(user_id, for_date):
    """Return (score_int, breakdown_dict, totals_dict, targets_dict)."""
    entries = FoodEntry.query.filter_by(user_id=user_id, entry_date=for_date).all()
    if not entries:
        return 0, {}, {}, {}

    totals = {
        'protein': round(sum(e.protein for e in entries), 1),
        'fat': round(sum(e.fat for e in entries), 1),
        'carbs': round(sum(e.carbs for e in entries), 1),
        'calories': round(sum(e.calories for e in entries), 1),
    }

    target = _get_active_target(user_id, for_date)
    if not target:
        return 0, {}, totals, {}

    targets_dict = {
        'protein': target.protein,
        'fat': target.fat,
        'carbs': target.carbs,
        'calories': target.calories,
        'water_goal_ml': target.water_goal_ml,
    }

    def macro_pts(actual, goal):
        if goal <= 0:
            return 0
        pct = actual / goal
        if 0.90 <= pct <= 1.10:
            return 25
        if (0.75 <= pct < 0.90) or (1.10 < pct <= 1.25):
            return 15
        return 0

    protein_pts = macro_pts(totals['protein'], target.protein)
    fat_pts = macro_pts(totals['fat'], target.fat)
    carbs_pts = macro_pts(totals['carbs'], target.carbs)
    calories_pts = macro_pts(totals['calories'], target.calories)

    # Water bonus
    water_bonus = 0
    if target.water_goal_ml and target.water_goal_ml > 0:
        water_total = db.session.query(
            db.func.coalesce(db.func.sum(WaterLog.amount_ml), 0)
        ).filter_by(user_id=user_id, log_date=for_date).scalar() or 0
        if water_total >= target.water_goal_ml:
            water_bonus = 5

    # Note bonus
    note_bonus = 0
    note = DailyNote.query.filter_by(user_id=user_id, note_date=for_date).first()
    if note and note.content and note.content.strip():
        note_bonus = 3

    score = min(100, protein_pts + fat_pts + carbs_pts + calories_pts + water_bonus + note_bonus)

    breakdown = {
        'protein_pts': protein_pts,
        'fat_pts': fat_pts,
        'carbs_pts': carbs_pts,
        'calories_pts': calories_pts,
        'water_bonus': water_bonus,
        'note_bonus': note_bonus,
    }
    return score, breakdown, totals, targets_dict


def _daily_score_value(user_id, for_date):
    """Lightweight: return just the integer score."""
    score, _, _, _ = _compute_score(user_id, for_date)
    return score


def _iso_week_monday(iso_week_str=None):
    """Return the Monday date of the given ISO week string (YYYY-WNN) or current week."""
    if iso_week_str:
        try:
            year, wk = iso_week_str.split('-W')
            return date.fromisocalendar(int(year), int(wk), 1)
        except Exception:
            pass
    today = date.today()
    return today - timedelta(days=today.weekday())


def _weekly_score_and_daily(user_id, monday):
    """Return (total_score, [score_mon, ..., score_sun])."""
    daily = []
    for i in range(7):
        d = monday + timedelta(days=i)
        daily.append(_daily_score_value(user_id, d))
    return sum(daily), daily


# ---------------------------------------------------------------------------
# Badge evaluation
# ---------------------------------------------------------------------------

def _award_badge(user_id, badge_key, meta=None):
    """Award badge if not already earned. Uses INSERT OR IGNORE equivalent."""
    existing = UserBadge.query.filter_by(user_id=user_id, badge_key=badge_key).first()
    if existing:
        return
    ub = UserBadge(
        user_id=user_id,
        badge_key=badge_key,
        earned_at=datetime.utcnow(),
        badge_meta=json.dumps(meta) if meta else None,
    )
    db.session.add(ub)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def _evaluate_badges(user_id):
    """Evaluate and award all applicable badges for user_id."""
    today = date.today()

    # --- streak_7: 7 consecutive days with at least one food entry ---
    streak = 0
    for i in range(7):
        d = today - timedelta(days=i)
        count = FoodEntry.query.filter_by(user_id=user_id, entry_date=d).count()
        if count > 0:
            streak += 1
        else:
            break
    if streak >= 7:
        _award_badge(user_id, 'streak_7', {'streak_length': streak})

    # --- consistent: 30 total days logged ---
    distinct_days = (
        db.session.query(db.func.count(db.func.distinct(FoodEntry.entry_date)))
        .filter(FoodEntry.user_id == user_id)
        .scalar() or 0
    )
    if distinct_days >= 30:
        _award_badge(user_id, 'consistent', {'total_days': distinct_days})

    # --- protein_king: hit protein target 5 consecutive days ---
    protein_streak = 0
    for i in range(5):
        d = today - timedelta(days=i)
        target = _get_active_target(user_id, d)
        if not target or target.protein <= 0:
            break
        total_protein = db.session.query(
            db.func.coalesce(db.func.sum(FoodEntry.protein), 0)
        ).filter_by(user_id=user_id, entry_date=d).scalar() or 0
        pct = total_protein / target.protein
        if 0.90 <= pct <= 1.10:
            protein_streak += 1
        else:
            break
    if protein_streak >= 5:
        _award_badge(user_id, 'protein_king', {'consecutive_days': protein_streak})

    # --- hydration_hero: hit water goal 3 consecutive days ---
    water_streak = 0
    for i in range(3):
        d = today - timedelta(days=i)
        target = _get_active_target(user_id, d)
        if not target or not target.water_goal_ml or target.water_goal_ml <= 0:
            break
        water_total = db.session.query(
            db.func.coalesce(db.func.sum(WaterLog.amount_ml), 0)
        ).filter_by(user_id=user_id, log_date=d).scalar() or 0
        if water_total >= target.water_goal_ml:
            water_streak += 1
        else:
            break
    if water_streak >= 3:
        _award_badge(user_id, 'hydration_hero', {'consecutive_days': water_streak})

    # --- early_bird: logged breakfast before 08:00 for 3 consecutive days ---
    import datetime as dt_mod
    early_count = 0
    for i in range(3):
        d = today - timedelta(days=i)
        earliest = (
            db.session.query(db.func.min(FoodEntry.entry_time))
            .filter(
                FoodEntry.user_id == user_id,
                FoodEntry.entry_date == d,
                FoodEntry.meal_type == 'Breakfast',
            )
            .scalar()
        )
        if earliest and earliest < dt_mod.time(8, 0, 0):
            early_count += 1
        else:
            break
    if early_count >= 3:
        _award_badge(user_id, 'early_bird', {'consecutive_days': early_count})

    # --- perfect_week: hit all macros every day of the current week ---
    monday = _iso_week_monday()
    week_str = monday.strftime('%G-W%V')
    perfect = True
    for i in range(7):
        d = monday + timedelta(days=i)
        if d > today:
            break
        score, breakdown, _, _ = _compute_score(user_id, d)
        if not breakdown:
            perfect = False
            break
        if not (breakdown.get('protein_pts', 0) == 25
                and breakdown.get('fat_pts', 0) == 25
                and breakdown.get('carbs_pts', 0) == 25
                and breakdown.get('calories_pts', 0) == 25):
            perfect = False
            break
    if perfect:
        _award_badge(user_id, 'perfect_week', {'week': week_str})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@game_bp.get('/score')
def daily_score():
    uid = current_user_id()
    date_str = request.args.get('date')
    if date_str:
        try:
            for_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400
    else:
        for_date = date.today()

    score, breakdown, totals, targets = _compute_score(uid, for_date)
    return jsonify({
        'date': for_date.isoformat(),
        'score': score,
        'breakdown': breakdown,
        'totals': totals,
        'targets': targets,
    })


@game_bp.get('/leaderboard')
def leaderboard():
    from routes.friends import _friend_ids
    uid = current_user_id()
    week_str = request.args.get('week')
    monday = _iso_week_monday(week_str)
    iso_label = monday.strftime('%G-W%V')

    # Collect user set: self + accepted friends
    participant_ids = list(_friend_ids(uid)) + [uid]

    # Evaluate badges for all participants
    for pid in participant_ids:
        try:
            _evaluate_badges(pid)
        except Exception:
            pass

    scores = []
    for pid in participant_ids:
        user = db.session.get(User, pid)
        if not user:
            continue
        weekly, daily = _weekly_score_and_daily(pid, monday)
        badges = [b.badge_key for b in UserBadge.query.filter_by(user_id=pid).all()]
        scores.append({
            'user_id': pid,
            'username': user.username,
            'weekly_score': weekly,
            'daily_scores': daily,
            'badges': badges,
            'is_me': pid == uid,
        })

    scores.sort(key=lambda x: x['weekly_score'], reverse=True)

    my_rank = next((i + 1 for i, s in enumerate(scores) if s['is_me']), None)

    return jsonify({
        'week': iso_label,
        'my_rank': my_rank,
        'total_participants': len(scores),
        'scores': scores,
    })


@game_bp.get('/badges')
def my_badges():
    uid = current_user_id()
    _evaluate_badges(uid)
    rows = UserBadge.query.filter_by(user_id=uid).order_by(UserBadge.earned_at).all()
    result = []
    for row in rows:
        catalog = BADGE_CATALOG.get(row.badge_key, {})
        result.append({
            'badge_key': row.badge_key,
            'badge_name': catalog.get('badge_name', row.badge_key),
            'description': catalog.get('description', ''),
            'icon_class': catalog.get('icon_class', ''),
            'earned_at': row.earned_at.isoformat() if row.earned_at else None,
            'badge_meta': row.badge_meta,
        })
    return jsonify(result)


@game_bp.get('/stats')
def my_stats():
    uid = current_user_id()
    today = date.today()

    # Current streak
    streak = 0
    d = today
    while True:
        count = FoodEntry.query.filter_by(user_id=uid, entry_date=d).count()
        if count > 0:
            streak += 1
            d -= timedelta(days=1)
        else:
            break

    # Total points (sum across all days with entries)
    all_dates = (
        db.session.query(db.func.distinct(FoodEntry.entry_date))
        .filter(FoodEntry.user_id == uid)
        .all()
    )
    total_points = 0
    best_week_score = 0
    week_scores = {}

    for (entry_date,) in all_dates:
        score = _daily_score_value(uid, entry_date)
        total_points += score
        # Track by ISO week
        iso = entry_date.isocalendar()
        wk = f'{iso[0]}-W{iso[1]:02d}'
        week_scores[wk] = week_scores.get(wk, 0) + score

    if week_scores:
        best_week = max(week_scores, key=lambda k: week_scores[k])
        best_week_score = week_scores[best_week]
    else:
        best_week = None

    return jsonify({
        'current_streak': streak,
        'best_week_score': best_week_score,
        'best_week': best_week,
        'total_points': total_points,
        'total_days_logged': len(all_dates),
    })