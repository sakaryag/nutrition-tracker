from datetime import datetime, timezone
from models import db


class Recipe(db.Model):
    __tablename__ = 'recipe'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    name_tr = db.Column(db.String(200), nullable=True)
    owner_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False, index=True
    )
    prep_notes = db.Column(db.Text, nullable=True)
    prep_notes_tr = db.Column(db.Text, nullable=True)
    category_tags = db.Column(db.Text, nullable=True)  # JSON array stored as Text
    total_protein = db.Column(db.Float, nullable=True)
    total_fat = db.Column(db.Float, nullable=True)
    total_carbs = db.Column(db.Float, nullable=True)
    total_calories = db.Column(db.Float, nullable=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    ingredients = db.relationship(
        'RecipeIngredient', backref='recipe',
        cascade='all, delete-orphan', lazy=True,
        order_by='RecipeIngredient.sort_order',
    )

    def recalculate_totals(self):
        self.total_protein = round(sum(i.protein or 0 for i in self.ingredients), 1)
        self.total_fat = round(sum(i.fat or 0 for i in self.ingredients), 1)
        self.total_carbs = round(sum(i.carbs or 0 for i in self.ingredients), 1)
        self.total_calories = round(sum(i.calories or 0 for i in self.ingredients), 0)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_tr': self.name_tr,
            'owner_id': self.owner_id,
            'prep_notes': self.prep_notes,
            'prep_notes_tr': self.prep_notes_tr,
            'category_tags': self.category_tags,
            'total_protein': self.total_protein,
            'total_fat': self.total_fat,
            'total_carbs': self.total_carbs,
            'total_calories': self.total_calories,
            'is_archived': self.is_archived,
            'ingredients': [i.to_dict() for i in self.ingredients],
        }
