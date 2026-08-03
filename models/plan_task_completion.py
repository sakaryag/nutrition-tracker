from models import db


class PlanTaskCompletion(db.Model):
    __tablename__ = 'plan_task_completion'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('nutrition_plan.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('plan_task.id'), nullable=False)
    completed_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.String(500), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan_id': self.plan_id,
            'task_id': self.task_id,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'notes': self.notes,
        }
