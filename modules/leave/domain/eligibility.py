"""Leave eligibility rules.

Pure Python domain logic following BR-EL-001 through BR-EL-015.
No Django/DRF imports here.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LeaveEligibilityResult:
    """Result of leave eligibility check."""
    is_eligible: bool
    category: str | None = None
    reason: str | None = None
    available_days: float = 0.0


class EligibilityRules:
    """Business rules for leave eligibility."""

    # BR-EL-001: Supported leave-category eligibility
    SUPPORTED_CATEGORIES = {"CL", "RH", "SCL", "EL", "COL", "VL"}

    # BR-EL-002: Casual Leave entitlement and lapse
    CL_ENTITLEMENT = 8
    CL_LAPSE = True  # Unused CL lapses at year end

    # BR-EL-003: Restricted Holiday entitlement and applicability
    RH_ENTITLEMENT = 2
    RH_LAPSE = True  # Unused RH lapses at year end

    # BR-EL-004: Special Casual Leave entitlement and admissibility
    SCL_ENTITLEMENT = 15
    SCL_ADMISSIBLE = True  # Requires specific authority

    # BR-EL-005: Non-faculty Earned Leave credit and carry-forward
    EL_CARRY_FORWARD = True  # EL can carry forward

    # BR-EL-006: Faculty Vacation Leave entitlement
    VL_CARRY_FORWARD = True  # VL can carry forward

    # BR-EL-007: VL-to-EL year-end conversion
    VL_TO_EL_CONVERSION = True

    # BR-EL-008: Treatment of EL created by VL conversion
    EL_FROM_VL_IS_EL = True

    # BR-EL-009: Commuted Leave entitlement and treatment
    COL_CARRY_FORWARD = True

    def __init__(self, leave_balances):
        """Initialize with leave balance data."""
        self.leave_balances = leave_balances

    def is_category_supported(self, category: str) -> tuple[bool, str]:
        """BR-EL-001: Check if leave category is supported."""
        if category not in self.SUPPORTED_CATEGORIES:
            return False, f"Category {category} is not supported. Supported: {self.SUPPORTED_CATEGORIES}"
        return True, None

    def get_entitlement(self, category: str, year: int, kind: str) -> tuple[float, str]:
        """Get leave entitlement for a category."""
        if category == "CL":
            return self.CL_ENTITLEMENT, "Casual Leave"
        if category == "RH":
            return self.RH_ENTITLEMENT, "Restricted Holiday"
        if category == "SCL":
            return self.SCL_ENTITLEMENT, "Special Casual Leave"
        if category == "EL":
            return self.EL_CARRY_FORWARD, "Earned Leave"
        if category == "COL":
            return self.COL_CARRY_FORWARD, "Commuted Leave"
        if category == "VL":
            return self.VL_CARRY_FORWARD, "Vacation Leave"
        return 0, "Unknown"

    def check_balance(self, user_id: int, category: str, year: int, kind: str) -> LeaveEligibilityResult:
        """Check if user has sufficient leave balance."""
        if category not in self.SUPPORTED_CATEGORIES:
            return LeaveEligibilityResult(
                is_eligible=False,
                reason=f"Category {category} is not supported.",
                category=category
            )

        # Get balance for this year
        balance = self.leave_balances.get((kind, category, year))
        if not balance:
            return LeaveEligibilityResult(
                is_eligible=False,
                reason=f"No leave balance record found for {kind}/{category}/{year}",
                category=category
            )

        available = balance.available
        requested = self._calculate_duration(category, year, user_id, kind)

        if available < requested:
            return LeaveEligibilityResult(
                is_eligible=False,
                reason=f"Insufficient balance: {available:.2f} available, {requested:.2f} requested",
                category=category
            )

        return LeaveEligibilityResult(
            is_eligible=True,
            category=category,
            available_days=available
        )

    def _calculate_duration(self, category: str, year: int, user_id: int, kind: str) -> float:
        """Calculate requested duration based on category rules."""
        # This would normally be calculated from start_date and end_date
        # For now, return a placeholder
        return 1.0

    def check_scl_authority(self, user_id: int, kind: str) -> tuple[bool, str]:
        """BR-EL-004: Check if user has authority for SCL."""
        if kind == "faculty":
            return True, "Faculty has SCL authority"
        if kind == "staff":
            return False, "Staff does not have SCL authority"
        return False, "Unknown employee kind"

    def check_eligibility(self, user_id: int, category: str, year: int, kind: str) -> LeaveEligibilityResult:
        """Complete eligibility check."""
        # Check category support
        is_supported, error = self.is_category_supported(category)
        if not is_supported:
            return LeaveEligibilityResult(
                is_eligible=False,
                reason=error,
                category=category
            )

        # Check authority for SCL
        if category == "SCL":
            has_authority, authority_error = self.check_scl_authority(user_id, kind)
            if not has_authority:
                return LeaveEligibilityResult(
                    is_eligible=False,
                    reason=authority_error,
                    category=category
                )

        # Check balance
        return self.check_balance(user_id, category, year, kind)


def calculate_available_cl(kind: str, year: int) -> float:
    """BR-EL-002: Calculate available CL."""
    from modules.leave.domain import eligibility as el

    # In production, this would query the database
    return el.ELIGIBILITY_RULES.CL_ENTITLEMENT


def calculate_available_rh(kind: str, year: int) -> float:
    """BR-EL-003: Calculate available RH."""
    from modules.leave.domain import eligibility as el

    return el.ELIGIBILITY_RULES.RH_ENTITLEMENT


def calculate_available_scl(kind: str, year: int) -> float:
    """BR-EL-004: Calculate available SCL."""
    from modules.leave.domain import eligibility as el

    return el.ELIGIBILITY_RULES.SCL_ENTITLEMENT


# Access the rules instance (would be initialized from database in production)
ELIGIBILITY_RULES = None


def get_eligibility_rules() -> EligibilityRules:
    """Get the eligibility rules instance."""
    global ELIGIBILITY_RULES
    if ELIGIBILITY_RULES is None:
        # In production, query the database
        ELIGIBILITY_RULES = EligibilityRules({})
    return ELIGIBILITY_RULES


def check_leave_eligibility(user_id: int, category: str, year: int, kind: str) -> LeaveEligibilityResult:
    """Check leave eligibility for a user."""
    return get_eligibility_rules().check_eligibility(user_id, category, year, kind)


def can_take_leave(user_id: int, category: str, year: int, kind: str) -> bool:
    """Check if user can take leave."""
    result = check_leave_eligibility(user_id, category, year, kind)
    return result.is_eligible
