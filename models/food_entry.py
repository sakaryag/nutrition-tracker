from datetime import datetime
from models import db


class FoodEntry(db.Model):
    __tablename__ = 'food_entry'

    id = db.Column(db.Integer, primary_key=True)
    food_name = db.Column(db.String(200), nullable=False)
    protein = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    carbs = db.Column(db.Float, nullable=False)
    calories = db.Column(db.Float, nullable=False)
    meal_type = db.Column(db.String(20), default='Snack')
    serving_size = db.Column(db.Float, nullable=True)
    serving_unit = db.Column(db.String(20), default='g')
    saved_food_id = db.Column(
        db.Integer, db.ForeignKey('saved_food.id'), nullable=True
    )
    entry_date = db.Column(db.Date, nullable=False, index=True)
    entry_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    template_id = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)

    saved_food = db.relationship('SavedFood', backref='entries', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'food_name': self.food_name,
            'protein': self.protein,
            'fat': self.fat,
            'carbs': self.carbs,
            'calories': self.calories,
            'meal_type': self.meal_type,
            'serving_size': self.serving_size,
            'serving_unit': self.serving_unit,
            'saved_food_id': self.saved_food_id,
            'template_id': self.template_id,
            'entry_date': self.entry_date.isoformat(),
            'entry_time': self.entry_time.isoformat(),
        }
