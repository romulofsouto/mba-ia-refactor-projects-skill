from datetime import timedelta

from models.category import Category
from models.task import Task, VALID_STATUSES
from models.user import User
from utils.dates import utc_now

PRIORITY_LABELS = {1: "critical", 2: "high", 3: "medium", 4: "low", 5: "minimal"}
RECENT_ACTIVITY_DAYS = 7


def completion_rate(done, total):
    return round((done / total) * 100, 2) if total > 0 else 0


def status_counts(tasks):
    return {status: sum(1 for task in tasks if task.status == status) for status in VALID_STATUSES}


def priority_counts(tasks):
    return {label: sum(1 for task in tasks if task.priority == p) for p, label in PRIORITY_LABELS.items()}


def task_stats():
    tasks = Task.all()
    by_status = status_counts(tasks)
    total = len(tasks)
    return {
        "total": total,
        **by_status,
        "overdue": sum(1 for task in tasks if task.is_overdue()),
        "completion_rate": completion_rate(by_status["done"], total),
    }


def summary():
    now = utc_now()
    tasks = Task.all()
    overdue = [task for task in tasks if task.is_overdue(now)]
    since = now - timedelta(days=RECENT_ACTIVITY_DAYS)

    tasks_by_user = {}
    for task in tasks:
        tasks_by_user.setdefault(task.user_id, []).append(task)

    user_productivity = []
    for user in User.all():
        user_tasks = tasks_by_user.get(user.id, [])
        completed = sum(1 for task in user_tasks if task.status == "done")
        user_productivity.append({
            "user_id": user.id,
            "user_name": user.name,
            "total_tasks": len(user_tasks),
            "completed_tasks": completed,
            "completion_rate": completion_rate(completed, len(user_tasks)),
        })

    return {
        "generated_at": str(now),
        "overview": {
            "total_tasks": len(tasks),
            "total_users": User.count(),
            "total_categories": Category.count(),
        },
        "tasks_by_status": status_counts(tasks),
        "tasks_by_priority": priority_counts(tasks),
        "overdue": {
            "count": len(overdue),
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "due_date": str(task.due_date),
                    "days_overdue": task.days_overdue(now),
                }
                for task in overdue
            ],
        },
        "recent_activity": {
            "tasks_created_last_7_days": sum(1 for t in tasks if t.created_at and t.created_at >= since),
            "tasks_completed_last_7_days": sum(
                1 for t in tasks if t.status == "done" and t.updated_at and t.updated_at >= since
            ),
        },
        "user_productivity": user_productivity,
    }


def user_report(user):
    tasks = Task.by_user(user.id)
    by_status = status_counts(tasks)
    total = len(tasks)
    return {
        "user": {"id": user.id, "name": user.name, "email": user.email},
        "statistics": {
            "total_tasks": total,
            **by_status,
            "overdue": sum(1 for task in tasks if task.is_overdue()),
            "high_priority": sum(1 for task in tasks if task.is_high_priority()),
            "completion_rate": completion_rate(by_status["done"], total),
        },
    }
