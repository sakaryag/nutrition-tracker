from datetime import datetime
from models import db


class SavedFood(db.Model):
    __tablename__ = 'saved_food'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(200), nullable=True)
    source = db.Column(db.String(20), nullable=False, default='custom')
    usda_fdc_id = db.Column(db.Integer, nullable=True, unique=True)
    category = db.Column(db.String(100), nullable=True, index=True)
    protein = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    carbs = db.Column(db.Float, nullable=False)
    calories = db.Column(db.Float, nullable=False)
    fiber = db.Column(db.Float, nullable=True)
    sugar = db.Column(db.Float, nullable=True)
    default_serving = db.Column(db.Float, default=100)
    serving_unit = db.Column(db.String(20), default='g')
    food_type = db.Column(db.String(20), nullable=False, default='ingredient')
    name_tr = db.Column(db.String(300), nullable=True)
    is_archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.Index('ix_saved_food_name', 'name'),
        db.Index('ix_saved_food_source', 'source'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'source': self.source,
            'usda_fdc_id': self.usda_fdc_id,
            'category': self.category,
            'protein': self.protein,
            'fat': self.fat,
            'carbs': self.carbs,
            'calories': self.calories,
            'fiber': self.fiber,
            'sugar': self.sugar,
            'default_serving': self.default_serving,
            'serving_unit': self.serving_unit,
            'food_type': self.food_type,
            'name_tr': self.name_tr,
            'is_archived': self.is_archived,
        }