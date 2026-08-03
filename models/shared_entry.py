from datetime import datetime
from models import db


class SharedEntry(db.Model):
    __tablename__ = 'shared_entry'

    id = db.Column(db.Integer, primary_key=True)
    # entry_id goes NULL if the original FoodEntry is deleted
    entry_id = db.Column(
        db.Integer,
        db.ForeignKey('food_entry.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    shared_by_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False, index=True
    )
    shared_to_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False, index=True
    )
    # Points to the cloned FoodEntry created in the recipient's log
    cloned_entry_id = db.Column(
        db.Integer,
        db.ForeignKey('food_entry.id'),
        nullable=True,
    )
    shared_at = db.Column(db.DateTime, default=datetime.utcnow)

    shared_by = db.relationship('User', foreign_keys=[shared_by_id], backref='shares_sent')
    shared_to = db.relationship('User', foreign_keys=[shared_to_id], backref='shares_received')
    original_entry = db.relationship('FoodEntry', foreign_keys=[entry_id])
    cloned_entry = db.relationship('FoodEntry', foreign_keys=[cloned_entry_id])

    def to_dict(self):
        return {
            'id': self.id,
            'entry_id': self.entry_id,
            'shared_by_id': self.shared_by_id,
            'shared_to_id': self.shared_to_id,
            'cloned_entry_id': self.cloned_entry_id,
            'shared_at': self.shared_at.isoformat() if self.shared_at else None,
        }
