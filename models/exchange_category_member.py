from models import db


class ExchangeCategoryMember(db.Model):
    __tablename__ = 'exchange_category_member'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey('food_exchange_category.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    saved_food_id = db.Column(
        db.Integer, db.ForeignKey('saved_food.id'), nullable=True
    )
    food_name_override = db.Column(db.String(200), nullable=True)
    equivalent_qty = db.Column(db.Float, nullable=False)
    equivalent_unit = db.Column(db.String(20), nullable=False, default='g')
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    saved_food = db.relationship('SavedFood', foreign_keys=[saved_food_id], lazy='joined', uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'category_id': self.category_id,
            'saved_food_id': self.saved_food_id,
            'food_name_override': self.food_name_override,
            'food_name': self.saved_food.name if self.saved_food else self.food_name_override,
            'equivalent_qty': self.equivalent_qty,
            'equivalent_unit': self.equivalent_unit,
            'sort_order': self.sort_order,
        }
