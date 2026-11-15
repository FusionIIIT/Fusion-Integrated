"""Domain exceptions for VMS Business Rules."""


class VMSDomainException(Exception):
    """Base exception for VMS domain rules."""
    def __init__(self, message: str, rule_id: str = ""):
        super().__init__(message)
        self.message = message
        self.rule_id = rule_id


class BlacklistMatchException(VMSDomainException):
    """Raised when an applicant or visitor matches a blacklist entry (BR-001, BR-004, BR-024)."""
    def __init__(self, message: str = "Visitor identity matches campus blacklist.", rule_id: str = "BR-004"):
        super().__init__(message, rule_id)


class DuplicatePassException(VMSDomainException):
    """Raised when a visitor attempts to obtain multiple passes on the same day (BR-017, BR-020)."""
    def __init__(self, message: str = "Duplicate pass requested for visitor on same day.", rule_id: str = "BR-020"):
        super().__init__(message, rule_id)


class UnauthorizedZoneException(VMSDomainException):
    """Raised when visitor attempts to enter a non-permitted zone (BR-005, BR-041)."""
    def __init__(self, message: str = "Zone access denied for visitor pass scope.", rule_id: str = "BR-041"):
        super().__init__(message, rule_id)


class PassExpiredException(VMSDomainException):
    """Raised when visitor pass validity has lapsed (BR-003)."""
    def __init__(self, message: str = "Visitor pass is expired or inactive.", rule_id: str = "BR-003"):
        super().__init__(message, rule_id)


class GateValidationException(VMSDomainException):
    """Raised when gate scan fails verification (BR-028, BR-029, BR-040)."""
    def __init__(self, message: str = "Gate validation failed.", rule_id: str = "BR-040"):
        super().__init__(message, rule_id)


class CheckoutBlockedException(VMSDomainException):
    """Raised when checkout is blocked by policy or status (BR-023, BR-043)."""
    def __init__(self, message: str = "Checkout could not be processed.", rule_id: str = "BR-023"):
        super().__init__(message, rule_id)
