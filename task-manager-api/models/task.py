from datetime import datetime

from models.database import CRUDMixin, db
from models.errors import ValidationError
from utils.dates import utc_now

VALID_STATUSES = ("pending", "in_progress", "done", "cancelled")
CLOSED_STATUSES = ("done", "cancelled")
MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_MAX = 2  # prioridades 1 (critical) e 2 (high)
MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
DUE_DATE_FORMAT = "%Y-%m-%d"


class Task(CRUDMixin, db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default="pending")
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship("User", backref=db.backref("tasks", cascade="all, delete"))
    category = db.relationship("Category", backref="tasks")

    # --- regras de domínio ---

    def is_overdue(self, now=None):
        if not self.due_date or self.status in CLOSED_STATUSES:
            return False
        return self.due_date < (now or utc_now())

    def days_overdue(self, now=None):
        return ((now or utc_now()) - self.due_date).days

    def is_high_priority(self):
        return self.priority <= HIGH_PRIORITY_MAX

    def touch(self):
        self.updated_at = utc_now()

    # --- validação de invariantes ---

    @staticmethod
    def validate_title(title):
        if not isinstance(title, str) or len(title) < MIN_TITLE_LENGTH:
            raise ValidationError("Título muito curto")
        if len(title) > MAX_TITLE_LENGTH:
            raise ValidationError("Título muito longo")

    @staticmethod
    def validate_status(status):
        if status not in VALID_STATUSES:
            raise ValidationError("Status inválido")

    @staticmethod
    def validate_priority(priority):
        if isinstance(priority, bool) or not isinstance(priority, int) or not MIN_PRIORITY <= priority <= MAX_PRIORITY:
            raise ValidationError("Prioridade deve ser entre 1 e 5")

    @staticmethod
    def parse_due_date(value, error_message):
        try:
            return datetime.strptime(value, DUE_DATE_FORMAT)
        except (TypeError, ValueError):
            raise ValidationError(error_message)

    @staticmethod
    def normalize_tags(tags):
        if isinstance(tags, list):
            return ",".join(str(tag) for tag in tags)
        return tags

    # --- consultas ---

    @classmethod
    def all_with_relations(cls):
        query = db.select(cls).options(db.joinedload(cls.user), db.joinedload(cls.category)).order_by(cls.id)
        return db.session.scalars(query).all()

    @classmethod
    def by_user(cls, user_id):
        return db.session.scalars(db.select(cls).filter_by(user_id=user_id).order_by(cls.id)).all()

    @classmethod
    def search(cls, text=None, status=None, priority=None, user_id=None):
        query = db.select(cls)
        if text:
            query = query.where(db.or_(cls.title.like(f"%{text}%"), cls.description.like(f"%{text}%")))
        if status:
            query = query.where(cls.status == status)
        if priority is not None:
            query = query.where(cls.priority == priority)
        if user_id is not None:
            query = query.where(cls.user_id == user_id)
        return db.session.scalars(query.order_by(cls.id)).all()

    # --- serialização ---

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "due_date": str(self.due_date) if self.due_date else None,
            "tags": self.tags.split(",") if self.tags else [],
        }

    def to_detail_dict(self):
        data = self.to_dict()
        data["overdue"] = self.is_overdue()
        data["user_name"] = self.user.name if self.user else None
        data["category_name"] = self.category.name if self.category else None
        return data

    def to_summary_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created_at": str(self.created_at),
            "due_date": str(self.due_date) if self.due_date else None,
            "overdue": self.is_overdue(),
        }
