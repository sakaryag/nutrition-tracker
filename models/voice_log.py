import json
from datetime import datetime, timezone
from models import db


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class VoiceLog(db.Model):
    """One row per /api/v1/log call; lets follow-up calls undo/inspect the last log."""
    __tablename__ = 'voice_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow, index=True)
    text = db.Column(db.String(500), nullable=False)
    lang = db.Column(db.String(5), nullable=False, default='en')
    entry_ids = db.Column(db.Text, nullable=False, default='[]')

    def get_entry_ids(self) -> list:
        try:
            ids = json.loads(self.entry_ids or '[]')
        except ValueError:
            return []
        return [i for i in ids if isinstance(i, int)]


class AiFoodCache(db.Model):
    """Gemini-estimated food (macros per 100 g), reused for 30 days to avoid repeat API calls."""
    __tablename__ = 'ai_food_cache'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    phrase = db.Column(db.String(200), nullable=False, index=True)
    food_name = db.Column(db.String(200), nullable=False)
    protein = db.Column(db.Float, nullable=False, default=0)
    fat = db.Column(db.Float, nullable=False, default=0)
    carbs = db.Column(db.Float, nullable=False, default=0)
    calories = db.Column(db.Float, nullable=False, default=0)
    default_grams = db.Column(db.Float, nullable=False, default=100)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'phrase', name='uq_ai_food_cache_user_phrase'),
    )
