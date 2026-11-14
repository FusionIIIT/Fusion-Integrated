
from modules.department.models import (
    Announcement,
    Department,
    DepartmentProfile,
    Feedback,
    InventoryItem,
    LabResource,
    Timetable,
)


def announcements_for(principal, department_id=None):
    qs = Announcement.objects.all()
    if department_id:
        qs = qs.filter(department_id=department_id)
    if not principal.has_permission("department.announcement.manage"):
        qs = qs.filter(is_hidden=False)
    return qs.order_by("-created_at")


def feedback_for(principal):
    if principal.has_permission("department.feedback.review") or principal.has_permission(
        "department.feedback.resolve"
    ):
        return Feedback.objects.all().order_by("-created_at")
    return Feedback.objects.filter(submitter_user_id=principal.user_id).order_by("-created_at")


def profiles_for(principal, department_id=None):
    qs = DepartmentProfile.objects.all()
    if department_id:
        qs = qs.filter(department_id=department_id)
    if not (principal.has_permission("department.profile.view")):
        return qs.none()
    return qs.order_by("user_id")


def inventory_for(department_id=None):
    qs = InventoryItem.objects.all()
    if department_id:
        qs = qs.filter(department_id=department_id)
    return qs.order_by("name")


def resources_for(department_id=None):
    qs = LabResource.objects.all()
    if department_id:
        qs = qs.filter(department_id=department_id)
    return qs.order_by("name")


def timetables_for(department_id=None):
    qs = Timetable.objects.all()
    if department_id:
        qs = qs.filter(department_id=department_id)
    return qs.order_by("-created_at")


def department_details_for(department_id=None):
    qs = Department.objects.all()
    if department_id:
        qs = qs.filter(id=department_id)
    return qs.order_by("name")
