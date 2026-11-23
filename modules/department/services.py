from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.department import permissions as p
from modules.department.domain import FEEDBACK_TRANSITIONS, STOCK_TRANSITIONS
from modules.department.models import (
    Announcement,
    Feedback,
    Notice,
    StockItem,
    StockMovement,
    StockRequest,
)
from modules.department.roles import (
    ADMIN_DEPARTMENTS,
    HOD_DEPARTMENTS,
    STUDENT_ROLES,
    acting_role,
    office_lane,
)
from modules.department.selectors import department_for, live_identity


def _department(actor, permission, roles):
    if (not actor.has_module("department") or not actor.has_permission(permission)
            or acting_role(actor) not in roles):
        raise PermissionDeniedError()
    department = department_for(actor, live_identity(actor))
    if not department:
        raise PermissionDeniedError("Contact your department office to verify your membership.")
    return department


def _next_state(transitions, current, action, lane):
    state = transitions.get((current, action, lane))
    if state is None:
        raise ConflictError("Refresh the record and choose an action allowed in its current state.")
    return state


@transaction.atomic
def publish_announcement(*, actor, content, target_roles, target_programmes, target_batch_years):
    department = _department(actor, p.PUBLISH_ANNOUNCEMENT,
                             {"faculty", *HOD_DEPARTMENTS, *ADMIN_DEPARTMENTS})
    announcement = Announcement.objects.create(
        department=department, content=content, target_roles=target_roles,
        target_programmes=target_programmes, target_batch_years=target_batch_years,
    )
    Notice.objects.create(department=department, announcement=announcement,
                          message="A Department announcement was published.")
    return announcement


@transaction.atomic
def maintain_announcement(*, actor, announcement_id, action, changes=None):
    department = _department(actor, p.MANAGE_ANNOUNCEMENT, HOD_DEPARTMENTS)
    announcement = Announcement.objects.select_for_update().filter(
        pk=announcement_id, department=department, is_active=True,
    ).first()
    if announcement is None:
        raise NotFoundError()
    if action == "delete":
        announcement.delete()
    elif action == "hide":
        announcement.is_active = False
        announcement.save(update_fields=["is_active"])
    elif action == "edit":
        announcement.content = changes["content"]
        announcement.target_roles = changes["target_roles"]
        announcement.target_programmes = changes["target_programmes"]
        announcement.target_batch_years = changes["target_batch_years"]
        announcement.save(update_fields=["content", "target_roles", "target_programmes",
                                         "target_batch_years"])
    else:
        raise ConflictError("Choose edit, hide or delete for this announcement.")


@transaction.atomic
def insert_stock(*, actor, name, quantity):
    department = _department(actor, p.INSERT_STOCK, ADMIN_DEPARTMENTS)
    item, created = StockItem.objects.get_or_create(
        department=department, name=name, defaults={"quantity": quantity},
    )
    if not created:
        StockItem.objects.filter(pk=item.pk).update(quantity=F("quantity") + quantity)
        item.refresh_from_db(fields=["quantity"])
    StockMovement.objects.create(item=item, actor_id=actor.user_id, delta=quantity)
    return item


@transaction.atomic
def request_stock(*, actor, item_id, quantity):
    department = _department(actor, p.REQUEST_STOCK, {"faculty"})
    item = StockItem.objects.select_for_update().filter(pk=item_id, department=department).first()
    if item is None:
        raise NotFoundError()
    if quantity > item.quantity:
        raise ConflictError("Request a quantity no greater than the current inventory.")
    request = StockRequest.objects.create(item=item, user_id=actor.user_id, quantity=quantity)
    Notice.objects.bulk_create([
        Notice(department=department, audience="admin", message="A stock request was submitted."),
        Notice(department=department, audience="hod", message="A stock request needs review."),
    ])
    return request


@transaction.atomic
def advance_stock_request(*, actor, request_id, action):
    if action == "issue":
        department = _department(actor, p.ISSUE_STOCK, ADMIN_DEPARTMENTS)
    else:
        department = _department(actor, p.REVIEW_STOCK, HOD_DEPARTMENTS)
    request = StockRequest.objects.select_for_update().filter(
        pk=request_id, item__department=department,
    ).first()
    if request is None:
        raise NotFoundError()
    state = _next_state(STOCK_TRANSITIONS, request.status, action, office_lane(actor))
    if action == "issue":
        item = StockItem.objects.select_for_update().get(pk=request.item_id)
        if item.quantity < request.quantity:
            raise ConflictError("Available stock has changed. Add stock before issuing.")
        item.quantity -= request.quantity
        item.save(update_fields=["quantity"])
        StockMovement.objects.create(item=item, request=request, delta=-request.quantity,
                                     actor_id=actor.user_id)
    else:
        request.decided_by_id = actor.user_id
        request.decided_at = timezone.now()
    request.status = state
    request.save(update_fields=["status", "decided_by_id", "decided_at"])
    if state in {StockRequest.Status.ISSUED, StockRequest.Status.REJECTED}:
        Notice.objects.create(department=department, user_id=request.user_id,
                              message=f"Stock request #{request.pk} was {state}.")
    return request


@transaction.atomic
def submit_feedback(*, actor, content):
    department = _department(actor, p.SUBMIT_FEEDBACK, {*STUDENT_ROLES, "faculty"})
    feedback = Feedback.objects.create(
        department=department, user_id=actor.user_id, content=content,
    )
    Notice.objects.create(department=department, audience="admin",
                          message="Department feedback was submitted.")
    return feedback


@transaction.atomic
def advance_feedback(*, actor, feedback_id, action, category="", close_simple=False,
                     oversight_notes=""):
    reviewing = action == "review"
    overseeing = action == "record_oversight"
    roles = ADMIN_DEPARTMENTS if reviewing else {**ADMIN_DEPARTMENTS, **HOD_DEPARTMENTS}
    if overseeing:
        roles = HOD_DEPARTMENTS
    department = _department(actor, p.REVIEW_FEEDBACK if reviewing else p.DISPOSE_FEEDBACK, roles)
    queryset = Feedback.objects.select_for_update().filter(pk=feedback_id, department=department)
    if actor.active_role in HOD_DEPARTMENTS:
        queryset = queryset.exclude(status=Feedback.Status.NEW)
    feedback = queryset.first()
    if feedback is None:
        raise NotFoundError()
    feedback.status = _next_state(FEEDBACK_TRANSITIONS, feedback.status, action, office_lane(actor))
    now = timezone.now()
    if reviewing:
        if not category.strip():
            raise ConflictError("Choose a category before completing the initial review.")
        feedback.category = category
        feedback.reviewed_at = now
        feedback.reviewed_by_id = actor.user_id
        if close_simple:
            feedback.status = _next_state(
                FEEDBACK_TRANSITIONS, feedback.status, "close", office_lane(actor),
            )
    if overseeing:
        if feedback.oversight_at is not None:
            raise ConflictError("HOD oversight has already been recorded for this feedback.")
        feedback.oversight_at = now
        feedback.oversight_by_id = actor.user_id
        feedback.oversight_notes = oversight_notes
    if feedback.status in {Feedback.Status.CLOSED, Feedback.Status.RESOLVED}:
        feedback.disposed_at = now
        feedback.disposed_by_id = actor.user_id
        Notice.objects.create(department=department, user_id=feedback.user_id,
                              message=f"Feedback #{feedback.pk} was {feedback.status}.")
    feedback.save()
    return feedback
