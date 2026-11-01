"""Domain errors for Visitor Management System."""


class VMSDomainError(Exception):
    def __init__(self, message: str, code: str = "vms_domain_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class BlacklistedVisitorError(VMSDomainError):
    def __init__(self, message: str = "Visitor identity is flagged in the security blacklist."):
        super().__init__(message, code="visitor_blacklisted")


class InvalidTimeWindowError(VMSDomainError):
    def __init__(self, message: str = "Scheduled end time must be after start time."):
        super().__init__(message, code="invalid_time_window")


class InvalidStateTransitionError(VMSDomainError):
    def __init__(self, message: str = "State transition is invalid under the workflow rules."):
        super().__init__(message, code="invalid_state_transition")


class PassNotActiveError(VMSDomainError):
    def __init__(self, message: str = "Visitor pass is not currently active or within valid time window."):
        super().__init__(message, code="pass_not_active")


class GateAccessDeniedError(VMSDomainError):
    def __init__(self, message: str = "Pass does not have authorization for this gate or zone."):
        super().__init__(message, code="gate_access_denied")


class VisitAlreadyCompletedError(VMSDomainError):
    def __init__(self, message: str = "Visit session has already been completed."):
        super().__init__(message, code="visit_already_completed")
