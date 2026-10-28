"""Pure domain exceptions for Employee Leave Management."""


class ElmDomainError(Exception):
    code = "elm_domain_error"


class InvalidLeaveRequest(ElmDomainError):
    code = "invalid_leave_request"


class InvalidTransition(ElmDomainError):
    code = "invalid_transition"


class NotEligible(ElmDomainError):
    code = "not_eligible"


class InsufficientBalance(ElmDomainError):
    code = "insufficient_balance"


class OverlapDetected(ElmDomainError):
    code = "leave_overlap"


class SubstituteRequired(ElmDomainError):
    code = "substitute_required"


class ActorNotAllowed(ElmDomainError):
    code = "actor_not_allowed"
