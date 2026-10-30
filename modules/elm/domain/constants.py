"""Domain constants for Employee Leave Management."""
from decimal import Decimal

# Leave Categories
CL = "CL"       # Casual Leave (8 days/year, 0.5 half day)
RH = "RH"       # Restricted Holiday (2 days/year)
SCL = "SCL"     # Special Casual Leave (up to 15 days/year)
EL = "EL"       # Earned Leave (30 days/year for staff, carries forward)
VL = "VL"       # Vacation Leave (60 days/year for faculty, converts to EL 2:1)
COL = "COL"     # Commuted / Medical Leave (20 days/year, carries forward)

LEAVE_CATEGORIES = (CL, RH, SCL, EL, VL, COL)

# Continuous count leave categories (weekends and holidays count as leave days)
CONTINUOUS_COUNT_CATEGORIES = frozenset({EL, COL, VL})

# Non-continuous count categories (weekends and closed holidays do NOT count)
DISCRETE_COUNT_CATEGORIES = frozenset({CL, SCL, RH})

# Categories where unused balance lapses at year-end
LAPSE_AT_YEAR_END = frozenset({CL, RH, SCL})

# Default annual entitlements
DEFAULT_ENTITLEMENTS = {
    CL: Decimal("8.0"),
    RH: Decimal("2.0"),
    SCL: Decimal("15.0"),
    EL: Decimal("30.0"),  # For non-faculty
    VL: Decimal("60.0"),  # For faculty
    COL: Decimal("20.0"),
}

# Half day types for Casual Leave
HALF_DAY_FIRST = "first_half"
HALF_DAY_SECOND = "second_half"
HALF_DAY_NONE = ""

# Application Statuses
STATUS_PENDING_SUBSTITUTE = "pending_substitute"
STATUS_SUBSTITUTE_DECLINED = "substitute_declined"
STATUS_PENDING_UNIT_HEAD = "pending_unit_head"
STATUS_PENDING_HIGHER_SANCTION = "pending_higher_sanction"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_WITHDRAWN = "withdrawn"
STATUS_CANCELLATION_REQUESTED = "cancellation_requested"
STATUS_CANCELLED = "cancelled"
STATUS_RESUMED = "resumed"

TERMINAL_STATUSES = frozenset({STATUS_REJECTED, STATUS_WITHDRAWN, STATUS_CANCELLED, STATUS_RESUMED})
ACTIVE_IN_FLIGHT_STATUSES = frozenset({
    STATUS_PENDING_SUBSTITUTE,
    STATUS_SUBSTITUTE_DECLINED,
    STATUS_PENDING_UNIT_HEAD,
    STATUS_PENDING_HIGHER_SANCTION,
})

# Substitute Response
SUBSTITUTE_PENDING = "pending"
SUBSTITUTE_ACCEPTED = "accepted"
SUBSTITUTE_DECLINED = "declined"

# Unit Head Recommendation
RECOMMENDATION_RECOMMENDED = "recommended"
RECOMMENDATION_NOT_RECOMMENDED = "not_recommended"

# Decisions
DECISION_APPROVED = "approved"
DECISION_REJECTED = "rejected"
