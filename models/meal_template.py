from datetime import datetime, timezone
from models import db


class MealTemplate(db.Model):
    __tablename__ = 'meal_template'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    meal_type = db.Column(db.String(20), default='Snack')
    category = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    items = db.relationship(
        'MealTemplateItem', backref='template',
        cascade='all, delete-orphan', lazy=True,
    )

    def to_dict(self):
        sorted_items = sorted(self.items, key=lambda i: (i.sort_order if i.sort_order is not None else 0, i.id))
        return {
            'id': self.id,
            'name': self.name,
            'meal_type': self.meal_type,
            'category': self.category,
            'items': [i.to_dict() for i in sorted_items],
            'total_protein': round(sum(i.protein for i in self.items), 1),
            'total_fat': round(sum(i.fat for i in self.items), 1),
            'total_carbs': round(sum(i.carbs for i in self.items), 1),
            'total_calories': round(sum(i.calories for i in self.items), 0),
        }