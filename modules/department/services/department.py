"""Small workflow services for the Department module."""

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, PermissionDeniedError
from fusion_auth.client import IamUnavailable
from modules.directory import contracts as directory
from modules.department.models import (
    Announcement,
    DepartmentChange,
    DepartmentDetails,
    Feedback,
    InventoryItem,
    StockMovement,
    StockRequest,
    TimetableEntry,
)
from modules.department.domain.timetable import has_room_overlap


def directory_person(actor):
    """Read the actor's department and academic attributes through the public ACL."""
    try:
        return directory.get_users([actor.user_id]).get(actor.user_id)
    except IamUnavailable as exc:
        raise PermissionDeniedError(
            "Department membership is temporarily unavailable.") from exc


def department_for(actor) -> str:
    """Use the IAM-owned directory projection to scope this module's records."""
    person = directory_person(actor)
    code = (person.department or "").strip() if person else ""
    if not code:
        raise PermissionDeniedError(
            "Your account does not have a department assigned.")
    return code


def _allowed(value, current):
    return current.casefold() in {str(item).casefold() for item in value}


def relevant_announcements(*, department_code, role, programme, academic_year,
                           manage_all_targets=False):
    rows = Announcement.objects.filter(department_code=department_code)
    rows = rows.filter(status="active")
    # HOD may maintain any active announcement in the department, independent
    # of its target audience. Other viewers receive only relevant notices.
    if manage_all_targets:
        return list(rows)
    return [a for a in rows if (
        _allowed(a.target_roles, role)
        and _allowed(a.target_programmes, programme)
        and _allowed(a.target_academic_years, academic_year)
    )]


@transaction.atomic
def insert_stock(*, department_code, actor_user_id, name, quantity, description=""):
    if quantity <= 0:
        raise ConflictError("Inserted quantity must be greater than zero.")
    item, _ = InventoryItem.objects.get_or_create(
        department_code=department_code, name=name,
        defaults={"description": description, "quantity": 0},
    )
    item = InventoryItem.objects.select_for_update().get(pk=item.pk)
    if description:
        item.description = description
    item.quantity += quantity
    item.save(update_fields=["description", "quantity", "updated_at"])
    StockMovement.objects.create(
        department_code=department_code, item=item, movement="insertion",
        quantity=quantity, actor_user_id=actor_user_id,
    )
    return item


@transaction.atomic
def request_stock(*, department_code, actor_user_id, item_id, quantity):
    if quantity <= 0:
        raise ConflictError("Requested quantity must be greater than zero.")
    item = InventoryItem.objects.select_for_update().filter(
        pk=item_id, department_code=department_code,
    ).first()
    if item is None:
        raise ConflictError("The selected inventory item is unavailable.")
    if quantity > item.quantity:
        raise ConflictError("Requested quantity exceeds current inventory.")
    return StockRequest.objects.create(
        department_code=department_code, item=item,
        faculty_user_id=actor_user_id, quantity=quantity,
    )


@transaction.atomic
def decide_stock_request(*, department_code, actor_user_id, request_id,
                         decision, note=""):
    row = StockRequest.objects.select_for_update().filter(
        pk=request_id, department_code=department_code,
        status="pending_hod_approval",
    ).first()
    if row is None:
        raise ConflictError("Only a pending stock request can be decided.")
    if decision not in ("approve", "reject"):
        raise ConflictError("Decision must be approve or reject.")
    row.status = ("approved_for_issuance" if decision == "approve" else "rejected")
    row.decision_by_user_id = actor_user_id
    row.decision_note = note
    row.save(update_fields=["status", "decision_by_user_id", "decision_note",
                            "updated_at"])
    return row


@transaction.atomic
def issue_stock_request(*, department_code, actor_user_id, request_id):
    row = StockRequest.objects.select_for_update().select_related("item").filter(
        pk=request_id, department_code=department_code,
        status="approved_for_issuance",
    ).first()
    if row is None:
        raise ConflictError("Only an HOD-approved request can be issued.")
    item = InventoryItem.objects.select_for_update().get(pk=row.item_id)
    # The baseline specifies availability validation at request time and does
    # not add a second issuance check or reservation policy.
    item.quantity -= row.quantity
    item.save(update_fields=["quantity", "updated_at"])
    StockMovement.objects.create(
        department_code=department_code, item=item, request=row,
        movement="issue", quantity=row.quantity, actor_user_id=actor_user_id,
    )
    row.status = "issued"
    row.save(update_fields=["status", "updated_at"])
    return row


@transaction.atomic
def review_feedback(*, department_code, actor_user_id, feedback_id,
                    category, disposition=""):
    row = Feedback.objects.select_for_update().filter(
        pk=feedback_id, department_code=department_code, status="new",
    ).first()
    if row is None:
        raise ConflictError("Only new feedback can receive its initial review.")
    row.category = category
    row.initial_reviewed_by_user_id = actor_user_id
    row.initial_reviewed_at = timezone.now()
    row.status = disposition if disposition in ("resolved", "closed") else "under_review"
    if row.status in ("resolved", "closed"):
        row.handled_by_user_id = actor_user_id
    row.save(update_fields=["category", "initial_reviewed_by_user_id",
                            "initial_reviewed_at", "status", "handled_by_user_id",
                            "updated_at"])
    return row


@transaction.atomic
def dispose_feedback(*, department_code, actor_user_id, feedback_id, disposition):
    if disposition not in ("resolved", "closed"):
        raise ConflictError("Feedback disposition must be resolved or closed.")
    row = Feedback.objects.select_for_update().filter(
        pk=feedback_id, department_code=department_code,
        status="under_review", initial_reviewed_at__isnull=False,
    ).first()
    if row is None:
        raise ConflictError("Feedback must receive Dept_Admin review first.")
    row.status = disposition
    row.handled_by_user_id = actor_user_id
    row.save(update_fields=["status", "handled_by_user_id", "updated_at"])
    return row


@transaction.atomic
def save_timetable_entry(*, department_code, actor_user_id, entry, entry_id=None):
    row = None
    if entry_id:
        row = TimetableEntry.objects.filter(
            pk=entry_id, department_code=department_code).first()
        if row is None:
            raise ConflictError("Timetable entry was not found.")
    conflicts = TimetableEntry.objects.filter(department_code=department_code)
    if entry_id:
        conflicts = conflicts.exclude(pk=entry_id)
    if has_room_overlap(conflicts, entry):
        raise ConflictError("This room already has a timetable slot at that time.")
    if row is None:
        return TimetableEntry.objects.create(
            department_code=department_code, updated_by_user_id=actor_user_id,
            **entry,
        )
    for field, value in entry.items():
        setattr(row, field, value)
    row.updated_by_user_id = actor_user_id
    row.save()
    return row


@transaction.atomic
def decide_department_change(*, department_code, actor_user_id, change_id,
                             decision, note=""):
    if decision not in ("approve", "reject"):
        raise ConflictError("Decision must be approve or reject.")
    change = DepartmentChange.objects.select_for_update().filter(
        pk=change_id, department_code=department_code,
        status="pending_hod_approval",
    ).first()
    if change is None:
        raise ConflictError("Only a pending department change can be decided.")
    change.status = "approved" if decision == "approve" else "rejected"
    change.decided_by_user_id = actor_user_id
    change.decision_note = note
    change.save(update_fields=["status", "decided_by_user_id", "decision_note",
                               "updated_at"])
    if decision == "approve":
        details, _ = DepartmentDetails.objects.get_or_create(
            department_code=department_code)
        details.official = {**details.official,
                            change.field_name: change.proposed_value}
        details.save(update_fields=["official", "updated_at"])
    return change
