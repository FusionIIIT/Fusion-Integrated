"""Final bill submission, Auditor validation, Director approval, and Accounts settlement."""

from decimal import Decimal

from django.utils import timezone

from modules.iwd.domain.state_machine import get_next_state
from modules.iwd.models import Complaint, DecisionAuditTrail, FinalBill


class UnverifiedBillSubmissionError(Exception):
    """Raised when a final bill is submitted before successful physical verification."""


def submit_final_bill(
    complaint_id: int, engineer_user_id: int, total_amount: Decimal | float | int | str
) -> FinalBill:
    """Submit final bill packet guarded by prior physical verification (BR-IWD-014)."""
    complaint = Complaint.objects.get(id=complaint_id)
    if not complaint.is_resolved:
        msg = "BR-IWD-014: Complaint must be verified and resolved before final billing."
        raise UnverifiedBillSubmissionError(msg)

    amount = Decimal(str(total_amount))
    bill = FinalBill.objects.create(
        complaint=complaint,
        engineer_user_id=engineer_user_id,
        total_amount=amount,
        auditor_status="Pending",
    )

    prev = complaint.status
    complaint.status = get_next_state(prev, "submit_bill", "iwd_engineer")
    complaint.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=engineer_user_id,
        actor_role="iwd_engineer",
        action="submit_final_bill",
        previous_state=prev,
        new_state=complaint.status,
        remarks=f"Final bill submitted: Rs.{amount}",
    )
    return bill


def audit_bill(
    complaint_id: int, auditor_user_id: int, outcome: str, remarks: str = ""
) -> FinalBill:
    """Auditor validates bill against approved estimate (UC-IWD-121, BR-IWD-015)."""
    complaint = Complaint.objects.get(id=complaint_id)
    bill = complaint.final_bills.latest("created_at")

    action = "audit_validate" if outcome == "Validated" else "audit_query"
    prev = complaint.status
    complaint.status = get_next_state(prev, action, "iwd_auditor")
    complaint.save()

    bill.auditor_status = outcome
    bill.auditor_remarks = remarks
    bill.audited_at = timezone.now()
    bill.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=auditor_user_id,
        actor_role="iwd_auditor",
        action=f"audit_{outcome.lower()}",
        previous_state=prev,
        new_state=complaint.status,
        remarks=remarks,
    )
    return bill


def approve_payment(complaint_id: int, director_user_id: int) -> FinalBill:
    """Director grants final payment approval following validation (BR-IWD-016)."""
    complaint = Complaint.objects.get(id=complaint_id)
    bill = complaint.final_bills.latest("created_at")

    prev = complaint.status
    complaint.status = get_next_state(prev, "director_approve_payment", "iwd_director")
    complaint.save()

    bill.director_approved = True
    bill.director_approved_at = timezone.now()
    bill.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=director_user_id,
        actor_role="iwd_director",
        action="director_approve_payment",
        previous_state=prev,
        new_state=complaint.status,
        remarks="Payment approved for Accounts settlement",
    )
    return bill


def settle_payment(
    complaint_id: int, accounts_user_id: int, settlement_reference: str
) -> FinalBill:
    """Accounts Department records disbursement and settles payment (BR-IWD-016)."""
    complaint = Complaint.objects.get(id=complaint_id)
    bill = complaint.final_bills.latest("created_at")

    prev = complaint.status
    complaint.status = get_next_state(prev, "accounts_settle", "iwd_accounts")
    complaint.save()

    bill.settled = True
    bill.settled_at = timezone.now()
    bill.settlement_reference = settlement_reference
    bill.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=accounts_user_id,
        actor_role="iwd_accounts",
        action="accounts_settle",
        previous_state=prev,
        new_state=complaint.status,
        remarks=f"Settlement reference: {settlement_reference}",
    )
    return bill
