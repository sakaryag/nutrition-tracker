from models import db


class SlotItem(db.Model):
    __tablename__ = 'slot_item'

    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(
        db.Integer, db.ForeignKey('meal_slot.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    alternative_group = db.Column(db.Integer, nullable=True)
    rotation_frequency = db.Column(db.Integer, nullable=True)
    saved_food_id = db.Column(
        db.Integer, db.ForeignKey('saved_food.id'), nullable=True
    )
    recipe_id = db.Column(
        db.Integer, db.ForeignKey('recipe.id'), nullable=True
    )
    exchange_category_id = db.Column(
        db.Integer, db.ForeignKey('food_exchange_category.id'), nullable=True
    )
    food_name_override = db.Column(db.String(200), nullable=True)
    quantity = db.Column(db.Float, nullable=True)
    unit = db.Column(db.String(20), nullable=True)
    is_fallback = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)
    notes_tr = db.Column(db.Text, nullable=True)

    saved_food = db.relationship('SavedFood', foreign_keys=[saved_food_id], lazy='joined', uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'slot_id': self.slot_id,
            'alternative_group': self.alternative_group,
            'rotation_frequency': self.rotation_frequency,
            'saved_food_id': self.saved_food_id,
            'recipe_id': self.recipe_id,
            'exchange_category_id': self.exchange_category_id,
            'food_name_override': self.food_name_override,
            'food_name': self.saved_food.name if self.saved_food else self.food_name_override,
            'quantity': self.quantity,
            'unit': self.unit,
            'is_fallback': self.is_fallback,
            'sort_order': self.sort_order,
            'notes': self.notes,
            'notes_tr': self.notes_tr,
        }
