from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

from models.errors import PersistenceError

db = SQLAlchemy()


def commit(error_message):
    try:
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise PersistenceError(error_message) from exc


class CRUDMixin:
    @classmethod
    def find(cls, record_id):
        return db.session.get(cls, record_id)

    @classmethod
    def all(cls):
        return db.session.scalars(db.select(cls).order_by(cls.id)).all()

    @classmethod
    def count(cls):
        return db.session.scalar(db.select(db.func.count(cls.id)))

    def save(self, error_message="Erro ao salvar"):
        db.session.add(self)
        commit(error_message)
        return self

    def delete(self, error_message="Erro ao deletar"):
        db.session.delete(self)
        commit(error_message)
