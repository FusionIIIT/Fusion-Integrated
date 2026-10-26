"""Leave policy parameters and their validation (BR-EL-001..009, BR-EL-030)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from modules.elm.domain import categories as c


class PolicyInvalid(Exception):
    pass


class NotEligible(Exception):
    pass


#: The canonical case stated by the spec; seeded as the first published version.
DEFAULT_PARAMS: dict = {
    "annual_credit": {
        c.FACULTY: {c.CL: 8, c.RH: 2, c.SCL: 15, c.EL: 0, c.COL: 20, c.VL: 60},
        c.STAFF: {c.CL: 8, c.RH: 2, c.SCL: 15, c.EL: 30, c.COL: 20, c.VL: 0},
    },
    "eligible": {
        c.FACULTY: [c.CL, c.RH, c.SCL, c.EL, c.COL, c.VL],
        c.STAFF: [c.CL, c.RH, c.SCL, c.EL, c.COL],
    },
    "vl_to_el_ratio": 2,
    "col_requires_medical_evidence": True,
}


@dataclass(frozen=True)
class Policy:
    annual_credit: dict
    eligible: dict
    vl_to_el_ratio: Decimal
    col_requires_medical_evidence: bool

    def annual_credit_for(self, kind: str, category: str) -> Decimal:
        return Decimal(str(self.annual_credit.get(kind, {}).get(category, 0)))

    def check_eligible(self, kind: str, category: str) -> None:
        if category not in self.eligible.get(kind, []):
            raise NotEligible(
                f"{c.LABELS.get(category, category)} is not available to "
                f"{kind or 'your'} employees under the current leave policy.")


def parse(params: dict) -> Policy:
    if not isinstance(params, dict):
        raise PolicyInvalid("Policy parameters must be an object.")
    credit = params.get("annual_credit")
    eligible = params.get("eligible")
    if not isinstance(credit, dict) or not isinstance(eligible, dict):
        raise PolicyInvalid("Policy needs both annual_credit and eligible.")
    for kind in c.EMPLOYEE_KINDS:
        for cat, n in (credit.get(kind) or {}).items():
            if cat not in c.ALL:
                raise PolicyInvalid(f"Unknown leave category {cat!r}.")
            try:
                if Decimal(str(n)) < 0:
                    raise PolicyInvalid(f"{kind} {cat} credit cannot be negative.")
            except ArithmeticError as exc:
                raise PolicyInvalid(f"{kind} {cat} credit must be a number.") from exc
        for cat in eligible.get(kind) or []:
            if cat not in c.ALL:
                raise PolicyInvalid(f"Unknown leave category {cat!r}.")
    ratio = Decimal(str(params.get("vl_to_el_ratio", 2)))
    if ratio <= 0:
        raise PolicyInvalid("vl_to_el_ratio must be positive.")
    return Policy(
        annual_credit=credit, eligible=eligible, vl_to_el_ratio=ratio,
        col_requires_medical_evidence=bool(
            params.get("col_requires_medical_evidence", True)),
    )
