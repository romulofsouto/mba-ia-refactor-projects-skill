from controllers import require_payload
from models.category import DEFAULT_COLOR, Category
from models.errors import NotFoundError, ValidationError


def _get_category(cat_id):
    category = Category.find(cat_id)
    if not category:
        raise NotFoundError("Categoria não encontrada")
    return category


def list_categories():
    return [{**cat.to_dict(), "task_count": count} for cat, count in Category.all_with_task_count()], 200


def create_category(data):
    require_payload(data)
    if not data.get("name"):
        raise ValidationError("Nome é obrigatório")

    category = Category(
        name=data["name"],
        description=data.get("description", ""),
        color=data.get("color", DEFAULT_COLOR),
    )
    category.save("Erro ao criar categoria")
    return category.to_dict(), 201


def update_category(cat_id, data):
    category = _get_category(cat_id)
    require_payload(data)
    for field in ("name", "description", "color"):
        if field in data:
            setattr(category, field, data[field])
    category.save("Erro ao atualizar")
    return category.to_dict(), 200


def delete_category(cat_id):
    category = _get_category(cat_id)
    category.delete("Erro ao deletar")  # tasks da categoria ficam com category_id = NULL
    return {"message": "Categoria deletada"}, 200
