"""Leave tables, split by aggregate.

Institute people are referenced by plain `user_id` integers, never foreign
keys — there is no user table in this database.

Import from `modules.leave.models` as usual; the split is internal.
"""
from modules.leave.models.calendar import (
    Holiday,
    HolidayCalendar,
    VacationPeriod,
)
from modules.leave.models.ledger import (
    EntryReason,
    LedgerEntry,
    YearEndClosure,
)
from modules.leave.models.policy import (  # noqa: F401
    CATEGORY_CHOICES,
    CategoryRule,
    LeavePolicy,
)
from modules.leave.models.request import (  # noqa: F401
    HALF_CHOICES,
    STATE_CHOICES,
    LeaveRequest,
    SubstituteNomination,
)
from modules.leave.models.workflow import (
    AuthorityRule,
    RequestTransition,
    SlaClock,
    SlaRule,
)

__all__ = [
    "AuthorityRule",
    "CategoryRule",
    "EntryReason",
    "Holiday",
    "HolidayCalendar",
    "LeavePolicy",
    "LeaveRequest",
    "LedgerEntry",
    "RequestTransition",
    "SlaClock",
    "SlaRule",
    "SubstituteNomination",
    "VacationPeriod",
    "YearEndClosure",
]
