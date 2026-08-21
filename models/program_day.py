from datetime import datetime, timezone
from models import db


class ProgramDay(db.Model):
    __tablename__ = 'program_day'

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey('nutrition_plan.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    day_offset = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(100), nullable=True)
    label_tr = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('program_id', 'day_offset', name='uq_program_day_offset'),
    )

    slots = db.relationship(
        'MealSlot', backref='day',
        cascade='all, delete-orphan', lazy=True,
        order_by='MealSlot.sort_order',
    )

    def to_dict(self):
        return {
            'id': self.id,
            'program_id': self.program_id,
            'day_offset': self.day_offset,
            'label': self.label,
            'label_tr': self.label_tr,
            'notes': self.notes,
            'sort_order': self.sort_order,
            'slots': [s.to_dict() for s in self.slots],
        }
