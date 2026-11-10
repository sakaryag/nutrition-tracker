"""Session-authenticated management of personal access tokens for the /api/v1 voice API."""
from flask import Blueprint, current_app, jsonify, request, session

from models import db
from models.api_token import ApiToken, MAX_ACTIVE_TOKENS
from utils import gemini as G

tokens_bp = Blueprint('tokens', __name__, url_prefix='/api/tokens')


@tokens_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


def _uid():
    return session.get('user_id') if current_app.config.get('AUTH_ENABLED') else None


@tokens_bp.route('', methods=['GET'])
def list_tokens():
    rows = (ApiToken.query.filter_by(user_id=_uid(), revoked=False)
            .order_by(ApiToken.created_at.desc()).all())
    return jsonify([t.to_dict() for t in rows])


@tokens_bp.route('', methods=['POST'])
def create_token():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'JSON body required'}), 400
    name = data.get('name', '')
    if not isinstance(name, str) or not name.strip():
        return jsonify({'error': 'name is required'}), 400
    name = name.strip()
    if len(name) > 80:
        return jsonify({'error': 'name must be at most 80 characters'}), 400

    uid = _uid()
    if ApiToken.query.filter_by(user_id=uid, revoked=False).count() >= MAX_ACTIVE_TOKENS:
        return jsonify({'error': f'At most {MAX_ACTIVE_TOKENS} active tokens allowed'}), 400

    token, token_hash, prefix = ApiToken.generate()
    row = ApiToken(user_id=uid, name=name, token_hash=token_hash, prefix=prefix)
    if data.get('use_ai_key', True) is not False:
        key = G.cookie_key(uid)
        if key:
            row.enc_gemini_key = G.seal_for_token(key, token)
    db.session.add(row)
    db.session.commit()
    return jsonify({'id': row.id, 'name': row.name, 'prefix': row.prefix,
                    'created_at': row.created_at.isoformat(), 'token': token,
                    'has_ai_key': bool(row.enc_gemini_key)}), 201


@tokens_bp.route('/<int:token_id>', methods=['DELETE'])
def delete_token(token_id):
    row = ApiToken.query.filter_by(id=token_id, user_id=_uid()).first()
    if row is None:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({'deleted': token_id})
