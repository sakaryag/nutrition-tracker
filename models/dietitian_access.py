from datetime import datetime, timezone
from models import db


class DietitianAccess(db.Model):
    __tablename__ = 'dietitian_access'

    id = db.Column(db.Integer, primary_key=True)
    dietitian_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True
    )
    client_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True
    )
    allowed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint('dietitian_id', 'client_id', name='uq_dietitian_access'),
    )

    dietitian = db.relationship('User', foreign_keys=[dietitian_id], backref='dietitian_clients')
    client = db.relationship('User', foreign_keys=[client_id], backref='dietitian_access_records')

    def to_dict(self):
        return {
            'id': self.id,
            'dietitian_id': self.dietitian_id,
            'client_id': self.client_id,
            'allowed': self.allowed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
