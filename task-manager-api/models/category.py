from models.database import CRUDMixin, db
from utils.dates import utc_now

DEFAULT_COLOR = "#000000"


class Category(CRUDMixin, db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default=DEFAULT_COLOR)
    created_at = db.Column(db.DateTime, default=utc_now)

    @classmethod
    def all_with_task_count(cls):
        """[(entidade, nº de tasks)] em uma única query, sem N+1."""
        from models.task import Task

        query = (
            db.select(cls, db.func.count(Task.id))
            .outerjoin(Task, Task.category_id == cls.id)
            .group_by(cls.id)
            .order_by(cls.id)
        )
        return db.session.execute(query).all()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "created_at": str(self.created_at),
        }
