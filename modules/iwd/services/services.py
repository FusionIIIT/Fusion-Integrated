from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from ..models import (
    Complaint, Estimate, InventoryItem, InventoryMovement,
    ProcurementRequest, PhysicalVerification, FinalBill, Feedback, ApprovalAuditLog
)
from ..domain.models import determine_cost_band, CostBand
from ..domain.estimate_rules import can_approve_estimate, validate_rejection
from ..domain.workflow_rules import can_resolve_complaint, can_settle_payment

@transaction.atomic
def submit_complaint(requester_id: str, department: str, category: str, title: str, description: str, location: str, urgency: str = "NORMAL", remarks: str = "") -> Complaint:
    if not title or len(title.strip()) < 3:
        raise ValidationError("Title is required and must be at least 3 characters.")
    if not description or len(description.strip()) < 5:
        raise ValidationError("Description is required and must be at least 5 characters.")

    # Automatic engineer assignment (Round robin or category based)
    assigned_eng = "eng_civil_01" if category == "CIVIL" else "eng_elec_01"

    c = Complaint.objects.create(
        requester_id=requester_id,
        department=department,
        category=category,
        title=title,
        description=description,
        location=location,
        urgency=urgency,
        remarks=remarks,
        assigned_engineer_id=assigned_eng,
        status="ASSIGNED",
        fast_tracked=(urgency == "URGENT")
    )

    ApprovalAuditLog.objects.create(
        entity_type="COMPLAINT",
        entity_id=str(c.id),
        action="SUBMIT_AND_ASSIGN",
        actor_id=requester_id,
        actor_role="employee",
        remarks=f"Submitted and auto-assigned to {assigned_eng}"
    )
    return c

@transaction.atomic
def create_estimate(complaint_id: int, engineer_id: str, time_days: int, material_cost: Decimal, labor_cost: Decimal, other_cost: Decimal) -> Estimate:
    complaint = Complaint.objects.get(id=complaint_id)
    est, created = Estimate.objects.get_or_create(
        complaint=complaint,
        defaults={
            "engineer_id": engineer_id,
            "time_days": time_days,
            "material_cost": material_cost,
            "labor_cost": labor_cost,
            "other_cost": other_cost,
            "status": "PENDING_APPROVAL"
        }
    )
    if not created:
        est.engineer_id = engineer_id
        est.time_days = time_days
        est.material_cost = material_cost
        est.labor_cost = labor_cost
        est.other_cost = other_cost
        est.status = "PENDING_APPROVAL"
        est.save()

    complaint.status = "ASSESSED"
    complaint.save()

    ApprovalAuditLog.objects.create(
        entity_type="ESTIMATE",
        entity_id=str(est.id),
        action="CREATE_ESTIMATE",
        actor_id=engineer_id,
        actor_role="engineer",
        remarks=f"Estimate prepared: Total {est.total_cost} (Band {est.cost_band})"
    )
    return est

@transaction.atomic
def approve_estimate(estimate_id: int, actor_id: str, actor_role: str) -> Estimate:
    est = Estimate.objects.get(id=estimate_id)
    authorized, msg = can_approve_estimate(
        role=actor_role,
        total_cost=est.total_cost,
        committee_reviewed=est.committee_reviewed,
        forwarded_to_director=est.forwarded_to_director
    )
    if not authorized:
        raise ValidationError(msg)

    est.status = "APPROVED"
    est.approved_by_id = actor_id
    est.approved_at = timezone.now()
    est.save()

    complaint = est.complaint
    complaint.status = "ESTIMATE_APPROVED"
    complaint.save()

    ApprovalAuditLog.objects.create(
        entity_type="ESTIMATE",
        entity_id=str(est.id),
        action="APPROVE_ESTIMATE",
        actor_id=actor_id,
        actor_role=actor_role,
        remarks=msg
    )
    return est

@transaction.atomic
def reject_estimate(estimate_id: int, actor_id: str, actor_role: str, reason: str) -> Estimate:
    val, msg = validate_rejection(reason)
    if not val:
        raise ValidationError(msg)

    est = Estimate.objects.get(id=estimate_id)
    est.status = "REJECTED"
    est.rejection_reason = reason
    est.save()

    complaint = est.complaint
    complaint.status = "REJECTED"
    complaint.save()

    ApprovalAuditLog.objects.create(
        entity_type="ESTIMATE",
        entity_id=str(est.id),
        action="REJECT_ESTIMATE",
        actor_id=actor_id,
        actor_role=actor_role,
        remarks=f"Rejected: {reason}"
    )
    return est

@transaction.atomic
def verify_and_resolve(complaint_id: int, verified_by_id: str, passed: bool, remarks: str) -> PhysicalVerification:
    complaint = Complaint.objects.get(id=complaint_id)
    pv = PhysicalVerification.objects.create(
        complaint=complaint,
        verified_by_id=verified_by_id,
        passed=passed,
        remarks=remarks
    )
    if passed:
        complaint.status = "RESOLVED"
        complaint.save()
    else:
        pv.rework_count += 1
        pv.save()
        complaint.status = "IN_PROGRESS"
        complaint.save()

    ApprovalAuditLog.objects.create(
        entity_type="COMPLAINT",
        entity_id=str(complaint.id),
        action="PHYSICAL_VERIFICATION",
        actor_id=verified_by_id,
        actor_role="hod",
        remarks=f"Verification: {'Passed' if passed else 'Failed - Rework needed'}"
    )
    return pv

@transaction.atomic
def submit_bill(complaint_id: int, engineer_id: str, bill_number: str, amount: Decimal) -> FinalBill:
    complaint = Complaint.objects.get(id=complaint_id)
    if complaint.status not in ["VERIFIED", "RESOLVED", "COMPLETED"]:
        raise ValidationError("Bill can only be submitted after physical work completion/verification.")

    bill = FinalBill.objects.create(
        complaint=complaint,
        bill_number=bill_number,
        submitted_by_id=engineer_id,
        total_amount=amount,
        settlement_status="SUBMITTED"
    )
    ApprovalAuditLog.objects.create(
        entity_type="FINAL_BILL",
        entity_id=str(bill.id),
        action="SUBMIT_BILL",
        actor_id=engineer_id,
        actor_role="engineer",
        remarks=f"Bill #{bill_number} submitted for Rs. {amount}"
    )
    return bill

@transaction.atomic
def settle_bill(bill_id: int, actor_id: str, actor_role: str) -> FinalBill:
    bill = FinalBill.objects.get(id=bill_id)
    auth, msg = can_settle_payment(bill.auditor_verified, bill.director_approved, actor_role)
    if not auth:
        raise ValidationError(msg)

    bill.settlement_status = "SETTLED_BY_ACCOUNTS"
    bill.settled_at = timezone.now()
    bill.save()

    complaint = bill.complaint
    complaint.status = "CLOSED"
    complaint.save()

    ApprovalAuditLog.objects.create(
        entity_type="FINAL_BILL",
        entity_id=str(bill.id),
        action="SETTLE_BILL",
        actor_id=actor_id,
        actor_role=actor_role,
        remarks="Payment settled by Accounts Department."
    )
    return bill
