from models import db


class WeeklyCategoryQuota(db.Model):
    __tablename__ = 'weekly_category_quota'

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey('nutrition_plan.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    exchange_category_id = db.Column(
        db.Integer, db.ForeignKey('food_exchange_category.id'), nullable=False
    )
    quota_per_week = db.Column(db.Integer, nullable=False)
    slot_id = db.Column(
        db.Integer, db.ForeignKey('meal_slot.id'), nullable=True
    )
    notes = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'program_id': self.program_id,
            'exchange_category_id': self.exchange_category_id,
            'quota_per_week': self.quota_per_week,
            'slot_id': self.slot_id,
            'notes': self.notes,
        }
