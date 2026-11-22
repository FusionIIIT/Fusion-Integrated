"""Domain entities and value objects for RSPC (pure Python)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class ProposalStatusString(str):
    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if not isinstance(other, str):
            return False
        if str(self) == other:
            return True
        if str(self) == "Department Not Recommended" and other == "rejected":
            return True
        if str(self) == "rejected" and other == "Department Not Recommended":
            return True
        if str(self) == "Dean Not Approved" and other == "rejected":
            return True
        return bool(str(self) == "rejected" and other == "Dean Not Approved")


class ProposalStatus:
    DRAFT = "draft"
    SUBMITTED_HOD = "submitted_hod"
    ENDORSED_HOD = "endorsed_hod"
    REVISION_REQUESTED = "revision_requested"
    APPROVED_DEAN = "approved_dean"
    REJECTED = "rejected"
    DEPT_NOT_RECOMMENDED = ProposalStatusString("Department Not Recommended")
    DEAN_NOT_APPROVED = ProposalStatusString("Dean Not Approved")


class ProjectStatus:
    SANCTIONED = "sanctioned"
    ACTIVE = "active"
    EXTENSION_REQUESTED = "extension_requested"
    CLOSURE_PENDING = "closure_pending"
    CLOSED = "closed"
    TERMINATED = "terminated"


class TransactionType:
    ALLOCATION = "allocation"
    DISBURSEMENT = "disbursement"
    REVERSAL = "reversal"


class BudgetHeadType:
    EQUIPMENT = "equipment"
    CONSUMABLES = "consumables"
    MANPOWER = "manpower"
    TRAVEL = "travel"
    CONTINGENCY = "contingency"
    OVERHEADS = "overheads"

    ALL_HEADS = (EQUIPMENT, CONSUMABLES, MANPOWER, TRAVEL, CONTINGENCY, OVERHEADS)


@dataclass(frozen=True)
class BudgetHeadEntity:
    head_type: str
    allocated_amount: Decimal
    spent_amount: Decimal
    committed_amount: Decimal = Decimal("0.00")
    id: int | None = None

    @property
    def available_balance(self) -> Decimal:
        return self.allocated_amount - self.spent_amount - self.committed_amount


@dataclass(frozen=True)
class ProposalEntity:
    id: int | None
    proposal_type: str
    title: str
    pi_user_id: int
    department: str
    funding_agency: str
    proposed_budget: Decimal
    overhead_amount: Decimal
    status: str


@dataclass(frozen=True)
class ProjectEntity:
    id: int | None
    project_code: str
    project_type: str
    title: str
    pi_user_id: int
    department: str
    funding_agency: str
    sanctioned_amount: Decimal
    status: str
