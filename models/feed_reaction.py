from datetime import datetime, timezone
from models import db


class FeedReaction(db.Model):
    __tablename__ = 'feed_reaction'

    id = db.Column(db.Integer, primary_key=True)
    reactor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_date = db.Column(db.Date, nullable=False)
    emoji = db.Column(db.String(10), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.UniqueConstraint('reactor_id', 'target_user_id', 'target_date', name='uq_feed_reaction'),
    )

    reactor = db.relationship('User', foreign_keys=[reactor_id])
    target_user = db.relationship('User', foreign_keys=[target_user_id])
