from django.db import transaction
from django.utils import timezone

from core.api.exceptions import DomainError as CoreDomainError
from modules.department.domain.errors import DomainError, InvalidTransition
from modules.department.domain.state_machine import (
    validate_detail_transition,
    validate_feedback_transition,
    validate_stock_transition,
)
from modules.department.models import (
    Announcement,
    Department,
    DepartmentDetail,
    DepartmentDetailChange,
    DepartmentProfile,
    Feedback,
    InventoryItem,
    LabResource,
    NotificationOutbox,
    StockMovement,
    StockRequest,
    Timetable,
    TimetableSlot,
)


def _domain_to_core(exc):
    return CoreDomainError(getattr(exc, "code", "domain_error"), str(exc))


def enqueue_notification(*, department_id, event, recipient_user_id, payload=None):
    return NotificationOutbox.objects.create(
        department_id=department_id,
        event=event,
        recipient_user_id=recipient_user_id,
        payload=payload or {},
    )


def create_department(*, code, name, description="", head_user_id=None, admin_user_id=None):
    return Department.objects.create(
        code=code,
        name=name,
        description=description,
        head_user_id=head_user_id,
        admin_user_id=admin_user_id,
    )


def create_announcement(
    *,
    department_id,
    title,
    body,
    academic_year="",
    programme="",
    role_target="",
    created_by_user_id,
):
    a = Announcement.objects.create(
        department_id=department_id,
        title=title,
        body=body,
        academic_year=academic_year,
        programme=programme,
        role_target=role_target,
        created_by_user_id=created_by_user_id,
    )
    enqueue_notification(
        department_id=department_id,
        event="announcement_published",
        recipient_user_id=created_by_user_id,
        payload={"announcement_id": a.id, "title": title},
    )
    return a


def hide_announcement(*, announcement_id):
    a = Announcement.objects.get(pk=announcement_id)
    a.is_hidden = True
    a.save(update_fields=["is_hidden", "updated_at"])
    return a


def delete_announcement(*, announcement_id):
    Announcement.objects.filter(pk=announcement_id).delete()


def create_inventory_item(*, department_id, name, quantity=0, unit=""):
    return InventoryItem.objects.create(
        department_id=department_id, name=name, quantity=quantity, unit=unit
    )


def insert_stock(*, department_id, item_id, quantity, actor_user_id):
    with transaction.atomic():
        item = InventoryItem.objects.select_for_update().get(
            pk=item_id, department_id=department_id
        )
        item.quantity += quantity
        item.save(update_fields=["quantity", "updated_at"])
        StockMovement.objects.create(
            department_id=department_id,
            item=item,
            movement_type="insertion",
            quantity=quantity,
            actor_user_id=actor_user_id,
        )
    return item


def create_stock_request(*, department_id, item_id, requester_user_id, quantity):
    item = InventoryItem.objects.get(pk=item_id, department_id=department_id)
    if quantity > item.quantity:
        raise DomainError("insufficient_stock", "Requested quantity exceeds current inventory.")
    req = StockRequest.objects.create(
        department_id=department_id,
        item=item,
        requester_user_id=requester_user_id,
        quantity=quantity,
    )
    enqueue_notification(
        department_id=department_id,
        event="stock_request_submitted",
        recipient_user_id=requester_user_id,
        payload={"request_id": req.id, "quantity": quantity},
    )
    return req


def decide_stock_request(*, request_id, to_status, actor_user_id):
    with transaction.atomic():
        req = StockRequest.objects.select_for_update().get(pk=request_id)
        try:
            validate_stock_transition(req.status, to_status)
        except ValueError as e:
            raise InvalidTransition("invalid_transition", str(e)) from None
        req.status = to_status
        if to_status in ("approved", "rejected"):
            req.approved_by_user_id = actor_user_id
            req.decided_at = timezone.now()
        req.save(update_fields=["status", "approved_by_user_id", "decided_at", "updated_at"])
        enqueue_notification(
            department_id=req.department_id,
            event="stock_request_decided",
            recipient_user_id=req.requester_user_id,
            payload={"request_id": req.id, "status": to_status},
        )
    return req


def issue_stock_request(*, request_id, actor_user_id):
    with transaction.atomic():
        req = StockRequest.objects.select_for_update().get(pk=request_id)
        try:
            validate_stock_transition(req.status, "issued")
        except ValueError as e:
            raise InvalidTransition("invalid_transition", str(e)) from None
        item = InventoryItem.objects.select_for_update().get(pk=req.item_id)
        if req.quantity > item.quantity:
            raise DomainError("insufficient_stock", "Insufficient inventory at issuance.")
        item.quantity -= req.quantity
        item.save(update_fields=["quantity", "updated_at"])
        req.status = "issued"
        req.issued_by_user_id = actor_user_id
        req.issued_at = timezone.now()
        req.save(update_fields=["status", "issued_by_user_id", "issued_at", "updated_at"])
        StockMovement.objects.create(
            department_id=req.department_id,
            item=item,
            movement_type="issue",
            quantity=-req.quantity,
            actor_user_id=actor_user_id,
            request=req,
        )
        enqueue_notification(
            department_id=req.department_id,
            event="stock_issued",
            recipient_user_id=req.requester_user_id,
            payload={"request_id": req.id, "quantity": req.quantity},
        )
    return req


def submit_feedback(*, department_id, submitter_user_id, subject, body):
    fb = Feedback.objects.create(
        department_id=department_id, submitter_user_id=submitter_user_id, subject=subject, body=body
    )
    enqueue_notification(
        department_id=department_id,
        event="feedback_submitted",
        recipient_user_id=submitter_user_id,
        payload={"feedback_id": fb.id, "subject": subject},
    )
    return fb


def review_feedback(*, feedback_id, category, reviewer_user_id):
    fb = Feedback.objects.get(pk=feedback_id)
    fb.category = category
    fb.status = "reviewed"
    fb.reviewed_by_user_id = reviewer_user_id
    fb.save(update_fields=["category", "status", "reviewed_by_user_id", "updated_at"])
    return fb


def resolve_feedback(*, feedback_id, to_status, actor_user_id):
    with transaction.atomic():
        fb = Feedback.objects.select_for_update().get(pk=feedback_id)
        try:
            validate_feedback_transition(fb.status, to_status)
        except ValueError as e:
            raise InvalidTransition("invalid_transition", str(e)) from None
        fb.status = to_status
        fb.resolved_by_user_id = actor_user_id
        fb.terminal_at = timezone.now()
        fb.save(update_fields=["status", "resolved_by_user_id", "terminal_at", "updated_at"])
        enqueue_notification(
            department_id=fb.department_id,
            event=f"feedback_{to_status}",
            recipient_user_id=fb.submitter_user_id,
            payload={"feedback_id": fb.id, "status": to_status},
        )
    return fb


def upsert_profile(
    *,
    department_id,
    user_id,
    display_name="",
    kind="",
    programme="",
    discipline="",
    batch_year=None,
    notes="",
):
    profile, _ = DepartmentProfile.objects.update_or_create(
        department_id=department_id,
        user_id=user_id,
        defaults={
            "display_name": display_name,
            "kind": kind,
            "programme": programme,
            "discipline": discipline,
            "batch_year": batch_year,
            "notes": notes,
        },
    )
    return profile


def create_timetable(*, department_id, title, academic_year="", programme="", uploaded_by_user_id):
    return Timetable.objects.create(
        department_id=department_id,
        title=title,
        academic_year=academic_year,
        programme=programme,
        uploaded_by_user_id=uploaded_by_user_id,
    )


def add_timetable_slot(
    *, timetable_id, day, start_time, end_time, subject, faculty_user_id=None, room=""
):
    # overlap check
    existing = TimetableSlot.objects.filter(timetable_id=timetable_id, day=day)
    for s in existing:
        if not (end_time <= s.start_time or start_time >= s.end_time):
            raise DomainError("slot_overlap", "Timetable slot overlaps an existing slot.")
    return TimetableSlot.objects.create(
        timetable_id=timetable_id,
        day=day,
        start_time=start_time,
        end_time=end_time,
        subject=subject,
        faculty_user_id=faculty_user_id,
        room=room,
    )


def upsert_resource(*, department_id, name, description="", quantity=0, updated_by_user_id):
    res, _ = LabResource.objects.update_or_create(
        department_id=department_id,
        name=name,
        defaults={
            "description": description,
            "quantity": quantity,
            "updated_by_user_id": updated_by_user_id,
        },
    )
    return res


def create_detail_change(*, department_id, field_name, proposed_value, proposed_by_user_id):
    return DepartmentDetailChange.objects.create(
        department_id=department_id,
        field_name=field_name,
        proposed_value=proposed_value,
        proposed_by_user_id=proposed_by_user_id,
    )


def decide_detail_change(*, change_id, to_status, decided_by_user_id):
    with transaction.atomic():
        ch = DepartmentDetailChange.objects.select_for_update().get(pk=change_id)
        try:
            validate_detail_transition(ch.status, to_status)
        except ValueError as e:
            raise InvalidTransition("invalid_transition", str(e)) from None
        ch.status = to_status
        ch.decided_by_user_id = decided_by_user_id
        ch.decided_at = timezone.now()
        ch.save(update_fields=["status", "decided_by_user_id", "decided_at", "updated_at"])
        if to_status == "approved":
            detail, _ = DepartmentDetail.objects.get_or_create(department_id=ch.department_id)
            setattr(detail, ch.field_name, ch.proposed_value)
            detail.save()
    return ch
