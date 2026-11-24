# Tender publication, bids, evaluation, and award (PSM-UC-022, BR-PSM-023).
from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.psm.domain import state_machine as sm
from modules.psm.models import Indent, Tender, TenderBid, Vendor
from modules.psm.services.common import audit_record, next_number, translate_errors
from modules.psm.services.indents import transition_indent


@transaction.atomic
def create_tender(
    *, actor, indent_id: int, title: str, scope: str, evaluation_criteria: str, submission_deadline
) -> Tender:
    """Create a draft tender for an authorized tender-method indent (PSM-UC-022)."""
    indent = Indent.objects.select_for_update().filter(pk=indent_id).first()
    if indent is None:
        raise NotFoundError("Indent not found.")
    if indent.status != sm.PROCUREMENT_AUTHORIZED or indent.procurement_method != "tender":
        raise ConflictError(
            "Tenders require an authorized indent with tender procurement method.",
            code="indent_not_tender_ready",
        )
    if submission_deadline <= timezone.now():
        raise DomainError("Set a submission deadline in the future.", code="deadline_in_past")
    tender = Tender.objects.create(
        tender_number=next_number("TND"),
        indent=indent,
        title=title.strip(),
        scope=scope.strip(),
        evaluation_criteria=evaluation_criteria.strip(),
        submission_deadline=submission_deadline,
        status=sm.TENDER_DRAFT,
        created_by_user_id=actor.user_id,
    )
    audit_record(
        actor=actor,
        action="tender.created",
        target_type="tender",
        target_id=tender.pk,
        to_state=sm.TENDER_DRAFT,
    )
    return tender


@transaction.atomic
def publish_tender(*, actor, tender_id: int) -> Tender:
    """Publish a draft tender invitation (AFR-PSM-032)."""
    tender = Tender.objects.select_for_update().filter(pk=tender_id).first()
    if tender is None:
        raise NotFoundError("Tender not found.")
    with translate_errors():
        sm.resolve("tender", tender.status, sm.TENDER_PUBLISHED, sm.PS_ADMIN)
    tender.status = sm.TENDER_PUBLISHED
    tender.published_at = timezone.now()
    tender.save(update_fields=["status", "published_at", "updated_at"])
    audit_record(
        actor=actor,
        action="tender.published",
        target_type="tender",
        target_id=tender.pk,
        from_state=sm.TENDER_DRAFT,
        to_state=sm.TENDER_PUBLISHED,
    )
    return tender


@transaction.atomic
def record_bid(*, actor, tender_id: int, vendor_id: int, quoted_amount: Decimal) -> TenderBid:
    """Record a vendor bid against a published tender (AFR-PSM-033)."""
    tender = Tender.objects.select_for_update().filter(pk=tender_id).first()
    if tender is None:
        raise NotFoundError("Tender not found.")
    if tender.status != sm.TENDER_PUBLISHED:
        raise ConflictError(
            "Bids can only be recorded while a tender is published.", code="tender_not_published"
        )
    vendor = Vendor.objects.filter(pk=vendor_id, is_active=True).first()
    if vendor is None:
        raise NotFoundError("Vendor not found.")
    if quoted_amount <= Decimal("0"):
        raise DomainError("Quoted bid amount must be greater than zero.", code="invalid_bid_amount")
    try:
        bid = TenderBid.objects.create(
            tender=tender,
            vendor=vendor,
            quoted_amount=quoted_amount,
            recorded_by_user_id=actor.user_id,
        )
    except IntegrityError as exc:
        raise ConflictError(
            "This vendor has already submitted a bid for this tender.", code="duplicate_bid"
        ) from exc
    audit_record(
        actor=actor,
        action="tender.bid_recorded",
        target_type="tender",
        target_id=tender.pk,
        details={"bid_id": bid.pk, "vendor_id": vendor.pk},
    )
    return bid


@transaction.atomic
def evaluate_bids(
    *,
    actor,
    tender_id: int,
    evaluations: list[dict],
    committee_members: list[str],
    committee_minutes: str,
) -> Tender:
    """Record bid evaluations against defined tender criteria (BR-PSM-023, AFR-PSM-034)."""
    tender = Tender.objects.select_for_update().filter(pk=tender_id).first()
    if tender is None:
        raise NotFoundError("Tender not found.")
    with translate_errors():
        sm.resolve("tender", tender.status, sm.TENDER_EVALUATED, sm.PS_ADMIN)
    bids = {b.pk: b for b in tender.bids.all()}
    if not bids:
        raise ConflictError(
            "Record at least one vendor bid before evaluating the tender.", code="no_bids"
        )
    if not evaluations:
        raise DomainError(
            "Provide evaluation scores for at least one submitted bid.", code="evaluations_required"
        )
    for item in evaluations:
        bid = bids.get(int(item["bid_id"]))
        if bid is None:
            raise NotFoundError("One of the evaluated bids does not belong to this tender.")
        bid.technical_score = item.get("technical_score")
        bid.financial_score = item.get("financial_score")
        bid.evaluation_notes = (item.get("evaluation_notes") or "").strip()
        bid.save(
            update_fields=["technical_score", "financial_score", "evaluation_notes", "updated_at"]
        )
    tender.committee_members = [m.strip() for m in committee_members if (m or "").strip()]
    tender.committee_minutes = committee_minutes.strip()
    tender.status = sm.TENDER_EVALUATED
    tender.save(update_fields=["committee_members", "committee_minutes", "status", "updated_at"])
    audit_record(
        actor=actor,
        action="tender.evaluated",
        target_type="tender",
        target_id=tender.pk,
        from_state=sm.TENDER_PUBLISHED,
        to_state=sm.TENDER_EVALUATED,
    )
    return tender


@transaction.atomic
def award_tender(*, actor, tender_id: int, bid_id: int, committee_minutes: str = "") -> Tender:
    """Record committee approval and award the tender (BR-PSM-023, AFR-PSM-035)."""
    tender = (
        Tender.objects.select_for_update().select_related("indent").filter(pk=tender_id).first()
    )
    if tender is None:
        raise NotFoundError("Tender not found.")
    with translate_errors():
        sm.resolve("tender", tender.status, sm.TENDER_AWARDED_STATE, sm.PS_ADMIN)
    bid = tender.bids.select_related("vendor").filter(pk=bid_id).first()
    if bid is None:
        raise NotFoundError("Selected bid not found on this tender.")
    tender.bids.update(is_selected=False)
    bid.is_selected = True
    bid.save(update_fields=["is_selected", "updated_at"])
    if committee_minutes.strip():
        tender.committee_minutes = committee_minutes.strip()
    tender.awarded_vendor = bid.vendor
    tender.awarded_by_user_id = actor.user_id
    tender.awarded_at = timezone.now()
    tender.status = sm.TENDER_AWARDED_STATE
    tender.save(
        update_fields=[
            "committee_minutes",
            "awarded_vendor",
            "awarded_by_user_id",
            "awarded_at",
            "status",
            "updated_at",
        ]
    )
    transition_indent(
        indent=tender.indent,
        to_status=sm.TENDER_AWARDED,
        actor=actor,
        actor_lane=sm.PS_ADMIN,
        action="tender.awarded",
        reason=f"Tender {tender.tender_number} awarded to {bid.vendor.name}",
    )
    audit_record(
        actor=actor,
        action="tender.awarded",
        target_type="tender",
        target_id=tender.pk,
        from_state=sm.TENDER_EVALUATED,
        to_state=sm.TENDER_AWARDED_STATE,
    )
    return tender
