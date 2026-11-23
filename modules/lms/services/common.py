"""Translate pure rule failures at the transactional service boundary."""

from functools import wraps

from core.api.exceptions import ConflictError, DomainError, PermissionDeniedError
from modules.lms.domain.rules import RuleViolation, require_role


def enforce_rules(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except RuleViolation as exc:
            error = {
                "LMS_ROLE_DENIED": PermissionDeniedError,
                "LMS_STATE_CONFLICT": ConflictError,
            }.get(exc.code, DomainError)
            raise error(str(exc), code=exc.code) from exc

    return call


def faculty(scope):
    require_role(scope.role, ("FACULTY",))
