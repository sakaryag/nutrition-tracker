from datetime import datetime, timezone
from models import db


class SlotFulfillment(db.Model):
    __tablename__ = 'slot_fulfillment'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False, index=True
    )
    slot_id = db.Column(
        db.Integer, db.ForeignKey('meal_slot.id'), nullable=False, index=True
    )
    fulfillment_date = db.Column(db.Date, nullable=False, index=True)
    saved_food_id = db.Column(
        db.Integer, db.ForeignKey('saved_food.id'), nullable=True
    )
    exchange_category_id = db.Column(
        db.Integer, db.ForeignKey('food_exchange_category.id'), nullable=True
    )
    recipe_id = db.Column(
        db.Integer, db.ForeignKey('recipe.id'), nullable=True
    )
    quantity = db.Column(db.Float, nullable=True)
    unit = db.Column(db.String(20), nullable=True)
    food_entry_id = db.Column(
        db.Integer, db.ForeignKey('food_entry.id'), nullable=True
    )
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'slot_id', 'fulfillment_date',
                            name='uq_slot_fulfillment_per_day'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'slot_id': self.slot_id,
            'fulfillment_date': self.fulfillment_date.isoformat() if self.fulfillment_date else None,
            'saved_food_id': self.saved_food_id,
            'exchange_category_id': self.exchange_category_id,
            'recipe_id': self.recipe_id,
            'quantity': self.quantity,
            'unit': self.unit,
            'food_entry_id': self.food_entry_id,
        }
