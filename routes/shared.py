"""routes/shared.py — /api/shared blueprint (sharing food entries with friends)."""
from datetime import datetime, date, time

from flask import Blueprint, jsonify, request, current_app, session

from models import db
from models.user import User
from models.food_entry import FoodEntry
from models.shared_entry import SharedEntry
from routes.auth import current_user_id
from routes.friends import _friend_ids

shared_bp = Blueprint('shared', __name__, url_prefix='/api/shared')


@shared_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


@shared_bp.post('')
def share_entry():
    uid = current_user_id()
    data = request.get_json(silent=True) or {}
    entry_id = data.get('entry_id')
    friend_ids_req = data.get('friend_ids', [])

    if not entry_id:
        return jsonify({'error': 'entry_id is required'}), 400
    if not friend_ids_req:
        return jsonify({'error': 'friend_ids is required'}), 400

    entry = db.session.get(FoodEntry, entry_id)
    if not entry or entry.user_id != uid:
        return jsonify({'error': 'Entry not found or not yours'}), 404

    accepted_friends = _friend_ids(uid)
    me = db.session.get(User, uid)
    prefix = f'Shared by {me.username}: '

    shared = []
    for fid in friend_ids_req:
        fid = int(fid)
        if fid not in accepted_friends:
            continue  # silently skip non-friends

        # Deduplication: skip if already shared this entry to this person
        existing = SharedEntry.query.filter_by(
            entry_id=entry_id, shared_by_id=uid, shared_to_id=fid
        ).first()
        if existing:
            continue

        # Clone the FoodEntry for the recipient
        clone = FoodEntry(
            food_name=prefix + entry.food_name,
            protein=entry.protein,
            fat=entry.fat,
            carbs=entry.carbs,
            calories=entry.calories,
            meal_type=entry.meal_type,
            serving_size=entry.serving_size,
            serving_unit=entry.serving_unit,
            entry_date=entry.entry_date,
            entry_time=entry.entry_time,
            user_id=fid,
        )
        db.session.add(clone)
        db.session.flush()  # get clone.id

        se = SharedEntry(
            entry_id=entry_id,
            shared_by_id=uid,
            shared_to_id=fid,
            cloned_entry_id=clone.id,
            shared_at=datetime.utcnow(),
        )
        db.session.add(se)

        recipient = db.session.get(User, fid)
        shared.append({
            'friend_id': fid,
            'cloned_entry_id': clone.id,
            'username': recipient.username if recipient else None,
        })

    db.session.commit()
    return jsonify({'shared': shared}), 201


@shared_bp.get('/incoming')
def incoming_shared():
    uid = current_user_id()
    rows = (
        SharedEntry.query
        .filter_by(shared_to_id=uid)
        .order_by(SharedEntry.shared_at.desc())
        .limit(50)
        .all()
    )
    result = []
    for row in rows:
        sender = db.session.get(User, row.shared_by_id)
        cloned = db.session.get(FoodEntry, row.cloned_entry_id) if row.cloned_entry_id else None
        entry_data = None
        if cloned:
            entry_data = {
                'food_name': cloned.food_name,
                'protein': cloned.protein,
                'fat': cloned.fat,
                'carbs': cloned.carbs,
                'calories': cloned.calories,
                'meal_type': cloned.meal_type,
                'entry_date': cloned.entry_date.isoformat() if cloned.entry_date else None,
            }
        result.append({
            'id': row.id,
            'shared_at': row.shared_at.isoformat() if row.shared_at else None,
            'shared_by_username': sender.username if sender else None,
            'entry': entry_data,
        })
    return jsonify(result)