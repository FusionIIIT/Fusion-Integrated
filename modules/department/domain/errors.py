class DomainError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class InvalidTransition(DomainError):
    pass


class PermissionDenied(DomainError):
    pass
