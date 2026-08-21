from datetime import datetime, timezone
from models import db


class FoodExchangeCategory(db.Model):
    __tablename__ = 'food_exchange_category'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    name_tr = db.Column(db.String(200), nullable=True)
    owner_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False, index=True
    )
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.UniqueConstraint('name', 'owner_id', name='uq_exchange_category_name_owner'),
    )

    members = db.relationship(
        'ExchangeCategoryMember', backref='category',
        cascade='all, delete-orphan', lazy=True,
        order_by='ExchangeCategoryMember.sort_order',
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_tr': self.name_tr,
            'owner_id': self.owner_id,
            'description': self.description,
            'members': [m.to_dict() for m in self.members],
        }
