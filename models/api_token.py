import hashlib
import secrets
from datetime import datetime, timezone
from models import db

TOKEN_PREFIX = 'nt_'
MAX_ACTIVE_TOKENS = 10


def _utcnow():
    # Naive UTC so comparisons behave the same on SQLite and Postgres "timestamp without time zone".
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class ApiToken(db.Model):
    """Personal access token for the /api/v1 voice API. Only the sha256 hash is stored."""
    __tablename__ = 'api_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    name = db.Column(db.String(80), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    prefix = db.Column(db.String(12), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)
    revoked = db.Column(db.Boolean, nullable=False, default=False)
    # User's Gemini key encrypted with a key derived from the plaintext token; useless without it.
    enc_gemini_key = db.Column(db.Text, nullable=True)

    @staticmethod
    def generate():
        """Return (plaintext_token, token_hash, display_prefix)."""
        token = TOKEN_PREFIX + secrets.token_urlsafe(32)
        return token, hash_token(token), token[:12]

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'prefix': self.prefix,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'has_ai_key': bool(self.enc_gemini_key),
        }
