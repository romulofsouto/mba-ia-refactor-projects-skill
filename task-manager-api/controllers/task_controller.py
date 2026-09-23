import logging

from controllers import require_payload
from models.category import Category
from models.errors import NotFoundError, ValidationError
from models.task import DEFAULT_PRIORITY, Task
from models.user import User
from services import report_service

logger = logging.getLogger(__name__)


def _get_task(task_id):
    task = Task.find(task_id)
    if not task:
        raise NotFoundError("Task não encontrada")
    return task


def _ensure_references_exist(user_id, category_id):
    if user_id and not User.find(user_id):
        raise NotFoundError("Usuário não encontrado")
    if category_id and not Category.find(category_id):
        raise NotFoundError("Categoria não encontrada")


def _parse_int_arg(value, error_message):
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        raise ValidationError(error_message)


def list_tasks():
    return [task.to_detail_dict() for task in Task.all_with_relations()], 200


def get_task(task_id):
    task = _get_task(task_id)
    return {**task.to_dict(), "overdue": task.is_overdue()}, 200


def create_task(data):
    require_payload(data)
    title = data.get("title")
    if not title:
        raise ValidationError("Título é obrigatório")
    Task.validate_title(title)

    status = data.get("status", "pending")
    priority = data.get("priority", DEFAULT_PRIORITY)
    Task.validate_status(status)
    Task.validate_priority(priority)
    _ensure_references_exist(data.get("user_id"), data.get("category_id"))

    task = Task(
        title=title,
        description=data.get("description", ""),
        status=status,
        priority=priority,
        user_id=data.get("user_id"),
        category_id=data.get("category_id"),
    )
    if data.get("due_date"):
        task.due_date = Task.parse_due_date(data["due_date"], "Formato de data inválido. Use YYYY-MM-DD")
    if data.get("tags"):
        task.tags = Task.normalize_tags(data["tags"])

    task.save("Erro ao criar task")
    logger.info("Task criada: %s - %s", task.id, task.title)
    return task.to_dict(), 201


def update_task(task_id, data):
    task = _get_task(task_id)
    require_payload(data)

    changes = {}
    if "title" in data:
        Task.validate_title(data["title"])
        changes["title"] = data["title"]
    if "description" in data:
        changes["description"] = data["description"]
    if "status" in data:
        Task.validate_status(data["status"])
        changes["status"] = data["status"]
    if "priority" in data:
        Task.validate_priority(data["priority"])
        changes["priority"] = data["priority"]
    if "user_id" in data:
        _ensure_references_exist(data["user_id"], None)
        changes["user_id"] = data["user_id"]
    if "category_id" in data:
        _ensure_references_exist(None, data["category_id"])
        changes["category_id"] = data["category_id"]
    if "due_date" in data:
        due_date = data["due_date"]
        changes["due_date"] = Task.parse_due_date(due_date, "Formato de data inválido") if due_date else None
    if "tags" in data:
        changes["tags"] = Task.normalize_tags(data["tags"])

    for field, value in changes.items():
        setattr(task, field, value)
    task.touch()
    task.save("Erro ao atualizar")
    logger.info("Task atualizada: %s", task.id)
    return task.to_dict(), 200


def delete_task(task_id):
    task = _get_task(task_id)
    task.delete("Erro ao deletar")
    logger.info("Task deletada: %s", task_id)
    return {"message": "Task deletada com sucesso"}, 200


def search_tasks(args):
    tasks = Task.search(
        text=args.get("q", ""),
        status=args.get("status", ""),
        priority=_parse_int_arg(args.get("priority", ""), "Prioridade inválida"),
        user_id=_parse_int_arg(args.get("user_id", ""), "user_id inválido"),
    )
    return [task.to_dict() for task in tasks], 200


def task_stats():
    return report_service.task_stats(), 200
