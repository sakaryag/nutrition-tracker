from datetime import date, datetime

from flask import Blueprint, jsonify, request, current_app, session

from models import db
from models.daily_note import DailyNote
from routes.auth import current_user_id

notes_bp = Blueprint('notes', __name__, url_prefix='/api/notes')


@notes_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


@notes_bp.route('', methods=['GET'])
def get_note():
    """GET /api/notes?date=YYYY-MM-DD — returns the note for that date or {content: ''}."""
    date_str = request.args.get('date', '').strip()
    try:
        note_date = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400

    uid = current_user_id()
    q = DailyNote.query.filter_by(note_date=note_date)
    if uid is not None:
        q = q.filter_by(user_id=uid)
    else:
        q = q.filter(DailyNote.user_id.is_(None))

    note = q.first()
    if note is None:
        return jsonify({'content': '', 'note_date': note_date.isoformat()})
    return jsonify(note.to_dict())


@notes_bp.route('', methods=['POST'])
def upsert_note():
    """POST /api/notes — {date, content} — upsert note for that date."""
    data = request.get_json(silent=True) or {}
    date_str = data.get('date', '').strip()
    try:
        note_date = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400

    content = data.get('content', '')

    uid = current_user_id()
    q = DailyNote.query.filter_by(note_date=note_date)
    if uid is not None:
        q = q.filter_by(user_id=uid)
    else:
        q = q.filter(DailyNote.user_id.is_(None))

    note = q.first()
    if note is None:
        note = DailyNote(
            user_id=uid,
            note_date=note_date,
            content=content,
            updated_at=datetime.utcnow(),
        )
        db.session.add(note)
    else:
        note.content = content
        note.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify(note.to_dict()), 200
