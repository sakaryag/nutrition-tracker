from datetime import datetime, timezone
from models import db


class WeightLog(db.Model):
    __tablename__ = 'weight_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    log_date = db.Column(db.Date, nullable=False, index=True)
    weight_kg = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.log_date.isoformat(),
            'weight_kg': self.weight_kg,
        }


class BodyGoal(db.Model):
    """Per-user height + goal weight; user_id NULL is the single auth-disabled profile."""
    __tablename__ = 'body_goal'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, unique=True, index=True)
    height_cm = db.Column(db.Float, nullable=True)
    goal_weight_kg = db.Column(db.Float, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True,
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
