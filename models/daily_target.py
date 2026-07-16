from datetime import datetime
from models import db


class DailyTarget(db.Model):
    __tablename__ = 'daily_target'

    id = db.Column(db.Integer, primary_key=True)
    protein = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    carbs = db.Column(db.Float, nullable=False)
    calories = db.Column(db.Float, nullable=False)
    effective_from = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'protein': self.protein,
            'fat': self.fat,
            'carbs': self.carbs,
            'calories': self.calories,
            'effective_from': self.effective_from.isoformat(),
        }
