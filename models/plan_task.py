from models import db


class PlanTask(db.Model):
    __tablename__ = 'plan_task'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(
        db.Integer, db.ForeignKey('nutrition_plan.id'), nullable=False, index=True
    )
    day_offset = db.Column(db.Integer, nullable=False, default=0)
    task_type = db.Column(db.String(20), nullable=False, default='food')
    description = db.Column(db.String(500), nullable=False)
    food_name = db.Column(db.String(200), nullable=True)
    quantity = db.Column(db.Float, nullable=True)
    unit = db.Column(db.String(20), nullable=True)
    repeat_days = db.Column(db.String(100), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'day_offset': self.day_offset,
            'task_type': self.task_type,
            'description': self.description,
            'food_name': self.food_name,
            'quantity': self.quantity,
            'unit': self.unit,
            'repeat_days': self.repeat_days,
        }
