from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count

from modules.directory.models import UserRef
from modules.iwd.models import (
    IwdAuditEvent,
    IwdComplaint,
    IwdEstimate,
    IwdFeedback,
    IwdFinalBill,
    IwdInventoryItem,
    IwdInventoryMovement,
    IwdNotification,
    IwdProcurementNeed,
    IwdWorkVerification,
)

LOW_COST = Decimal("25000")
HIGH_COST = Decimal("250000")


def _user_id(actor):
    try:
        return int(actor.user_id)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("An authenticated actor is required.") from exc


def cost_band(total):
    try:
        total = Decimal(str(total))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Estimate total must be a valid amount.") from exc
    if total < LOW_COST:
        return "low"
    if total <= HIGH_COST:
        return "mid"
    return "high"


def _audit(complaint, actor, action, old="", new="", reason=""):
    return IwdAuditEvent.objects.create(
        complaint=complaint,
        actor_user_id=_user_id(actor),
        action=action,
        from_state=old,
        to_state=new,
        reason=reason,
    )


def _notify(complaint, event, message, recipients):
    ids = {int(user_id) for user_id in recipients if user_id is not None}
    IwdNotification.objects.bulk_create(
        [
            IwdNotification(
                recipient_user_id=user_id,
                complaint=complaint,
                event=event,
                message=message,
            )
            for user_id in ids
        ]
    )


def _move(complaint, actor, state, action, reason=""):
    old = complaint.state
    complaint.state = state
    complaint.save(update_fields=["state", "updated_at"])
    _audit(complaint, actor, action, old, state, reason)
    _notify(
        complaint,
        "status_changed",
        f"Complaint IWD-{complaint.pk} changed from {old} to {state}.",
        [complaint.reporter_user_id, complaint.engineer_user_id],
    )
    return complaint


def _select_engineer(metadata):
    metadata = metadata or {}
    requested = metadata.get("engineer_user_id")
    if requested:
        return int(requested)
    candidates = metadata.get("engineer_user_ids", [])
    if candidates:
        ids = [int(value) for value in candidates]
        counts = {
            row["engineer_user_id"]: row["load"]
            for row in IwdComplaint.objects.filter(
                engineer_user_id__in=ids,
                state__in=["assigned", "assessed", "in_progress", "verification_pending"],
            ).values("engineer_user_id").annotate(load=Count("id"))
        }
        return min(ids, key=lambda value: counts.get(value, 0))
    expertise = metadata.get("expertise")
    if expertise:
        candidate = (
            UserRef.objects.filter(
                kind__in=("faculty", "staff"),
                is_active=True,
                discipline__iexact=str(expertise),
            )
            .order_by("user_id")
            .first()
        )
        if candidate:
            return candidate.user_id
    candidate = (
        UserRef.objects.filter(kind__in=("faculty", "staff"), is_active=True)
        .order_by("user_id")
        .first()
    )
    return candidate.user_id if candidate else None


@transaction.atomic
def submit_complaint(*, actor, title, description, location, issue_category="other",
                     urgency="normal", remarks="", urgent=False, metadata=None):
    values = [title, description, location, issue_category, urgency]
    if any(not str(value).strip() for value in values):
        raise ValueError("Issue category, title, description, location, and urgency are required.")
    if urgency not in {"low", "normal", "high", "critical"}:
        raise ValueError("Urgency must be low, normal, high, or critical.")
    data = dict(metadata or {})
    engineer_id = _select_engineer(data)
    complaint = IwdComplaint.objects.create(
        reporter_user_id=_user_id(actor),
        title=title.strip(),
        description=description.strip(),
        issue_category=issue_category.strip(),
        location=location.strip(),
        urgency=urgency,
        remarks=remarks.strip(),
        urgent=urgent,
        engineer_user_id=engineer_id,
        metadata=data,
        state="assigned" if engineer_id else "submitted",
    )
    _audit(complaint, actor, "UC-IWD-001 submit", "", complaint.state)
    _notify(
        complaint,
        "complaint_submitted",
        f"Complaint IWD-{complaint.pk} was submitted.",
        [complaint.reporter_user_id, engineer_id],
    )
    return complaint


@transaction.atomic
def assess(*, complaint, actor, assessment, needs_site_information=False):
    if (
        complaint.state not in {"assigned", "assessed"}
        or complaint.engineer_user_id != _user_id(actor)
    ):
        raise ValueError("Only the assigned Engineer may assess this complaint.")
    if not isinstance(assessment, dict) or not assessment:
        raise ValueError("Assessment details are required.")
    complaint.metadata = {**complaint.metadata, "assessment": assessment}
    complaint.save(update_fields=["metadata", "updated_at"])
    if needs_site_information:
        _audit(
            complaint,
            actor,
            "UC-IWD-015 assessment_incomplete",
            complaint.state,
            complaint.state,
        )
        return complaint
    return _move(complaint, actor, "assessed", "UC-IWD-015 assess")


@transaction.atomic
def estimate(
    *, complaint, actor, total_cost, details=None, estimated_time="", materials=None, submit=True
):
    if (
        complaint.state not in {"assessed", "rejected"}
        or complaint.engineer_user_id != _user_id(actor)
    ):
        raise ValueError("Only the assigned Engineer may prepare this estimate.")
    try:
        total = Decimal(str(total_cost))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Estimate total must be a valid amount.") from exc
    if total <= 0:
        raise ValueError("Estimate total must be positive.")
    band = cost_band(total)
    row, _ = IwdEstimate.objects.update_or_create(
        complaint=complaint,
        defaults={
            "total_cost": total,
            "cost_band": band,
            "status": "submitted" if submit else "draft",
            "estimated_time": estimated_time,
            "materials": materials or [],
            "details": details or {},
            "submitted_by_user_id": _user_id(actor),
        },
    )
    if not submit:
        _audit(complaint, actor, "UC-IWD-021 save_draft")
        return row
    state = {"low": "low_cost_review", "mid": "committee_review", "high": "director_review"}[band]
    _move(complaint, actor, state, "UC-IWD-021 submit estimate")
    return row


@transaction.atomic
def committee_review(*, complaint, actor, outcome):
    if complaint.state != "committee_review":
        raise ValueError("Complaint is not awaiting committee review.")
    if not str(outcome).strip():
        raise ValueError("Committee outcome is required.")
    complaint.estimate.committee_outcome = str(outcome).strip()
    complaint.estimate.save(update_fields=["committee_outcome", "updated_at"])
    return _move(complaint, actor, "department_head_review", "UC-IWD-041 committee review")


@transaction.atomic
def decide(*, complaint, actor, outcome, reason="", forward=False):
    review_states = {"low_cost_review", "department_head_review", "director_review"}
    if complaint.state not in review_states:
        if complaint.state == "committee_review":
            raise ValueError("committee outcome is required before an approval decision.")
        raise ValueError("Complaint is not awaiting an approval decision.")
    if outcome not in {"approve", "reject", "forward"}:
        raise ValueError("Outcome must be approve, reject, or forward.")
    if outcome == "reject" and not str(reason).strip():
        raise ValueError("A rejection reason is required.")
    if complaint.state == "department_head_review" and outcome == "forward":
        target = "director_review"
        action = "UC-IWD-041 forward to Director"
    elif outcome == "approve":
        target = (
            "bidding_authorized"
            if complaint.state == "director_review" and complaint.estimate.cost_band == "high"
            else "estimate_approved"
        )
        action = "approval decision"
    elif outcome == "reject":
        target = "rejected"
        action = "approval rejection"
    else:
        raise ValueError("Forward is only available to the Department Head.")
    estimate = complaint.estimate
    estimate.status = "approved" if target in {"estimate_approved", "bidding_authorized"} else (
        "rejected" if target == "rejected" else "submitted"
    )
    estimate.decision_reason = str(reason).strip()
    estimate.save(update_fields=["status", "decision_reason", "updated_at"])
    complaint.rejection_reason = str(reason).strip() if target == "rejected" else ""
    complaint.save(update_fields=["rejection_reason", "updated_at"])
    return _move(complaint, actor, target, action, str(reason).strip())


@transaction.atomic
def modify_and_resubmit(*, complaint, actor, total_cost=None, details=None):
    if complaint.state != "rejected" or complaint.engineer_user_id != _user_id(actor):
        raise ValueError("Only the assigned Engineer may resubmit a rejected request.")
    if total_cost is None:
        total_cost = complaint.estimate.total_cost
    complaint.rejection_reason = ""
    complaint.save(update_fields=["rejection_reason", "updated_at"])
    result = estimate(
        complaint=complaint,
        actor=actor,
        total_cost=total_cost,
        details=details or complaint.estimate.details,
    )
    _audit(complaint, actor, "UC-IWD-151 modify and resubmit", "rejected", complaint.state)
    return result


@transaction.atomic
def flag_urgent(*, complaint, actor, remarks=""):
    if complaint.engineer_user_id != _user_id(actor) or complaint.state in {"resolved", "settled"}:
        raise ValueError("Only the assigned Engineer may flag an active complaint.")
    complaint.urgent = True
    complaint.urgent_remarks = str(remarks).strip()
    complaint.save(update_fields=["urgent", "urgent_remarks", "updated_at"])
    _audit(complaint, actor, "UC-IWD-025 flag urgent", complaint.state, complaint.state, remarks)
    _notify(
        complaint,
        "urgent_escalation",
        f"Urgent repair IWD-{complaint.pk} requires fast-track review.",
        [complaint.reporter_user_id],
    )
    return complaint


@transaction.atomic
def review_urgent(*, complaint, actor, accepted, remarks=""):
    if not complaint.urgent:
        raise ValueError("Complaint has no urgent escalation.")
    _audit(complaint, actor, "UC-IWD-055 urgent review", complaint.state, complaint.state, remarks)
    if accepted:
        complaint.metadata = {**complaint.metadata, "urgent_priority": True}
        complaint.save(update_fields=["metadata", "updated_at"])
    return complaint


@transaction.atomic
def check_stock(*, complaint, actor, materials):
    if complaint.state != "estimate_approved":
        raise ValueError("Only approved work can enter stock checking.")
    if not materials:
        raise ValueError("Required materials are needed for a stock check.")
    shortages = []
    for requirement in materials:
        if not isinstance(requirement, dict) or not requirement.get("sku"):
            raise ValueError("Each material must include a stock keeping unit.")
        try:
            quantity = Decimal(str(requirement["quantity"]))
        except (InvalidOperation, KeyError, TypeError, ValueError) as exc:
            raise ValueError("Each material must include a valid quantity.") from exc
        if quantity <= 0:
            raise ValueError("Material quantities must be positive.")
        item = IwdInventoryItem.objects.filter(sku=requirement["sku"], active=True).first()
        if item is None or item.quantity < quantity:
            shortages.append(requirement)
    if shortages:
        complaint.state = "materials_pending"
        complaint.save(update_fields=["state", "updated_at"])
        need = IwdProcurementNeed.objects.create(
            complaint=complaint,
            actor_user_id=_user_id(actor),
            materials=shortages,
            route="internal" if complaint.estimate.cost_band == "low" else "policy",
        )
        _audit(
            complaint,
            actor,
            "UC-IWD-061 stock shortage",
            "estimate_approved",
            "materials_pending",
        )
        return need
    for requirement in materials:
        issue_material(complaint=complaint, actor=actor, sku=requirement["sku"],
                       quantity=requirement["quantity"])
    _move(complaint, actor, "materials_issued", "UC-IWD-061 issue material")
    return complaint


@transaction.atomic
def issue_material(*, complaint, actor, sku, quantity):
    item = IwdInventoryItem.objects.select_for_update().filter(sku=sku, active=True).first()
    try:
        amount = Decimal(str(quantity))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Material quantity must be valid.") from exc
    if item is None or amount <= 0 or item.quantity < amount:
        raise ValueError("Required stock is unavailable.")
    item.quantity -= amount
    item.save(update_fields=["quantity", "updated_at"])
    return IwdInventoryMovement.objects.create(
        item=item, complaint=complaint, actor_user_id=_user_id(actor),
        quantity=amount, movement_type="issue",
    )


@transaction.atomic
def complete_procurement(*, need, actor, remarks=""):
    if need.state not in {"pending", "coordinating"}:
        raise ValueError("Procurement need is not pending.")
    need.state = "completed"
    need.remarks = str(remarks).strip()
    need.save(update_fields=["state", "remarks", "updated_at"])
    _move(need.complaint, actor, "materials_available", "UC-IWD-071 procurement completed")
    return need


@transaction.atomic
def execute_work(*, complaint, actor, progress="", materials_used=None, complete=False):
    if complaint.engineer_user_id != _user_id(actor):
        raise ValueError("Only the assigned Engineer may execute this work.")
    if complaint.state not in {
        "estimate_approved",
        "vendor_selected",
        "materials_issued",
        "materials_available",
        "in_progress",
        "rework_required",
    }:
        raise ValueError("Work is not ready for execution.")
    metadata = {**complaint.metadata, "progress": str(progress).strip()}
    complaint.metadata = metadata
    complaint.save(update_fields=["metadata", "updated_at"])
    for item in materials_used or []:
        issue_material(complaint=complaint, actor=actor, sku=item["sku"], quantity=item["quantity"])
    return _move(complaint, actor, "verification_pending" if complete else "in_progress",
                 "UC-IWD-091 complete work" if complete else "UC-IWD-091 update progress")


@transaction.atomic
def verify_work(*, complaint, actor, outcome, remarks=""):
    if complaint.state != "verification_pending":
        raise ValueError("Complaint is not awaiting physical verification.")
    if outcome not in {"approved", "rework"}:
        raise ValueError("Verification outcome must be approved or rework.")
    verification, _ = IwdWorkVerification.objects.get_or_create(
        complaint=complaint,
        defaults={"actor_user_id": _user_id(actor), "outcome": outcome},
    )
    verification.actor_user_id = _user_id(actor)
    verification.outcome = outcome
    verification.remarks = str(remarks).strip()
    if outcome == "rework":
        verification.rework_count += 1
    verification.save()
    return _move(
        complaint,
        actor,
        "resolved" if outcome == "approved" else "rework_required",
        "UC-IWD-101 verify work",
        remarks,
    )


@transaction.atomic
def submit_bill(*, complaint, actor, invoice_number, amount, supporting_records=None):
    if complaint.state != "resolved" or complaint.engineer_user_id != _user_id(actor):
        raise ValueError("A verified complaint may be billed only by its assigned Engineer.")
    if not invoice_number.strip() or not supporting_records:
        raise ValueError("Invoice number and supporting records are required.")
    bill = IwdFinalBill.objects.create(
        complaint=complaint,
        submitted_by_user_id=_user_id(actor),
        invoice_number=invoice_number.strip(),
        amount=Decimal(str(amount)),
        supporting_records=supporting_records,
    )
    _move(complaint, actor, "audit_pending", "UC-IWD-111 submit final bill")
    return bill


@transaction.atomic
def audit_bill(*, bill, actor, outcome, remarks=""):
    if bill.state not in {"audit_pending", "queried"}:
        raise ValueError("Bill is not awaiting audit.")
    if outcome not in {"validated", "query"}:
        raise ValueError("Audit outcome must be validated or query.")
    bill.state = "validated" if outcome == "validated" else "queried"
    bill.audit_remarks = str(remarks).strip()
    bill.save(update_fields=["state", "audit_remarks", "updated_at"])
    _move(
        bill.complaint,
        actor,
        "payment_approval_pending" if outcome == "validated" else "resolved",
        "UC-IWD-121 audit bill",
        remarks,
    )
    return bill


@transaction.atomic
def approve_payment(*, bill, actor, approved, reason=""):
    if bill.state != "validated":
        raise ValueError("Only a validated bill can be submitted for payment approval.")
    if not approved and not str(reason).strip():
        raise ValueError("A reason is required when payment is withheld.")
    bill.state = "settlement_pending" if approved else "withheld"
    bill.decision_reason = str(reason).strip()
    bill.save(update_fields=["state", "decision_reason", "updated_at"])
    _move(bill.complaint, actor, "settlement_pending" if approved else "resolved",
          "UC-IWD-131 payment decision", reason)
    return bill


@transaction.atomic
def record_settlement(*, bill, actor, status):
    if bill.state != "settlement_pending" or not str(status).strip():
        raise ValueError("Only an approved payment can be settled.")
    bill.state = "settled"
    bill.settlement_status = str(status).strip()
    bill.save(update_fields=["state", "settlement_status", "updated_at"])
    return _move(bill.complaint, actor, "settled", "UC-IWD-131 settlement recorded", status)


@transaction.atomic
def submit_feedback(*, complaint, actor, rating=None, comments="", post_repair_issue=""):
    if complaint.state not in {
        "resolved",
        "audit_pending",
        "payment_approval_pending",
        "settlement_pending",
        "settled",
    }:
        raise ValueError(
            "Feedback is available only after physical verification resolves the complaint."
        )
    if complaint.reporter_user_id != _user_id(actor):
        raise ValueError("Only the complaint owner may submit feedback.")
    if rating is not None and not 1 <= int(rating) <= 5:
        raise ValueError("Rating must be between 1 and 5.")
    return IwdFeedback.objects.create(
        complaint=complaint,
        actor_user_id=_user_id(actor),
        rating=rating,
        comments=str(comments).strip(),
        post_repair_issue=str(post_repair_issue).strip(),
    )


@transaction.atomic
def select_vendor(*, complaint, actor, vendor_name, route, policy_compliant=True):
    if complaint.state != "bidding_authorized":
        raise ValueError("External bidding must be authorized before vendor selection.")
    if route not in {"approved_list", "competitive_bidding"} or not policy_compliant:
        raise ValueError("Vendor selection must follow an approved procurement route.")
    complaint.metadata = {
        **complaint.metadata,
        "vendor": {"name": str(vendor_name).strip(), "route": route},
    }
    complaint.save(update_fields=["metadata", "updated_at"])
    return _move(complaint, actor, "vendor_selected", "UC-IWD-081 vendor selected")


def switch_active_role(*, actor, role):
    assigned = set(getattr(actor, "roles", ()) or ())
    if role not in assigned:
        raise ValueError("The selected role is not assigned to this user.")
    actor.active_role = role
    return role


@transaction.atomic
def issue_configured_notification(*, complaint, actor, event, recipients, message):
    allowed = {
        "complaint_submitted",
        "status_changed",
        "approval_decision",
        "urgent_escalation",
        "deadline",
        "policy_update",
    }
    if event not in allowed:
        raise ValueError("Unsupported IWD notification event.")
    _audit(complaint, actor, "UC-IWD-175 notification", complaint.state, complaint.state, event)
    _notify(complaint, event, message, recipients)
    return complaint.notifications.filter(event=event).order_by("-created_at").first()
