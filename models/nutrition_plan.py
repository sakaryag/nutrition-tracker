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

    status = db.Column(db.String(20), nullable=False, default='draft')
    # Values: draft, active, archived
    is_template = db.Column(db.Boolean, nullable=False, default=False)
    parent_template_id = db.Column(
        db.Integer, db.ForeignKey('nutrition_plan.id'), nullable=True
    )
    current_version = db.Column(db.Integer, nullable=False, default=1)
    name_tr = db.Column(db.String(200), nullable=True)
    locale = db.Column(db.String(10), nullable=True, default='tr')

    tasks = db.relationship(
        'PlanTask', backref='plan',
        cascade='all, delete-orphan', lazy=True,
        order_by='PlanTask.day_offset, PlanTask.id',
    )
    assignments = db.relationship(
        'UserPlanAssignment', backref='plan',
        cascade='all, delete-orphan', lazy=True,
    )
    days = db.relationship(
        'ProgramDay', backref='program',
        cascade='all, delete-orphan', lazy=True,
        order_by='ProgramDay.sort_order',
    )
    guidelines = db.relationship(
        'ProgramGuideline', backref='program',
        cascade='all, delete-orphan', lazy=True,
        order_by='ProgramGuideline.sort_order',
    )
    versions = db.relationship(
        'ProgramVersion', backref='program',
        cascade='all, delete-orphan', lazy=True,
        order_by='ProgramVersion.version_number',
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_tr': self.name_tr,
            'description': self.description,
            'duration_days': self.duration_days,
            'created_by': self.created_by,
            'is_public': self.is_public,
            'status': self.status,
            'is_template': self.is_template,
            'parent_template_id': self.parent_template_id,
            'current_version': self.current_version,
            'locale': self.locale,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'task_count': len(self.tasks),
        }