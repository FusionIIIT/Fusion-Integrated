from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FilingClearance:
    cleared: bool
    reasons: tuple[str, ...] = ()

    @property
    def message(self) -> str:
        if self.cleared:
            return "Application cleared for external filing."
        return "Filing blocked: " + "; ".join(self.reasons)


def evaluate_filing_clearance(
    *,
    has_inventor_agreements: bool,
    has_budget_approval: bool,
    has_format_compliance: bool,
) -> FilingClearance:
    reasons: list[str] = []
    if not has_inventor_agreements:
        reasons.append("Inventor agreements must be completed (BR-PMS-020, 078)")
    if not has_budget_approval:
        reasons.append("Filing and prosecution budget must be approved (BR-PMS-128)")
    if not has_format_compliance:
        reasons.append("Filing package must satisfy patent-office format standards (BR-PMS-055)")

    return FilingClearance(cleared=len(reasons) == 0, reasons=tuple(reasons))
