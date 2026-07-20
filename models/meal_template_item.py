from models import db


class MealTemplateItem(db.Model):
    __tablename__ = 'meal_template_item'

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(
        db.Integer, db.ForeignKey('meal_template.id'), nullable=False
    )
    food_name = db.Column(db.String(200), nullable=False)
    saved_food_id = db.Column(
        db.Integer, db.ForeignKey('saved_food.id'), nullable=True
    )
    protein = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    carbs = db.Column(db.Float, nullable=False)
    calories = db.Column(db.Float, nullable=False)
    serving_size = db.Column(db.Float, nullable=True)
    serving_unit = db.Column(db.String(20), default='g')

    saved_food = db.relationship('SavedFood', foreign_keys=[saved_food_id], lazy='joined', uselist=False)

    def to_dict(self):
        valid_units = None
        if self.saved_food is not None:
            valid_units = self.saved_food.valid_units
        return {
            'id': self.id,
            'template_id': self.template_id,
            'food_name': self.food_name,
            'saved_food_id': self.saved_food_id,
            'protein': self.protein,
            'fat': self.fat,
            'carbs': self.carbs,
            'calories': self.calories,
            'serving_size': self.serving_size,
            'serving_unit': self.serving_unit,
            'valid_units': valid_units,
        }