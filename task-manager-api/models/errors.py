class DomainError(Exception):
    """Erro de regra de negócio. O middleware de erro traduz cada subclasse para um status HTTP."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class ValidationError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class AuthenticationError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass


class PersistenceError(DomainError):
    pass
