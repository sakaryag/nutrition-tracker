from datetime import datetime, timezone
from models import db


class WaterLog(db.Model):
    __tablename__ = 'water_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    log_date = db.Column(db.Date, nullable=False, index=True)
    amount_ml = db.Column(db.Float, nullable=False)
    logged_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'log_date': self.log_date.isoformat() if self.log_date else None,
            'amount_ml': self.amount_ml,
            'logged_at': self.logged_at.isoformat() if self.logged_at else None,
        }
