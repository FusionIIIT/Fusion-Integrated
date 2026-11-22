import logging

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from fusion_auth.client import IamUnavailable, get_client
from modules.dept.domain import transition
from modules.dept.models import (
    Announcement,
    Department,
    DepartmentChange,
    Feedback,
    InventoryItem,
    Notification,
    StockMovement,
    StockRequest,
    UserProfile,
)
from modules.directory.contracts import get_users, users_in_department

logger = logging.getLogger(__name__)


def require(actor, permission, role=None):
    if not actor.has_permission(permission) or (role and actor.active_role != role):
        raise PermissionDeniedError(
            "Your active role cannot perform this action.", code="permission_denied"
        )


def department_scope(actor, department_code=None, roles=()):
    code = (department_code or "").strip().upper()
    if actor.active_role in {"HOD", "Dept_Admin"}:
        matches = [
            a
            for a in actor.department_assignments
            if a.get("role") == actor.active_role and (not code or a.get("department_code") == code)
        ]
        if len(matches) != 1:
            raise NotFoundError("No department is available in your active role.")
        if roles and actor.active_role not in roles:
            raise PermissionDeniedError(
                "This action is not available in your active role.", code="role_not_allowed"
            )
        row = matches[0]
        department, _ = Department.objects.get_or_create(
            code=row["department_code"],
            defaults={"name": row.get("department_name") or row["department_code"]},
        )
        return department
    if actor.kind not in {"student", "faculty", "staff"}:
        raise NotFoundError("No department is available for this account.")
    identity = get_users([actor.user_id]).get(actor.user_id)
    if identity is None or not identity.department:
        raise NotFoundError("Your directory profile has no department.")
    department = Department.objects.filter(name__iexact=identity.department).first()
    if department is None or (code and department.code != code):
        raise NotFoundError("No department is available for this account.")
    return department


def notify(department, recipients, event, subject, body):
    ids = sorted({int(uid) for uid in recipients if uid is not None})
    return [
        Notification.objects.create(
            department=department,
            recipient_user_id=uid,
            event=event,
            subject=subject[:180],
            body=body,
        )
        for uid in ids
    ]


def officeholders(department, role):
    try:
        appointments = get_client().get_department_appointments(department.code)
    except IamUnavailable:
        # Reviewer discovery is ancillary to accepting feedback. Keep the
        # business record and surface the missing IAM integration in logs.
        logger.exception(
            "dept.reviewers.lookup_failed",
            extra={"department_code": department.code, "role": role},
        )
        return []
    return [int(a["user_id"]) for a in appointments if a.get("role") == role]


def create_announcement(*, actor, department, data):
    require(actor, "dept.announcement.create")
    if not data.get("title", "").strip() or not data.get("body", "").strip():
        raise ConflictError("Enter a title and message before publishing.", code="content_required")
    target_roles = data.get("target_roles") or ["student", "faculty"]
    if not isinstance(target_roles, list) or set(target_roles) - {"student", "faculty", "staff"}:
        raise ConflictError("Choose a supported announcement audience.", code="bad_audience")
    announcement = Announcement.objects.create(
        department=department,
        author_user_id=actor.user_id,
        title=data["title"].strip(),
        body=data["body"].strip(),
        target_roles=target_roles,
        programme=(data.get("programme") or "").strip(),
        academic_year=(data.get("academic_year") or "").strip(),
    )
    recipients = users_in_department(
        department=(department.code, department.name),
        kinds=target_roles,
        programme=announcement.programme,
        batch_year=int(announcement.academic_year)
        if announcement.academic_year.isdigit()
        else None,
    )
    notify(
        department,
        recipients,
        "announcement.published",
        announcement.title,
        announcement.body[:1000],
    )
    return announcement


@transaction.atomic
def stock_insert(*, actor, department, item_id, name, description, quantity):
    require(actor, "dept.stock_item.create", "Dept_Admin")
    if quantity < 1:
        raise ConflictError("Quantity must be greater than zero.", code="invalid_quantity")
    item = (
        InventoryItem.objects.select_for_update().filter(pk=item_id, department=department).first()
        if item_id
        else None
    )
    if item is None:
        if item_id:
            raise NotFoundError("Inventory item was not found.")
        item = InventoryItem.objects.create(
            department=department,
            name=name.strip(),
            description=description.strip(),
            on_hand=quantity,
        )
    else:
        item.on_hand = F("on_hand") + quantity
        item.save(update_fields=["on_hand", "updated_at"])
        item.refresh_from_db()
    StockMovement.objects.create(
        department=department,
        item=item,
        kind="insert",
        quantity=quantity,
        actor_user_id=actor.user_id,
    )
    return item


@transaction.atomic
def request_stock(*, actor, department, item_id, quantity, purpose=""):
    require(actor, "dept.stock_request.create", "faculty")
    if quantity < 1:
        raise ConflictError(
            "Requested quantity must be greater than zero.", code="invalid_quantity"
        )
    item = (
        InventoryItem.objects.select_for_update()
        .filter(pk=item_id, department=department, active=True)
        .first()
    )
    if item is None:
        raise NotFoundError("Inventory item was not found.")
    if item.on_hand - item.reserved < quantity:
        raise ConflictError(
            "Available stock is insufficient. Reduce the quantity or contact "
            "the department administrator.",
            code="insufficient_stock",
        )
    request = StockRequest.objects.create(
        department=department,
        item=item,
        requester_user_id=actor.user_id,
        quantity=quantity,
        purpose=purpose.strip(),
    )
    recipients = officeholders(department, "Dept_Admin")
    recipients.extend(officeholders(department, "HOD"))
    notify(
        department,
        recipients,
        "stock.requested",
        "Stock request requires review",
        f"A faculty member requested {quantity} x {item.name}.",
    )
    return request


@transaction.atomic
def decide_stock(*, actor, request_id, department, approve):
    require(actor, "dept.stock_request.approve", "HOD")
    req = (
        StockRequest.objects.select_for_update()
        .filter(pk=request_id, department=department)
        .first()
    )
    if req is None:
        raise NotFoundError("Stock request was not found.")
    if req.status != "pending":
        raise ConflictError("This request has already been decided.", code="invalid_transition")
    item = InventoryItem.objects.select_for_update().get(pk=req.item_id)
    if approve:
        if item.on_hand - item.reserved < req.quantity:
            raise ConflictError(
                "Available stock changed. Reject this request or reduce its quantity.",
                code="insufficient_stock",
            )
        item.reserved = F("reserved") + req.quantity
        item.save(update_fields=["reserved", "updated_at"])
        item.refresh_from_db()
        req.status = transition(req.status, "approve", actor.active_role)
        StockMovement.objects.create(
            department=department,
            item=item,
            request=req,
            kind="reserve",
            quantity=req.quantity,
            actor_user_id=actor.user_id,
        )
    else:
        req.status = transition(req.status, "reject", actor.active_role)
    req.decided_by_user_id = actor.user_id
    req.save(update_fields=["status", "decided_by_user_id", "updated_at"])
    if approve:
        notify(
            department,
            officeholders(department, "Dept_Admin"),
            "stock.approved",
            "Stock request approved",
            "A stock request is approved and ready for issuance.",
        )
    if not approve:
        notify(
            department,
            [req.requester_user_id],
            "stock.rejected",
            "Stock request rejected",
            "Your stock request was rejected.",
        )
    return req


@transaction.atomic
def issue_stock(*, actor, request_id, department):
    require(actor, "dept.stock_request.update", "Dept_Admin")
    req = (
        StockRequest.objects.select_for_update()
        .filter(pk=request_id, department=department)
        .first()
    )
    if req is None:
        raise NotFoundError("Stock request was not found.")
    if req.status != "approved":
        raise ConflictError("Only an approved request can be issued.", code="invalid_transition")
    item = InventoryItem.objects.select_for_update().get(pk=req.item_id)
    if item.reserved < req.quantity or item.on_hand < req.quantity:
        raise ConflictError(
            "The reserved stock is unavailable. Contact the department administrator.",
            code="stock_invariant",
        )
    item.on_hand = F("on_hand") - req.quantity
    item.reserved = F("reserved") - req.quantity
    item.save(update_fields=["on_hand", "reserved", "updated_at"])
    req.status = transition(req.status, "issue", actor.active_role)
    req.issued_by_user_id = actor.user_id
    req.save(update_fields=["status", "issued_by_user_id", "updated_at"])
    StockMovement.objects.create(
        department=department,
        item=item,
        request=req,
        kind="issue",
        quantity=req.quantity,
        actor_user_id=actor.user_id,
    )
    notify(
        department,
        [req.requester_user_id],
        "stock.issued",
        "Stock request issued",
        "Your approved stock request has been issued.",
    )
    return req


@transaction.atomic
def submit_feedback(*, actor, department, title, body):
    require(actor, "dept.feedback.create")
    if not title.strip() or not body.strip():
        raise ConflictError(
            "Enter a subject and feedback before submitting.", code="content_required"
        )
    feedback = Feedback.objects.create(
        department=department,
        submitter_user_id=actor.user_id,
        title=title.strip(),
        body=body.strip(),
    )
    notify(
        department,
        officeholders(department, "Dept_Admin"),
        "feedback.submitted",
        "New department feedback",
        "A confidential feedback submission needs initial review.",
    )
    return feedback


@transaction.atomic
def review_feedback(*, actor, department, feedback_id, action, category="", resolution=""):
    require(actor, "dept.feedback.review", actor.active_role)
    fb = Feedback.objects.select_for_update().filter(pk=feedback_id, department=department).first()
    if fb is None:
        raise NotFoundError("Feedback was not found.")
    role = actor.active_role
    if action == "review":
        if not category.strip():
            raise ConflictError(
                "Choose a category during the initial review.", code="category_required"
            )
        fb.status = transition(fb.status, action, role)
        fb.category = category.strip()
        fb.reviewed_by_user_id = actor.user_id
    else:
        if role == "HOD" and not fb.reviewed_by_user_id:
            raise ConflictError(
                "Department Admin must complete the initial review first.",
                code="initial_review_required",
            )
        fb.status = transition(fb.status, action, role)
        if not resolution.strip():
            raise ConflictError("Enter a resolution or closure note.", code="resolution_required")
        fb.resolution = resolution.strip()
        fb.closed_at = timezone.now()
        notify(
            department,
            [fb.submitter_user_id],
            "feedback.resolved",
            "Feedback updated",
            "Your feedback has reached a final outcome.",
        )
    fb.save()
    return fb


@transaction.atomic
def decide_department_change(*, actor, department, change_id, approve, note=""):
    require(actor, "dept.department.approve", "HOD")
    change = (
        DepartmentChange.objects.select_for_update()
        .filter(pk=change_id, department=department, status="pending")
        .first()
    )
    if change is None:
        raise NotFoundError("Pending department change was not found.")
    change.status = transition(
        "pending", "approve_detail" if approve else "reject_detail", actor.active_role
    )
    change.decided_by_user_id = actor.user_id
    change.decision_note = note.strip()
    change.decided_at = timezone.now()
    change.save()
    if approve:
        department.official_info = {**department.official_info, **change.proposed}
        department.save(update_fields=["official_info", "updated_at"])
    return change


def visible_feedback(actor, department):
    qs = Feedback.objects.filter(department=department)
    if actor.active_role in {"HOD", "Dept_Admin"}:
        return qs
    return qs.filter(submitter_user_id=actor.user_id)


def visible_profiles(actor, department):
    qs = UserProfile.objects.filter(department=department)
    if actor.active_role == "Dept_Admin":
        return qs
    identity = get_users([actor.user_id]).get(actor.user_id)
    return (
        qs.filter(kind__in=("faculty", "alumni"))
        if identity and identity.kind == "student"
        else qs.filter(user_id=actor.user_id)
    )
