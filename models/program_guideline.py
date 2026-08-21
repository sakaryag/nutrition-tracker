from datetime import datetime, timezone
from models import db


class ProgramGuideline(db.Model):
    __tablename__ = 'program_guideline'

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey('nutrition_plan.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    # Valid types: frequency, daily_quantity, timing, conditional, cooking_method, general
    guideline_type = db.Column(db.String(30), nullable=False)
    target_category_id = db.Column(
        db.Integer, db.ForeignKey('food_exchange_category.id'), nullable=True
    )
    target_food_id = db.Column(
        db.Integer, db.ForeignKey('saved_food.id'), nullable=True
    )
    frequency_min = db.Column(db.Integer, nullable=True)
    frequency_max = db.Column(db.Integer, nullable=True)
    daily_qty_min = db.Column(db.Float, nullable=True)
    daily_qty_max = db.Column(db.Float, nullable=True)
    unit = db.Column(db.String(20), nullable=True)
    rule_text = db.Column(db.Text, nullable=False)
    rule_text_tr = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'program_id': self.program_id,
            'guideline_type': self.guideline_type,
            'target_category_id': self.target_category_id,
            'target_food_id': self.target_food_id,
            'frequency_min': self.frequency_min,
            'frequency_max': self.frequency_max,
            'daily_qty_min': self.daily_qty_min,
            'daily_qty_max': self.daily_qty_max,
            'unit': self.unit,
            'rule_text': self.rule_text,
            'rule_text_tr': self.rule_text_tr,
            'sort_order': self.sort_order,
        }
