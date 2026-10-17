"""Domain errors. Plain exceptions: services map them to HTTP-aware ones, so
the rules stay callable from a task or a management command."""


class LeaveRuleViolation(Exception):
    """A new request breaks a leave rule. `code` names the rule for clients."""

    code = "leave_rule_violation"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidDateRange(LeaveRuleViolation):
    code = "invalid_date_range"


class IneligibleCategory(LeaveRuleViolation):
    code = "ineligible_category"


class InsufficientBalance(LeaveRuleViolation):
    code = "insufficient_balance"


class OverlappingLeave(LeaveRuleViolation):
    code = "overlapping_leave"


class MissingStationDetails(LeaveRuleViolation):
    code = "missing_station_details"


class InvalidTransition(Exception):
    """`denied` separates "you may not" (403) from "not from this state" (409)."""

    def __init__(self, frm: str, to: str, reason: str = "", *, denied: bool = False):
        super().__init__(f"{frm} -> {to}" + (f": {reason}" if reason else ""))
        self.frm, self.to, self.reason, self.denied = frm, to, reason, denied
