from datetime import datetime, timezone
from models import db


class FriendConnection(db.Model):
    __tablename__ = 'friend_connection'

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False, index=True
    )
    recipient_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False, index=True
    )
    # status: pending | accepted | declined | blocked
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.UniqueConstraint('requester_id', 'recipient_id', name='uq_friend_connection'),
    )

    requester = db.relationship('User', foreign_keys=[requester_id], backref='sent_requests')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_requests')

    def to_dict(self):
        return {
            'id': self.id,
            'requester_id': self.requester_id,
            'recipient_id': self.recipient_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }