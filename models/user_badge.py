from datetime import datetime, timezone
from models import db


class UserBadge(db.Model):
    __tablename__ = 'user_badge'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False, index=True
    )
    badge_key = db.Column(db.String(50), nullable=False)
    earned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    badge_meta = db.Column(db.Text, nullable=True)  # JSON string

    __table_args__ = (
        db.UniqueConstraint('user_id', 'badge_key', name='uq_user_badge'),
    )

    user = db.relationship('User', backref='badges')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'badge_key': self.badge_key,
            'earned_at': self.earned_at.isoformat() if self.earned_at else None,
            'badge_meta': self.badge_meta,
        }
