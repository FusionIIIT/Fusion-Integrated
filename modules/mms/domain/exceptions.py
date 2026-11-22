"""Domain errors raised by MMS rules and state transitions.

These are plain exceptions — no Django, DRF or Celery — so they stay
callable from tasks and management commands. The service layer maps them
to `core.api.exceptions` types with an HTTP status.
"""


class DomainError(Exception):
    code = "domain_error"
    message = "The request could not be processed."

    def __init__(self, message=None, *, code=None, details=None):
        msg = message or self.message
        super().__init__(msg)
        self.message = msg
        self.code = code or self.code
        self.details = details or []


class InvalidTransition(DomainError):
    code = "invalid_transition"
    message = "This state change is not allowed."

    def __init__(self, frm=None, to=None, message=None, *, code=None, details=None):
        if frm and to and not message:
            message = f"Cannot transition from {frm} to {to}."
        super().__init__(message or self.message, code=code or self.code, details=details)
        self.frm = frm
        self.to = to


class ActorNotAllowed(DomainError):
    code = "actor_not_allowed"
    message = "This actor may not perform that action."

    def __init__(
        self, actor_kind=None, frm=None, to=None, message=None, *, code=None, details=None
    ):
        if actor_kind and not message:
            message = f"Actor kind {actor_kind} is not allowed to transition from {frm} to {to}."
        super().__init__(message or self.message, code=code or self.code, details=details)
        self.actor_kind = actor_kind
        self.frm = frm
        self.to = to


class GuardFailed(DomainError):
    code = "guard_failed"
    message = "A precondition for this action is not met."

    def __init__(self, rule_or_message=None, message=None, *, code=None, details=None):
        if message is not None:
            rule_code = rule_or_message
            msg = message
        else:
            rule_code = code or self.code
            msg = rule_or_message or self.message
        super().__init__(msg, code=rule_code or self.code, details=details)
        self.rule = rule_code


class NotFound(DomainError):
    code = "not_found"
    message = "Not found."
