"""The current configured policy, as the domain sees it (BR-EL-030).

A frozen dataclass, built from the database row by the service layer, so every
rule reads the same values and the domain imports no Django. Entitlement
figures live here rather than in code because the specification states them as
policy parameters an administrator maintains (CFR-EL-024).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from modules.leave.domain import categories as cat

#: Default entitlement figures, from the business rules. Each cites its rule.
DEFAULT_CASUAL_DAYS = Decimal("8")            # BR-EL-002
DEFAULT_RESTRICTED_HOLIDAY_DAYS = Decimal("2")  # BR-EL-003
DEFAULT_SPECIAL_CASUAL_DAYS = Decimal("15")   # BR-EL-004
DEFAULT_EARNED_DAYS = Decimal("30")           # BR-EL-005
DEFAULT_VACATION_DAYS = Decimal("60")         # BR-EL-006
DEFAULT_COMMUTED_DAYS = Decimal("20")         # BR-EL-009
DEFAULT_VACATION_TO_EARNED_RATIO = Decimal("2")  # BR-EL-007, 2 VL : 1 EL


@dataclass(frozen=True)
class Policy:
    casual_days: Decimal = DEFAULT_CASUAL_DAYS
    restricted_holiday_days: Decimal = DEFAULT_RESTRICTED_HOLIDAY_DAYS
    special_casual_days: Decimal = DEFAULT_SPECIAL_CASUAL_DAYS
    earned_days: Decimal = DEFAULT_EARNED_DAYS
    vacation_days: Decimal = DEFAULT_VACATION_DAYS
    commuted_days: Decimal = DEFAULT_COMMUTED_DAYS
    #: Vacation days consumed per earned day credited at year end (BR-EL-007).
    vacation_to_earned_ratio: Decimal = DEFAULT_VACATION_TO_EARNED_RATIO
    #: BR-EL-002/003/004 lapse unused; BR-EL-005/009 carry forward.
    earned_carries_forward: bool = True
    commuted_carries_forward: bool = True
    #: The specification states carry-forward but names no cap, so there is none
    #: until an administrator sets one.
    earned_carry_forward_cap: Decimal | None = None
    commuted_carry_forward_cap: Decimal | None = None
    #: Month the year-end boundary falls in; BR-EL-004 says "calendar year".
    year_end_month: int = 12
    #: Categories whose applications need a nominated substitute (BR-EL-014).
    substitute_required_for: frozenset[str] = field(default_factory=frozenset)
    #: Whether the optional Establishment step runs (BR-EL-019).
    establishment_step_enabled: bool = False
    #: Which employee kinds may apply for each category (BR-EL-005, BR-EL-006).
    category_kinds: dict[str, frozenset[str]] = field(default_factory=lambda: {
        cat.CASUAL: frozenset(cat.EMPLOYEE_KINDS),
        cat.RESTRICTED_HOLIDAY: frozenset(cat.EMPLOYEE_KINDS),
        cat.SPECIAL_CASUAL: frozenset(cat.EMPLOYEE_KINDS),
        cat.EARNED: frozenset({cat.STAFF}),
        cat.COMMUTED: frozenset(cat.EMPLOYEE_KINDS),
        cat.VACATION: frozenset({cat.FACULTY}),
    })

    def annual_entitlement(self, category: str) -> Decimal:
        return {
            cat.CASUAL: self.casual_days,
            cat.RESTRICTED_HOLIDAY: self.restricted_holiday_days,
            cat.SPECIAL_CASUAL: self.special_casual_days,
            cat.EARNED: self.earned_days,
            cat.COMMUTED: self.commuted_days,
            cat.VACATION: self.vacation_days,
        }[category]

    def carry_forward_cap(self, category: str) -> Decimal | None:
        if category == cat.EARNED:
            return self.earned_carry_forward_cap
        if category == cat.COMMUTED:
            return self.commuted_carry_forward_cap
        return None

    def carries_forward(self, category: str) -> bool:
        """Vacation leave never carries forward; it converts (BR-EL-007)."""
        if category == cat.VACATION:
            return False
        if category == cat.EARNED:
            return self.earned_carries_forward
        if category == cat.COMMUTED:
            return self.commuted_carries_forward
        return False

    def substitute_required(self, category: str) -> bool:
        return category in self.substitute_required_for

    def kinds_permitted(self, category: str) -> frozenset[str]:
        return self.category_kinds.get(category, frozenset(cat.EMPLOYEE_KINDS))