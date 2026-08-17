from datetime import datetime, timezone
from models import db


class FeedVisibility(db.Model):
    __tablename__ = 'feed_visibility'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True
    )
    show_in_feed = db.Column(db.Boolean, nullable=False, default=False)
    show_calories = db.Column(db.Boolean, nullable=False, default=True)
    show_macros = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship('User', backref=db.backref('feed_visibility', uselist=False))

    def to_dict(self):
        return {
            'show_in_feed': bool(self.show_in_feed),
            'show_calories': bool(self.show_calories),
            'show_macros': bool(self.show_macros),
        }