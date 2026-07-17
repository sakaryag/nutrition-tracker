from models import db


class RecipeCatalog(db.Model):
    __tablename__ = 'recipe_catalog'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=True)
    cuisine = db.Column(db.String(50), nullable=True)
    source = db.Column(db.String(50), nullable=True)  # 'turkish-kaggle', '3a2m-kaggle'

    def to_dict(self):
        return {
            'id': f'rc-{self.id}',  # prefix to avoid ID collision with saved_food
            'name': self.name,
            'brand': None,
            'source': self.source or 'catalog',
            'category': self.category,
            'protein': 0.0,
            'fat': 0.0,
            'carbs': 0.0,
            'calories': 0.0,
            'fiber': None,
            'sugar': None,
            'default_serving': 100.0,
            'serving_unit': 'g',
            'food_type': 'meal',
            'is_archived': False,
            'from_catalog': True,  # flag so UI can show "macros unknown"
        }
