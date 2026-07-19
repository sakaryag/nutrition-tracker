from datetime import datetime
from models import db


class MealTemplate(db.Model):
    __tablename__ = 'meal_template'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    meal_type = db.Column(db.String(20), default='Snack')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    items = db.relationship(
        'MealTemplateItem', backref='template',
        cascade='all, delete-orphan', lazy=True,
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'meal_type': self.meal_type,
            'items': [i.to_dict() for i in self.items],
            'total_protein': round(sum(i.protein for i in self.items), 1),
            'total_fat': round(sum(i.fat for i in self.items), 1),
            'total_carbs': round(sum(i.carbs for i in self.items), 1),
            'total_calories': round(sum(i.calories for i in self.items), 0),
        }