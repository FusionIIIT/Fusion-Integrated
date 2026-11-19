"""Domain rules and validation constraints for RSPC module.

Pure Python module with no cross-module foreign key dependencies.
Implements business rules from the RSPC specifications:
- BR-RSPC-004: Forward high-value or strategic requests to Director
- BR-RSPC-005: Director approval for large funding requests
- BR-RSPC-006: Director authorization for high-value expenditures
- BR-RSPC-012: Research project proposal approval route
- BR-RSPC-013: Mandatory research proposal fields validation
- BR-RSPC-014: Represented proposal policy validation
- BR-RSPC-015: Timestamp proposal review decisions
- BR-RSPC-016: Record proposal decision remarks
- BR-RSPC-022: Consultancy approval routing
- BR-RSPC-026: Staff appointment approval routing
- BR-RSPC-032: Dean financial approval delegation limit
- BR-RSPC-033: Escalate high-value financial requests to Director
- BR-RSPC-035: Procurement request validation against sanctioned budget
- BR-RSPC-036: Procurement approval hierarchy
- BR-RSPC-043: Project closure archival constraint
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

#: Operation to permission mapping for RBAC enforcement (CFR-RSPC-023, BR-RSPC-048, BR-RSPC-049)
OPERATION_PERMISSIONS: dict[str, str] = {
    "proposal.view": "rspc.proposal.view",
    "proposal.submit": "rspc.proposal.submit",
    "proposal.recommend_hod": "rspc.proposal.recommend_hod",
    "proposal.verify_admin": "rspc.proposal.verify_admin",
    "proposal.approve_dean": "rspc.proposal.approve_dean",
    "proposal.authorize_director": "rspc.proposal.authorize_director",
    "consultancy.view": "rspc.consultancy.view",
    "consultancy.register": "rspc.consultancy.register",
    "consultancy.recommend_hod": "rspc.consultancy.recommend_hod",
    "consultancy.approve_dean": "rspc.consultancy.approve_dean",
    "staff.request": "rspc.staff.request",
    "staff.manage": "rspc.staff.manage",
    "financial.request": "rspc.financial.request",
    "financial.verify": "rspc.financial.verify",
    "financial.approve_dean": "rspc.financial.approve_dean",
    "financial.authorize_director": "rspc.financial.authorize_director",
    "procurement.request": "rspc.procurement.request",
    "procurement.approve": "rspc.procurement.approve",
    "report.submit": "rspc.report.submit",
    "closure.submit": "rspc.closure.submit",
    "closure.approve": "rspc.closure.approve",
    "audit.view": "rspc.audit.view",
}

#: Financial limits and thresholds (configurable defaults)
LARGE_FUNDING_PROPOSAL_THRESHOLD = Decimal("1000000.00")  # >= 10 Lakhs requires Director (BR-RSPC-005)
HIGH_VALUE_EXPENDITURE_THRESHOLD = Decimal("200000.00")   # >= 2 Lakhs requires Director (BR-RSPC-006, BR-RSPC-033)
DEAN_FINANCIAL_DELEGATION_LIMIT = Decimal("200000.00")    # Dean approves within 2 Lakhs (BR-RSPC-032)

#: Research Proposal Status Constants (BR-RSPC-012)
PROPOSAL_STATUS_DRAFT = "DRAFT"
PROPOSAL_STATUS_SUBMITTED_HOD = "SUBMITTED_HOD"
PROPOSAL_STATUS_RECOMMENDED_HOD = "RECOMMENDED_HOD"
PROPOSAL_STATUS_REJECTED_HOD = "REJECTED_HOD"
PROPOSAL_STATUS_VERIFIED_ADMIN = "VERIFIED_ADMIN"
PROPOSAL_STATUS_REJECTED_ADMIN = "REJECTED_ADMIN"
PROPOSAL_STATUS_APPROVED_DEAN = "APPROVED_DEAN"
PROPOSAL_STATUS_REJECTED_DEAN = "REJECTED_DEAN"
PROPOSAL_STATUS_FORWARDED_DIRECTOR = "FORWARDED_DIRECTOR"
PROPOSAL_STATUS_APPROVED_DIRECTOR = "APPROVED_DIRECTOR"
PROPOSAL_STATUS_REJECTED_DIRECTOR = "REJECTED_DIRECTOR"

#: Valid Proposal Statuses
PROPOSAL_STATUS_CHOICES = (
    PROPOSAL_STATUS_DRAFT,
    PROPOSAL_STATUS_SUBMITTED_HOD,
    PROPOSAL_STATUS_RECOMMENDED_HOD,
    PROPOSAL_STATUS_REJECTED_HOD,
    PROPOSAL_STATUS_VERIFIED_ADMIN,
    PROPOSAL_STATUS_REJECTED_ADMIN,
    PROPOSAL_STATUS_APPROVED_DEAN,
    PROPOSAL_STATUS_REJECTED_DEAN,
    PROPOSAL_STATUS_FORWARDED_DIRECTOR,
    PROPOSAL_STATUS_APPROVED_DIRECTOR,
    PROPOSAL_STATUS_REJECTED_DIRECTOR,
)

#: Consultancy Status Constants (BR-RSPC-022)
CONSULTANCY_STATUS_DRAFT = "DRAFT"
CONSULTANCY_STATUS_SUBMITTED_HOD = "SUBMITTED_HOD"
CONSULTANCY_STATUS_RECOMMENDED_HOD = "RECOMMENDED_HOD"
CONSULTANCY_STATUS_VERIFIED_ADMIN = "VERIFIED_ADMIN"
CONSULTANCY_STATUS_APPROVED_DEAN = "APPROVED_DEAN"
CONSULTANCY_STATUS_FORWARDED_DIRECTOR = "FORWARDED_DIRECTOR"
CONSULTANCY_STATUS_APPROVED_DIRECTOR = "APPROVED_DIRECTOR"
CONSULTANCY_STATUS_REJECTED = "REJECTED"

#: Financial Request Status Constants (BR-RSPC-032, BR-RSPC-033)
FINANCIAL_STATUS_SUBMITTED = "SUBMITTED"
FINANCIAL_STATUS_VERIFIED_ADMIN = "VERIFIED_ADMIN"
FINANCIAL_STATUS_APPROVED_DEAN = "APPROVED_DEAN"
FINANCIAL_STATUS_ESCALATED_DIRECTOR = "ESCALATED_DIRECTOR"
FINANCIAL_STATUS_APPROVED_DIRECTOR = "APPROVED_DIRECTOR"
FINANCIAL_STATUS_REJECTED = "REJECTED"

#: Project Closure Status Constants (BR-RSPC-043)
CLOSURE_STATUS_REQUESTED = "REQUESTED"
CLOSURE_STATUS_VERIFIED_ADMIN = "VERIFIED_ADMIN"
CLOSURE_STATUS_APPROVED_DEAN = "APPROVED_DEAN"
CLOSURE_STATUS_FORWARDED_DIRECTOR = "FORWARDED_DIRECTOR"
CLOSURE_STATUS_APPROVED_DIRECTOR = "APPROVED_DIRECTOR"
CLOSURE_STATUS_ARCHIVED = "ARCHIVED"
CLOSURE_STATUS_REJECTED = "REJECTED"


def validate_research_proposal(data: dict[str, Any]) -> list[str]:
    """Validate mandatory fields and constraints for research proposals (BR-RSPC-013, BR-RSPC-014).

    Returns a list of validation error messages. Empty list indicates success.
    """
    errors: list[str] = []

    # Mandatory field checks
    if not data.get("title") or not str(data["title"]).strip():
        errors.append("Proposal title is mandatory.")

    pi_id = data.get("pi_id")
    if pi_id is None or int(pi_id) <= 0:
        errors.append("A valid Principal Investigator (PI) user ID is required.")

    if not data.get("department") or not str(data["department"]).strip():
        errors.append("Department is mandatory.")

    if not data.get("funding_agency") or not str(data["funding_agency"]).strip():
        errors.append("Funding agency name is mandatory.")

    if not data.get("objectives") or not str(data["objectives"]).strip():
        errors.append("Proposal objectives are mandatory.")

    # Budget validation
    budget = data.get("budget")
    if budget is None:
        errors.append("Project budget is mandatory.")
    else:
        try:
            budget_val = Decimal(str(budget))
            if budget_val <= Decimal("0"):
                errors.append("Project budget must be greater than zero.")
        except Exception:
            errors.append("Invalid budget format.")

    # Dates validation
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    if not start_date or not end_date:
        errors.append("Both start date and end date are mandatory.")
    else:
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)
        if end_date <= start_date:
            errors.append("End date must be strictly after the start date.")

    return errors


def validate_consultancy_project(data: dict[str, Any]) -> list[str]:
    """Validate consultancy project registration data (CFR-RSPC-009, BR-RSPC-022)."""
    errors: list[str] = []

    if not data.get("title") or not str(data["title"]).strip():
        errors.append("Consultancy project title is mandatory.")

    pi_id = data.get("pi_id")
    if pi_id is None or int(pi_id) <= 0:
        errors.append("A valid Faculty Consultant user ID is required.")

    if not data.get("client_name") or not str(data["client_name"]).strip():
        errors.append("Client name is mandatory.")

    if not data.get("scope_of_work") or not str(data["scope_of_work"]).strip():
        errors.append("Scope of work is mandatory.")

    if not data.get("deliverables") or not str(data["deliverables"]).strip():
        errors.append("Deliverables specification is mandatory.")

    total_cost = data.get("total_cost")
    if total_cost is None:
        errors.append("Total cost is mandatory.")
    else:
        try:
            cost_val = Decimal(str(total_cost))
            if cost_val <= Decimal("0"):
                errors.append("Total cost must be greater than zero.")
        except Exception:
            errors.append("Invalid total cost format.")

    return errors


def is_director_approval_required(
    entity_type: str,
    amount: Decimal | float,
    is_strategic: bool = False,
) -> bool:
    """Determine whether Director review/approval is required (BR-RSPC-004, BR-RSPC-005, BR-RSPC-006)."""
    val = Decimal(str(amount))
    if is_strategic:
        return True

    if entity_type == "proposal":
        return val >= LARGE_FUNDING_PROPOSAL_THRESHOLD
    elif entity_type in ("financial", "expenditure"):
        return val >= HIGH_VALUE_EXPENDITURE_THRESHOLD
    elif entity_type == "procurement":
        return val >= HIGH_VALUE_EXPENDITURE_THRESHOLD

    return False


def validate_financial_request(
    amount: Decimal | float,
    available_budget: Decimal | float,
) -> list[str]:
    """Validate fund-utilization/expenditure request against available budget (BR-RSPC-032)."""
    errors: list[str] = []
    amt = Decimal(str(amount))
    avail = Decimal(str(available_budget))

    if amt <= Decimal("0"):
        errors.append("Requested financial amount must be positive.")
    if amt > avail:
        errors.append(f"Requested amount ({amt}) exceeds available sanctioned budget ({avail}).")

    return errors


def validate_procurement_request(
    estimated_cost: Decimal | float,
    available_budget: Decimal | float,
) -> list[str]:
    """Validate procurement request against available equipment/consumable budget (BR-RSPC-035)."""
    errors: list[str] = []
    cost = Decimal(str(estimated_cost))
    avail = Decimal(str(available_budget))

    if cost <= Decimal("0"):
        errors.append("Estimated procurement cost must be positive.")
    if cost > avail:
        errors.append(f"Estimated procurement cost ({cost}) exceeds available budget ({avail}).")

    return errors


def validate_project_closure(
    financial_settled: bool,
    has_asset_declaration: bool,
) -> list[str]:
    """Validate closure requirements prior to project archival (BR-RSPC-043, CFR-RSPC-020)."""
    errors: list[str] = []
    if not financial_settled:
        errors.append("Project cannot be closed: financial settlement is pending.")
    if not has_asset_declaration:
        errors.append("Project closure requires a completed asset declaration record.")
    return errors
