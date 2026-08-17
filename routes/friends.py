"""routes/friends.py — /api/friends blueprint (friend requests & management)."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, current_app, session

from models import db
from models.user import User
from models.friend_connection import FriendConnection
from models.user_badge import UserBadge
from routes.auth import current_user_id

friends_bp = Blueprint('friends', __name__, url_prefix='/api/friends')


def _auth_guard():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    return None


@friends_bp.before_request
def check_auth():
    return _auth_guard()


def _get_connection_between(a_id, b_id):
    """Return the FriendConnection row between two users in either direction, or None."""
    return FriendConnection.query.filter(
        db.or_(
            db.and_(
                FriendConnection.requester_id == a_id,
                FriendConnection.recipient_id == b_id,
            ),
            db.and_(
                FriendConnection.requester_id == b_id,
                FriendConnection.recipient_id == a_id,
            ),
        )
    ).first()


def _weekly_score(user_id, iso_week_str=None):
    """Return the sum of daily scores for user_id across the current ISO week Mon-Sun."""
    from routes.game import _daily_score_value
    from datetime import date, timedelta
    import datetime as dt_mod

    if iso_week_str:
        # parse YYYY-WNN
        try:
            year, wk = iso_week_str.split('-W')
            ref = dt_mod.date.fromisocalendar(int(year), int(wk), 1)
        except Exception:
            ref = dt_mod.date.today()
    else:
        today = dt_mod.date.today()
        ref = today - timedelta(days=today.weekday())  # Monday

    total = 0
    for i in range(7):
        d = ref + timedelta(days=i)
        total += _daily_score_value(user_id, d)
    return total


def _friend_ids(user_id):
    """Return set of user_ids that are accepted friends of user_id."""
    rows = FriendConnection.query.filter(
        db.or_(
            FriendConnection.requester_id == user_id,
            FriendConnection.recipient_id == user_id,
        ),
        FriendConnection.status == 'accepted',
    ).all()
    ids = set()
    for row in rows:
        if row.requester_id == user_id:
            ids.add(row.recipient_id)
        else:
            ids.add(row.requester_id)
    return ids


@friends_bp.get('')
def list_friends():
    uid = current_user_id()
    friend_ids = _friend_ids(uid)
    result = []
    for fid in friend_ids:
        user = db.session.get(User, fid)
        if not user:
            continue
        badges = [b.badge_key for b in UserBadge.query.filter_by(user_id=fid).all()]
        result.append({
            'user_id': fid,
            'username': user.username,
            'weekly_score': _weekly_score(fid),
            'badges': badges,
        })
    result.sort(key=lambda x: x['weekly_score'], reverse=True)
    return jsonify(result)


@friends_bp.post('/request')
def send_request():
    uid = current_user_id()
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    if not username:
        return jsonify({'error': 'username is required'}), 400

    target = User.query.filter_by(username=username).first()
    if not target:
        return jsonify({'error': 'User not found'}), 404
    if target.id == uid:
        return jsonify({'error': 'Cannot send a friend request to yourself'}), 400

    existing = _get_connection_between(uid, target.id)
    if existing:
        if existing.status == 'blocked':
            return jsonify({'error': 'Cannot send request — user is blocked'}), 409
        return jsonify({'error': 'Connection already exists', 'status': existing.status}), 409

    conn = FriendConnection(
        requester_id=uid,
        recipient_id=target.id,
        status='pending',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.session.add(conn)
    db.session.commit()
    return jsonify({'connection_id': conn.id, 'status': 'pending'}), 201


@friends_bp.get('/requests')
def incoming_requests():
    uid = current_user_id()
    rows = FriendConnection.query.filter_by(
        recipient_id=uid, status='pending'
    ).order_by(FriendConnection.created_at.desc()).all()
    result = []
    for row in rows:
        requester = db.session.get(User, row.requester_id)
        result.append({
            'connection_id': row.id,
            'requester_id': row.requester_id,
            'requester_username': requester.username if requester else None,
            'sent_at': row.created_at.isoformat() if row.created_at else None,
        })
    return jsonify(result)


@friends_bp.put('/requests/<int:connection_id>/accept')
def accept_request(connection_id):
    uid = current_user_id()
    conn = db.session.get(FriendConnection, connection_id)
    if not conn:
        return jsonify({'error': 'Connection not found'}), 404
    if conn.recipient_id != uid:
        return jsonify({'error': 'Forbidden'}), 403
    if conn.status == 'accepted':
        return jsonify({'error': 'Already accepted'}), 409
    if conn.status != 'pending':
        return jsonify({'error': f'Cannot accept a request with status {conn.status}'}), 409
    conn.status = 'accepted'
    conn.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'status': 'accepted'})


@friends_bp.put('/requests/<int:connection_id>/decline')
def decline_request(connection_id):
    uid = current_user_id()
    conn = db.session.get(FriendConnection, connection_id)
    if not conn:
        return jsonify({'error': 'Connection not found'}), 404
    if conn.recipient_id != uid:
        return jsonify({'error': 'Forbidden'}), 403
    if conn.status not in ('pending', 'accepted'):
        return jsonify({'error': f'Cannot decline a request with status {conn.status}'}), 409
    conn.status = 'declined'
    conn.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'status': 'declined'})


@friends_bp.delete('/<int:friend_id>')
def remove_friend(friend_id):
    uid = current_user_id()
    data = request.get_json(silent=True) or {}
    block = bool(data.get('block', False))

    conn = _get_connection_between(uid, friend_id)
    if not conn:
        return jsonify({'error': 'Connection not found'}), 404

    if block:
        conn.status = 'blocked'
        conn.updated_at = datetime.now(timezone.utc)
        # Ensure current user is the requester for consistency
        if conn.recipient_id == uid:
            conn.requester_id, conn.recipient_id = uid, friend_id
        db.session.commit()
        return jsonify({'deleted': False, 'blocked': True})

    db.session.delete(conn)
    db.session.commit()
    return jsonify({'deleted': True})