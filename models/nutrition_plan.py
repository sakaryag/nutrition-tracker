from datetime import datetime, timezone
from models import db


class NutritionPlan(db.Model):
    __tablename__ = 'nutrition_plan'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration_days = db.Column(db.Integer, default=7, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    tasks = db.relationship(
        'PlanTask', backref='plan',
        cascade='all, delete-orphan', lazy=True,
        order_by='PlanTask.day_offset, PlanTask.id',
    )
    assignments = db.relationship(
        'UserPlanAssignment', backref='plan',
        cascade='all, delete-orphan', lazy=True,
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'duration_days': self.duration_days,
            'created_by': self.created_by,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'task_count': len(self.tasks),
        }