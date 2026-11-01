class InvalidTransition(ValueError):
    pass


class ActorNotAllowed(PermissionError):
    pass


class GuardFailed(ValueError):
    pass
