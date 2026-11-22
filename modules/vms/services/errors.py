"""VMS Service Exceptions.
Inherits from core.api.exceptions.DomainError subclasses.
"""

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError


class BlacklistMatchError(ConflictError):
    code = "vms_blacklist_match"

    def __init__(
        self, message="Identity matches campus security blacklist (rule BR-004).", rule_id="BR-004"
    ):
        super().__init__(message, code=self.code)
        self.rule_id = rule_id


class DuplicatePassError(ConflictError):
    code = "vms_duplicate_pass"

    def __init__(
        self,
        message="Visitor already has an active pass for this date (rule BR-020).",
        rule_id="BR-020",
    ):
        super().__init__(message, code=self.code)
        self.rule_id = rule_id


class InvalidTransitionError(ConflictError):
    code = "vms_invalid_transition"

    def __init__(
        self, message="State transition is not permitted (rule BR-023).", rule_id="BR-023"
    ):
        super().__init__(message, code=self.code)
        self.rule_id = rule_id


class UnauthorizedZoneError(PermissionDeniedError):
    code = "vms_unauthorized_zone"

    def __init__(
        self,
        message="Visitor is not authorized to access this zone (rule BR-041).",
        rule_id="BR-041",
    ):
        super().__init__(message, code=self.code)
        self.rule_id = rule_id


class PassExpiredError(ConflictError):
    code = "vms_pass_expired"

    def __init__(self, message="Pass validity has expired (rule BR-045).", rule_id="BR-045"):
        super().__init__(message, code=self.code)
        self.rule_id = rule_id


class VisitNotFoundError(NotFoundError):
    code = "vms_visit_not_found"

    def __init__(self, message="Visit record not found."):
        super().__init__(message, code=self.code)
