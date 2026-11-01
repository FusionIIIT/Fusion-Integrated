"""Query selectors for the Mess Management System (MMS)."""

from django.db.models import QuerySet

from modules.mms.models import (
    DailyMenuItem,
    MessActionLog,
    MessFeedback,
    MessRegistration,
    MessRoleAssignment,
    RebateRequest,
    RegistrationWindow,
)


def get_active_role_assignment(role: str) -> MessRoleAssignment | None:
    """Return the single active role assignment for the given role."""
    return MessRoleAssignment.objects.filter(role=role, is_active=True).first()


def list_role_assignments(role: str | None = None) -> QuerySet[MessRoleAssignment]:
    """List role assignments, optionally filtered by role."""
    qs = MessRoleAssignment.objects.all()
    if role:
        qs = qs.filter(role=role)
    return qs.order_by("-created_at")


def get_current_registration_window(
    mess_name: str = "Central Mess",
) -> RegistrationWindow | None:
    """Return the currently open registration window for the given mess."""
    return RegistrationWindow.objects.filter(mess_name=mess_name, is_open=True).first()


def get_student_registration(student_id: int) -> MessRegistration | None:
    """Return the current active or pending registration for a student."""
    return MessRegistration.objects.filter(student_id=student_id).order_by("-created_at").first()


def list_registrations(
    mess_name: str | None = None,
    status: str | None = None,
) -> QuerySet[MessRegistration]:
    """List registrations filtered by mess facility or status."""
    qs = MessRegistration.objects.all()
    if mess_name:
        qs = qs.filter(mess_name=mess_name)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


def get_weekly_menu(mess_name: str = "Central Mess") -> QuerySet[DailyMenuItem]:
    """Return all menu items for a mess ordered by day and meal time."""
    return DailyMenuItem.objects.filter(mess_name=mess_name, is_active=True)


def list_rebate_requests(
    student_id: int | None = None,
    status: str | None = None,
) -> QuerySet[RebateRequest]:
    """List rebate requests filtered by student or status."""
    qs = RebateRequest.objects.all()
    if student_id:
        qs = qs.filter(student_id=student_id)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


def list_feedbacks(mess_name: str | None = None) -> QuerySet[MessFeedback]:
    """List feedback submissions for a mess."""
    qs = MessFeedback.objects.all()
    if mess_name:
        qs = qs.filter(mess_name=mess_name)
    return qs.order_by("-created_at")


def list_action_logs(
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> QuerySet[MessActionLog]:
    """List audit logs for an entity."""
    qs = MessActionLog.objects.all()
    if entity_type:
        qs = qs.filter(entity_type=entity_type)
    if entity_id:
        qs = qs.filter(entity_id=entity_id)
    return qs.order_by("-created_at")
