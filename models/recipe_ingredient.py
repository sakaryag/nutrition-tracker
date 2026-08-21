from models import db


class RecipeIngredient(db.Model):
    __tablename__ = 'recipe_ingredient'

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(
        db.Integer, db.ForeignKey('recipe.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    saved_food_id = db.Column(
        db.Integer, db.ForeignKey('saved_food.id'), nullable=True
    )
    food_name_override = db.Column(db.String(200), nullable=True)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False, default='g')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    # Cached macros at this quantity (denormalized for performance)
    protein = db.Column(db.Float, nullable=True)
    fat = db.Column(db.Float, nullable=True)
    carbs = db.Column(db.Float, nullable=True)
    calories = db.Column(db.Float, nullable=True)

    saved_food = db.relationship('SavedFood', foreign_keys=[saved_food_id], lazy='joined', uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'recipe_id': self.recipe_id,
            'saved_food_id': self.saved_food_id,
            'food_name_override': self.food_name_override,
            'food_name': self.saved_food.name if self.saved_food else self.food_name_override,
            'quantity': self.quantity,
            'unit': self.unit,
            'sort_order': self.sort_order,
            'protein': self.protein,
            'fat': self.fat,
            'carbs': self.carbs,
            'calories': self.calories,
        }
