from django.db.models import Q

from fusion_auth.client import get_client
from modules.department.models import Announcement, Feedback, Notice, StockItem, StockRequest
from modules.department.roles import ADMIN_DEPARTMENTS, HOD_DEPARTMENTS


def live_identity(principal):
    viewer = get_client().get_users([principal.user_id]).get(principal.user_id)
    return viewer if viewer and viewer.is_active else None


def department_for(principal, viewer):
    if viewer is None:
        return ""
    role = principal.active_role
    return (HOD_DEPARTMENTS.get(role) or ADMIN_DEPARTMENTS.get(role)
            or viewer.department.strip())


def _matches_target(field, value):
    unrestricted = Q(**{field: []})
    if value is None or value == "":
        return unrestricted
    return unrestricted | Q(**{f"{field}__contains": [value]})


def visible_announcements(principal):
    """Apply BR-DEPT-002 using live IAM membership and the current acting role."""
    viewer = live_identity(principal)
    return _relevant_announcements(principal, viewer, department_for(principal, viewer))


def manageable_announcements(principal):
    department = department_for(principal, live_identity(principal))
    if department and principal.active_role in HOD_DEPARTMENTS:
        return Announcement.objects.filter(department=department, is_active=True)
    return Announcement.objects.none()


def _relevant_announcements(principal, viewer, department):
    if not department:
        return Announcement.objects.none()
    return Announcement.objects.filter(
        _matches_target("target_roles", principal.active_role or principal.kind),
        _matches_target("target_programmes", viewer.programme),
        _matches_target("target_batch_years", viewer.batch_year),
        department=department,
        is_active=True,
    )


def stock_items_for(principal):
    department = department_for(principal, live_identity(principal))
    if not department:
        return StockItem.objects.none()
    return StockItem.objects.filter(department=department)


def stock_requests_for(principal):
    department = department_for(principal, live_identity(principal))
    if not department:
        return StockRequest.objects.none()
    requests = StockRequest.objects.filter(item__department=department).select_related("item")
    if principal.active_role in HOD_DEPARTMENTS:
        return requests.filter(status=StockRequest.Status.PENDING)
    if principal.active_role in ADMIN_DEPARTMENTS:
        return requests.filter(status=StockRequest.Status.APPROVED)
    return requests.filter(user_id=principal.user_id, status=StockRequest.Status.ISSUED)


def feedback_for(principal):
    department = department_for(principal, live_identity(principal))
    if not department:
        return Feedback.objects.none()
    feedback = Feedback.objects.filter(department=department)
    if principal.active_role in ADMIN_DEPARTMENTS:
        return feedback
    if principal.active_role in HOD_DEPARTMENTS:
        return feedback.exclude(status=Feedback.Status.NEW)
    return feedback.none()


def notices_for(principal):
    viewer = live_identity(principal)
    department = department_for(principal, viewer)
    if not department:
        return Notice.objects.none()
    audience = Q(user_id=principal.user_id)
    if principal.active_role in HOD_DEPARTMENTS:
        audience |= Q(audience="hod")
    if principal.active_role in ADMIN_DEPARTMENTS:
        audience |= Q(audience="admin")
    if principal.kind in ("student", "faculty"):
        audience |= Q(announcement__in=_relevant_announcements(principal, viewer, department))
    return Notice.objects.filter(audience, department=department)
