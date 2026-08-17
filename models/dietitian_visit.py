from datetime import datetime, timezone
from models import db


class DietitianVisit(db.Model):
    __tablename__ = 'dietitian_visit'

    id = db.Column(db.Integer, primary_key=True)
    dietitian_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False
    )
    client_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True
    )
    visited_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    seen = db.Column(db.Boolean, nullable=False, default=False)

    dietitian = db.relationship('User', foreign_keys=[dietitian_id], backref='visits_made')
    client = db.relationship('User', foreign_keys=[client_id], backref='dietitian_visits')

    def to_dict(self):
        return {
            'id': self.id,
            'dietitian_id': self.dietitian_id,
            'client_id': self.client_id,
            'visited_at': self.visited_at.isoformat() if self.visited_at else None,
            'seen': self.seen,
        }
