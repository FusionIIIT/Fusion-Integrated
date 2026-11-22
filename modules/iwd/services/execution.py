from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from modules.iwd.domain.state_machine import transition
from modules.iwd.models.complaint import Complaint
from modules.iwd.models.completion import (
    ComplaintFeedback,
    FinalBill,
    PhysicalVerification,
)
from modules.iwd.services.audit import record_audit_trail


def complete_repair_work(
    complaint: Complaint,
    engineer_id: int,
) -> Complaint:
    """Engineer marks repair work complete."""
    if complaint.assigned_engineer_id != engineer_id:
        raise ValidationError("Only assigned engineer can mark work complete.")

    with transaction.atomic():
        outcome = transition(complaint.status, "complete_work", "engineer")
        if not outcome.allowed:
            raise ValidationError(outcome.reason)

        old_state = complaint.status
        complaint.status = outcome.next_state
        complaint.save(update_fields=["status", "updated_at"])

        record_audit_trail(
            complaint=complaint,
            actor_user_id=engineer_id,
            acting_role="engineer",
            action="complete_work",
            from_state=old_state,
            to_state=complaint.status,
            decision_reason="Work completed, awaiting physical verification",
        )

        return complaint


def record_physical_verification(
    complaint: Complaint,
    dept_head_user_id: int,
    approve: bool,
    remarks: str,
    rework_notes: str = "",
) -> PhysicalVerification:
    """Department Head verifies work before resolution (BR-IWD-014)."""
    event = "verify_approved" if approve else "verify_rework"

    with transaction.atomic():
        outcome = transition(complaint.status, event, "department_head")
        if not outcome.allowed:
            raise ValidationError(outcome.reason)

        verif, _ = PhysicalVerification.objects.update_or_create(
            complaint=complaint,
            defaults={
                "verified_by_user_id": dept_head_user_id,
                "is_approved": approve,
                "verification_remarks": remarks,
                "rework_notes": rework_notes if not approve else "",
            },
        )

        old_state = complaint.status
        complaint.status = outcome.next_state
        complaint.save(update_fields=["status", "updated_at"])

        record_audit_trail(
            complaint=complaint,
            actor_user_id=dept_head_user_id,
            acting_role="department_head",
            action=event,
            from_state=old_state,
            to_state=complaint.status,
            decision_reason=remarks if approve else rework_notes,
        )

        return verif


def submit_final_bill(
    complaint: Complaint,
    engineer_id: int,
    invoice_number: str,
    claimed_amount: Decimal,
) -> FinalBill:
    """Submits final bill after physical verification resolution."""
    if complaint.assigned_engineer_id != engineer_id:
        raise ValidationError("Only assigned engineer can submit final bill.")

    with transaction.atomic():
        outcome = transition(complaint.status, "submit_final_bill", "engineer")
        if not outcome.allowed:
            raise ValidationError(outcome.reason)

        bill = FinalBill.objects.create(
            complaint=complaint,
            engineer_id=engineer_id,
            invoice_number=invoice_number,
            claimed_amount=claimed_amount,
        )

        old_state = complaint.status
        complaint.status = outcome.next_state
        complaint.save(update_fields=["status", "updated_at"])

        record_audit_trail(
            complaint=complaint,
            actor_user_id=engineer_id,
            acting_role="engineer",
            action="submit_final_bill",
            from_state=old_state,
            to_state=complaint.status,
            decision_reason=f"Invoice {invoice_number} for {claimed_amount}",
        )

        return bill


def audit_final_bill(
    bill: FinalBill,
    auditor_user_id: int,
    remarks: str,
) -> FinalBill:
    """Auditor validates final bill against estimate (BR-IWD-015)."""
    complaint = bill.complaint

    with transaction.atomic():
        outcome = transition(complaint.status, "audit_validated", "auditor")
        if not outcome.allowed:
            raise ValidationError(outcome.reason)

        bill.is_audited = True
        bill.auditor_user_id = auditor_user_id
        bill.audit_remarks = remarks
        bill.audit_timestamp = timezone.now()
        bill.save(update_fields=["is_audited", "auditor_user_id", "audit_remarks", "audit_timestamp"])

        old_state = complaint.status
        complaint.status = outcome.next_state
        complaint.save(update_fields=["status", "updated_at"])

        record_audit_trail(
            complaint=complaint,
            actor_user_id=auditor_user_id,
            acting_role="auditor",
            action="audit_validated",
            from_state=old_state,
            to_state=complaint.status,
            decision_reason=remarks,
        )

        return bill


def settle_payment(
    bill: FinalBill,
    user_id: int,
    role: str,  # 'director' or 'accounts'
    accounts_ref: str = "",
) -> FinalBill:
    """Director payment approval and Accounts settlement sequence (BR-IWD-016)."""
    complaint = bill.complaint

    with transaction.atomic():
        if role == "director":
            outcome = transition(complaint.status, "approve_payment", "director")
            if not outcome.allowed:
                raise ValidationError(outcome.reason)

            bill.director_approved = True
            bill.director_user_id = user_id
            bill.director_approved_at = timezone.now()
            bill.save(update_fields=["director_approved", "director_user_id", "director_approved_at"])

            action_name = "director_approved_payment"
        else:
            outcome = transition(complaint.status, "record_settlement", "accounts")
            if not outcome.allowed:
                raise ValidationError(outcome.reason)

            bill.settlement_status = "settled"
            bill.accounts_reference = accounts_ref
            bill.settled_at = timezone.now()
            bill.save(update_fields=["settlement_status", "accounts_reference", "settled_at"])

            action_name = "accounts_settled_payment"

        old_state = complaint.status
        complaint.status = outcome.next_state
        complaint.save(update_fields=["status", "updated_at"])

        record_audit_trail(
            complaint=complaint,
            actor_user_id=user_id,
            acting_role=role,
            action=action_name,
            from_state=old_state,
            to_state=complaint.status,
            decision_reason=accounts_ref or "Payment approved/settled",
        )

        return bill


def submit_feedback(
    complaint: Complaint,
    user_id: int,
    rating: int,
    feedback_text: str = "",
    post_repair_issue: str = "",
) -> ComplaintFeedback:
    """Submits rating and post-repair feedback after resolution (BR-IWD-017)."""
    if complaint.complainant_user_id != user_id:
        raise ValidationError("Only the original complainant can submit feedback.")
    if complaint.status not in ["resolved", "audit_pending", "director_payment_approval_pending", "accounts_settlement_pending", "settled"]:
        raise ValidationError("Feedback can only be submitted after complaint resolution.")

    feedback, _ = ComplaintFeedback.objects.update_or_create(
        complaint=complaint,
        defaults={
            "user_id": user_id,
            "rating": rating,
            "feedback_text": feedback_text,
            "post_repair_issue": post_repair_issue,
        },
    )
    return feedback
