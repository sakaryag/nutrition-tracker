"""routes/social.py — /api/social blueprint: feed, visibility, badges, leaderboard, score."""
from datetime import datetime, date, timedelta

from flask import Blueprint, jsonify, request, current_app, session

from models import db
from models.user import User
from models.food_entry import FoodEntry
from models.daily_target import DailyTarget
from models.feed_visibility import FeedVisibility
from models.user_badge import UserBadge
from routes.auth import current_user_id
from routes.friends import _friend_ids
from routes.game import (
    _daily_score_value, _compute_score, _evaluate_badges,
    _iso_week_monday, _weekly_score_and_daily, BADGE_CATALOG
)

social_bp = Blueprint('social', __name__, url_prefix='/api/social')


@social_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


def _get_active_target_for(user_id, for_date=None):
    if for_date is None:
        for_date = date.today()
    return (
        DailyTarget.query
        .filter(DailyTarget.user_id == user_id, DailyTarget.effective_from <= for_date)
        .order_by(DailyTarget.effective_from.desc())
        .first()
    )


# ---------------------------------------------------------------------------
# Leaderboard (also available under /api/game/leaderboard — this is the social URL)
# ---------------------------------------------------------------------------

@social_bp.get('/leaderboard')
def leaderboard():
    uid = current_user_id()
    week_str = request.args.get('week')
    monday = _iso_week_monday(week_str)
    iso_label = monday.strftime('%G-W%V')

    participant_ids = list(_friend_ids(uid)) + [uid]

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


# ---------------------------------------------------------------------------
# Daily score (mirrors /api/game/score — available under /api/social too)
# ---------------------------------------------------------------------------

@social_bp.get('/score')
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

    if not totals:
        return jsonify({'date': for_date.isoformat(), 'total': 0})

    target = _get_active_target_for(uid, for_date)

    def pct(actual, goal):
        if goal and goal > 0:
            return round(actual / goal * 100, 1)
        return None

    return jsonify({
        'date': for_date.isoformat(),
        'base': score - breakdown.get('water_bonus', 0) - breakdown.get('note_bonus', 0),
        'bonus': breakdown.get('water_bonus', 0) + breakdown.get('note_bonus', 0),
        'total': score,
        'breakdown': {
            'protein_hit': breakdown.get('protein_pts', 0) == 25,
            'fat_hit': breakdown.get('fat_pts', 0) == 25,
            'carbs_hit': breakdown.get('carbs_pts', 0) == 25,
            'calories_hit': breakdown.get('calories_pts', 0) == 25,
            'protein_pct': pct(totals.get('protein', 0), target.protein if target else None),
            'fat_pct': pct(totals.get('fat', 0), target.fat if target else None),
            'carbs_pct': pct(totals.get('carbs', 0), target.carbs if target else None),
            'calories_pct': pct(totals.get('calories', 0), target.calories if target else None),
            'water_hit': breakdown.get('water_bonus', 0) > 0,
            'note_hit': breakdown.get('note_bonus', 0) > 0,
            'early_bird_hit': False,  # evaluated at badge level, not per-day API
        },
    })


# ---------------------------------------------------------------------------
# Friend feed
# ---------------------------------------------------------------------------

@social_bp.get('/feed')
def friend_feed():
    uid = current_user_id()
    today = date.today()
    friend_ids = _friend_ids(uid)

    result = []
    for fid in friend_ids:
        vis = FeedVisibility.query.filter_by(user_id=fid).first()
        if not vis or not vis.show_in_feed:
            continue

        friend = db.session.get(User, fid)
        if not friend:
            continue

        target = _get_active_target_for(fid, today)
        entries = FoodEntry.query.filter_by(user_id=fid, entry_date=today).all()

        totals = {
            'protein': sum(e.protein for e in entries),
            'fat': sum(e.fat for e in entries),
            'carbs': sum(e.carbs for e in entries),
            'calories': sum(e.calories for e in entries),
        }

        def pct(actual, goal):
            if goal and goal > 0:
                return round(actual / goal * 100, 1)
            return None

        p_pct = pct(totals['protein'], target.protein if target else None)
        f_pct = pct(totals['fat'], target.fat if target else None)
        c_pct = pct(totals['carbs'], target.carbs if target else None)
        cal_pct = pct(totals['calories'], target.calories if target else None)

        # big_win: highest macro above 90%
        macro_hits = {}
        if p_pct and p_pct >= 90:
            macro_hits['Protein'] = p_pct
        if f_pct and f_pct >= 90:
            macro_hits['Fat'] = f_pct
        if c_pct and c_pct >= 90:
            macro_hits['Carbs'] = c_pct
        if cal_pct and cal_pct >= 90:
            macro_hits['Calories'] = cal_pct
        big_win = max(macro_hits, key=macro_hits.get) if macro_hits else None

        # Badges earned today
        badges_today = [
            b.badge_key for b in UserBadge.query.filter_by(user_id=fid).all()
            if b.earned_at and b.earned_at.date() == today
        ]

        card = {
            'user_id': fid,
            'username': friend.username,
            'date': today.isoformat(),
            'big_win': big_win,
            'badges_today': badges_today,
        }

        if vis.show_calories:
            card['calories_consumed'] = round(totals['calories'], 1)
            card['calories_target'] = target.calories if target else None
            card['calories_pct'] = cal_pct
        else:
            card['calories_consumed'] = None
            card['calories_target'] = None
            card['calories_pct'] = None

        if vis.show_macros:
            card['protein_pct'] = p_pct
            card['fat_pct'] = f_pct
            card['carbs_pct'] = c_pct
        else:
            card['protein_pct'] = None
            card['fat_pct'] = None
            card['carbs_pct'] = None

        result.append(card)

    return jsonify(result)


# ---------------------------------------------------------------------------
# Feed visibility
# ---------------------------------------------------------------------------

@social_bp.get('/feed/visibility')
def get_visibility():
    uid = current_user_id()
    vis = FeedVisibility.query.filter_by(user_id=uid).first()
    if not vis:
        return jsonify({'show_in_feed': False, 'show_calories': True, 'show_macros': True})
    return jsonify(vis.to_dict())


@social_bp.put('/feed/visibility')
def update_visibility():
    uid = current_user_id()
    data = request.get_json(silent=True) or {}

    vis = FeedVisibility.query.filter_by(user_id=uid).first()
    if not vis:
        vis = FeedVisibility(
            user_id=uid,
            show_in_feed=False,
            show_calories=True,
            show_macros=True,
        )
        db.session.add(vis)

    if 'show_in_feed' in data:
        vis.show_in_feed = bool(data['show_in_feed'])
    if 'show_calories' in data:
        vis.show_calories = bool(data['show_calories'])
    if 'show_macros' in data:
        vis.show_macros = bool(data['show_macros'])
    vis.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify(vis.to_dict())


# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------

@social_bp.get('/badges')
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