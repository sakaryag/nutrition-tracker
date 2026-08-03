from datetime import datetime, date
from flask import Blueprint, jsonify, request, session, current_app
from models import db
from models.user import User
from models.food_entry import FoodEntry
from models.daily_target import DailyTarget
from models.user_plan_assignment import UserPlanAssignment
from routes.auth import current_user_id

dietitian_bp = Blueprint('dietitian', __name__, url_prefix='/api/dietitian')


@dietitian_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


def _require_dietitian():
    uid = current_user_id()
    if uid is None:
        return None, jsonify({'error': 'Authentication required'}), 401
    user = db.session.get(User, uid)
    if user is None or not user.is_admin:
        return None, jsonify({'error': 'Dietitian access required'}), 403
    return user, None, None


def _get_access(dietitian_id, client_id):
    row = db.session.execute(
        db.text('SELECT allowed FROM dietitian_access WHERE dietitian_id=:d AND client_id=:c'),
        {'d': dietitian_id, 'c': client_id}
    ).fetchone()
    return row and bool(row[0])


# ── Dietitian: list assigned clients ─────────────────────────────────────────

@dietitian_bp.route('/clients', methods=['GET'])
def list_clients():
    dietitian, err, code = _require_dietitian()
    if err:
        return err, code

    rows = db.session.execute(
        db.text('''
            SELECT u.id, u.username, u.created_at,
                   COALESCE(da.allowed, false) AS allowed
            FROM user_plan_assignment upa
            JOIN "user" u ON u.id = upa.user_id
            LEFT JOIN dietitian_access da ON da.dietitian_id = :did AND da.client_id = u.id
            WHERE upa.assigned_by = :did AND upa.is_active = true
            GROUP BY u.id, u.username, u.created_at, da.allowed
            ORDER BY u.username
        '''),
        {'did': dietitian.id}
    ).fetchall()

    result = []
    for r in rows:
        result.append({
            'user_id': r[0],
            'username': r[1],
            'member_since': r[2].isoformat() if r[2] else None,
            'access_granted': bool(r[3]),
        })
    return jsonify(result)


# ── Dietitian: view client data (read-only, requires consent) ────────────────

@dietitian_bp.route('/clients/<int:client_id>/data', methods=['GET'])
def client_data(client_id):
    dietitian, err, code = _require_dietitian()
    if err:
        return err, code

    # Verify this client is actually assigned to this dietitian
    assignment = UserPlanAssignment.query.filter_by(
        user_id=client_id, assigned_by=dietitian.id, is_active=True
    ).first()
    if not assignment:
        return jsonify({'error': 'Client not assigned to you'}), 403

    if not _get_access(dietitian.id, client_id):
        return jsonify({'error': 'Client has not granted access'}), 403

    # Log the visit
    db.session.execute(
        db.text('INSERT INTO dietitian_visit (dietitian_id, client_id, visited_at, seen) VALUES (:d, :c, :v, false)'),
        {'d': dietitian.id, 'c': client_id, 'v': datetime.utcnow()}
    )
    db.session.commit()

    # Fetch last 7 days of entries + today summary
    raw_date = request.args.get('date', date.today().isoformat())
    try:
        target_date = date.fromisoformat(raw_date)
    except ValueError:
        target_date = date.today()

    entries = FoodEntry.query.filter_by(
        user_id=client_id, date=target_date
    ).order_by(FoodEntry.id).all()

    target = DailyTarget.query.filter(
        DailyTarget.user_id == client_id,
        DailyTarget.effective_from <= target_date
    ).order_by(DailyTarget.effective_from.desc()).first()

    client = db.session.get(User, client_id)

    return jsonify({
        'client': {'id': client_id, 'username': client.username if client else ''},
        'date': target_date.isoformat(),
        'entries': [e.to_dict() for e in entries],
        'target': target.to_dict() if target else None,
        'totals': {
            'protein': sum(e.protein or 0 for e in entries),
            'fat': sum(e.fat or 0 for e in entries),
            'carbs': sum(e.carbs or 0 for e in entries),
            'calories': sum(e.calories or 0 for e in entries),
        },
    })


# ── Notifications: user reads visits by their dietitian ──────────────────────

@dietitian_bp.route('/notifications', methods=['GET'])
def notifications():
    uid = current_user_id()
    if uid is None:
        return jsonify([])

    rows = db.session.execute(
        db.text('''
            SELECT dv.id, u.username AS dietitian_name, dv.visited_at, dv.seen
            FROM dietitian_visit dv
            JOIN "user" u ON u.id = dv.dietitian_id
            WHERE dv.client_id = :uid
            ORDER BY dv.visited_at DESC
            LIMIT 20
        '''),
        {'uid': uid}
    ).fetchall()

    return jsonify([{
        'id': r[0],
        'dietitian_name': r[1],
        'visited_at': r[2].isoformat() if r[2] else None,
        'seen': bool(r[3]),
    } for r in rows])


@dietitian_bp.route('/notifications/mark-seen', methods=['POST'])
def mark_seen():
    uid = current_user_id()
    if uid is None:
        return jsonify({'ok': True})
    db.session.execute(
        db.text('UPDATE dietitian_visit SET seen=true WHERE client_id=:uid AND seen=false'),
        {'uid': uid}
    )
    db.session.commit()
    return jsonify({'ok': True})


@dietitian_bp.route('/notifications/unread-count', methods=['GET'])
def unread_count():
    uid = current_user_id()
    if uid is None:
        return jsonify({'count': 0})
    row = db.session.execute(
        db.text('SELECT COUNT(*) FROM dietitian_visit WHERE client_id=:uid AND seen=false'),
        {'uid': uid}
    ).fetchone()
    return jsonify({'count': row[0] if row else 0})


# ── Client: manage dietitian access consent ───────────────────────────────────

@dietitian_bp.route('/access', methods=['GET'])
def my_access_settings():
    uid = current_user_id()
    if uid is None:
        return jsonify([])

    rows = db.session.execute(
        db.text('''
            SELECT da.id, u.id AS dietitian_id, u.username, da.allowed, da.updated_at
            FROM dietitian_access da
            JOIN "user" u ON u.id = da.dietitian_id
            WHERE da.client_id = :uid
            ORDER BY u.username
        '''),
        {'uid': uid}
    ).fetchall()

    return jsonify([{
        'id': r[0],
        'dietitian_id': r[1],
        'dietitian_name': r[2],
        'allowed': bool(r[3]),
        'updated_at': r[4].isoformat() if r[4] else None,
    } for r in rows])


@dietitian_bp.route('/access/<int:dietitian_id>', methods=['PUT'])
def set_access(dietitian_id):
    uid = current_user_id()
    if uid is None:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json(silent=True) or {}
    allowed = bool(data.get('allowed', False))
    now = datetime.utcnow()

    existing = db.session.execute(
        db.text('SELECT id FROM dietitian_access WHERE dietitian_id=:d AND client_id=:c'),
        {'d': dietitian_id, 'c': uid}
    ).fetchone()

    if existing:
        db.session.execute(
            db.text('UPDATE dietitian_access SET allowed=:a, updated_at=:t WHERE dietitian_id=:d AND client_id=:c'),
            {'a': allowed, 't': now, 'd': dietitian_id, 'c': uid}
        )
    else:
        db.session.execute(
            db.text('INSERT INTO dietitian_access (dietitian_id, client_id, allowed, created_at, updated_at) VALUES (:d, :c, :a, :t, :t)'),
            {'d': dietitian_id, 'c': uid, 'a': allowed, 't': now}
        )
    db.session.commit()
    return jsonify({'allowed': allowed})


# ── Role switch endpoint ──────────────────────────────────────────────────────

@dietitian_bp.route('/role', methods=['PUT'])
def set_role():
    uid = current_user_id()
    if uid is None:
        return jsonify({'error': 'Authentication required'}), 401
    data = request.get_json(silent=True) or {}
    role = data.get('role', 'member')
    user = db.session.get(User, uid)
    if user is None:
        return jsonify({'error': 'User not found'}), 404
    user.is_admin = (role == 'dietitian')
    if user.is_admin:
        user.plan_feature_enabled = True
    db.session.commit()
    return jsonify({'role': user.role, 'is_admin': user.is_admin})


# ── Dietitian summary for admin user management ───────────────────────────────

@dietitian_bp.route('/stats', methods=['GET'])
def dietitian_stats():
    uid = current_user_id()
    if uid is None:
        return jsonify({'error': 'Authentication required'}), 401
    user = db.session.get(User, uid)
    if not user or not user.is_admin:
        return jsonify({'error': 'Dietitian access required'}), 403

    client_count = db.session.execute(
        db.text('SELECT COUNT(DISTINCT user_id) FROM user_plan_assignment WHERE assigned_by=:uid AND is_active=true'),
        {'uid': uid}
    ).scalar() or 0

    access_count = db.session.execute(
        db.text('SELECT COUNT(*) FROM dietitian_access WHERE dietitian_id=:uid AND allowed=true'),
        {'uid': uid}
    ).scalar() or 0

    return jsonify({'client_count': client_count, 'access_granted_count': access_count})