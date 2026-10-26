"""The configured policy as plain values, and what every revision must pass (BR-EL-030)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from modules.leave.domain import categories as cat

REQUIRED, OPTIONAL, NONE = "required", "optional", "none"
SUBSTITUTE_POLICIES = (REQUIRED, OPTIONAL, NONE)

#: The baseline's own numbers (PS §3), used to seed a fresh installation.
BASELINE_ENTITLEMENTS = {
    cat.CL: Decimal(8), cat.RH: Decimal(2), cat.SCL: Decimal(15),
    cat.EL: Decimal(30), cat.COL: Decimal(20), cat.VL: Decimal(60),
}


class PolicyInvalid(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class CategoryRule:
    category: str
    annual_entitlement: Decimal
    substitute: str = OPTIONAL
    #: BR-EL-009: at or above this many days an evidence reference is required; None never.
    evidence_min_days: Decimal | None = None


@dataclass(frozen=True)
class Policy:
    rules: dict[str, CategoryRule]
    #: Python weekday numbers, Monday = 0.
    weekend_days: frozenset[int] = frozenset({5, 6})
    max_backdate_days: int = 0
    revision_id: int | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def rule(self, category: str) -> CategoryRule:
        return self.rules[category]


def baseline() -> Policy:
    rules = {c: CategoryRule(c, BASELINE_ENTITLEMENTS[c]) for c in cat.ALL}
    rules[cat.COL] = CategoryRule(cat.COL, BASELINE_ENTITLEMENTS[cat.COL],
                                  evidence_min_days=Decimal(3))
    return Policy(rules=rules)


def validate(policy: Policy) -> None:
    """Raise PolicyInvalid naming every problem, so one save reports them all."""
    problems: list[str] = []
    missing = [c for c in cat.ALL if c not in policy.rules]
    if missing:
        problems.append(f"Every category needs a rule; missing: {', '.join(missing)}.")
    for code, rule in policy.rules.items():
        if code not in cat.CATEGORIES:
            problems.append(f"{code} is not a leave category.")
            continue
        if rule.annual_entitlement < 0:
            problems.append(f"{code}: the annual entitlement cannot be negative.")
        if rule.annual_entitlement > 366:
            problems.append(f"{code}: an annual entitlement above 366 days is not credible.")
        if rule.annual_entitlement % Decimal("0.5"):
            problems.append(f"{code}: the entitlement must be a whole or half day.")
        if rule.substitute not in SUBSTITUTE_POLICIES:
            problems.append(f"{code}: substitute must be one of {', '.join(SUBSTITUTE_POLICIES)}.")
        if rule.evidence_min_days is not None and rule.evidence_min_days <= 0:
            problems.append(f"{code}: the evidence threshold must be at least half a day.")
    if not policy.weekend_days <= set(range(7)):
        problems.append("Weekend days must be weekday numbers 0 (Monday) to 6 (Sunday).")
    if len(policy.weekend_days) > 3:
        problems.append("More than three weekend days a week is not credible.")
    if not 0 <= policy.max_backdate_days <= 30:
        problems.append("Back-dating must be between 0 and 30 days.")
    if problems:
        raise PolicyInvalid(problems)
