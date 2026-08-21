from datetime import datetime, timezone
from models import db


class MealSlot(db.Model):
    __tablename__ = 'meal_slot'

    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(
        db.Integer, db.ForeignKey('program_day.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    slot_name = db.Column(db.String(100), nullable=False)
    slot_name_tr = db.Column(db.String(100), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    content_pattern = db.Column(db.String(1), nullable=False, default='A')
    is_optional = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    items = db.relationship(
        'SlotItem', backref='slot',
        cascade='all, delete-orphan', lazy=True,
        order_by='SlotItem.sort_order',
    )

    def to_dict(self):
        return {
            'id': self.id,
            'day_id': self.day_id,
            'slot_name': self.slot_name,
            'slot_name_tr': self.slot_name_tr,
            'sort_order': self.sort_order,
            'content_pattern': self.content_pattern,
            'is_optional': self.is_optional,
            'items': [i.to_dict() for i in self.items],
        }
