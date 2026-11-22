from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PolicySpec:
    director_review_days: int = 15
    revision_resubmission_days: int = 60
    cost_escalation_threshold: Decimal | None = None
    max_attorney_workload: int | None = None
    max_document_size_bytes: int = 52_428_800
    withdrawal_eligible_states: tuple[str, ...] = ()

    def is_withdrawal_permitted(self, current_status: str) -> bool:
        return current_status in self.withdrawal_eligible_states

    def is_cost_escalation_triggered(self, total_cost: Decimal) -> bool:
        if self.cost_escalation_threshold is None:
            return False
        return total_cost > self.cost_escalation_threshold

    def is_attorney_workload_exceeded(self, current_workload: int) -> bool:
        if self.max_attorney_workload is None:
            return False
        return current_workload >= self.max_attorney_workload
