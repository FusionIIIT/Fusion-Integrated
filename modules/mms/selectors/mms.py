"""Selectors for Mess Management System (MMS)."""

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
    """Get the single currently active assignment for a given role (BR-MMS-003, BR-MMS-004)."""
    return MessRoleAssignment.objects.filter(role=role, is_active=True).first()


def list_role_assignments(role: str | None = None) -> QuerySet[MessRoleAssignment]:
    """List role assignments, optionally filtered by role."""
    qs = MessRoleAssignment.objects.all()
    if role:
        qs = qs.filter(role=role)
    return qs


def get_current_registration_window(mess_name: str = "Central Mess") -> RegistrationWindow | None:
    """Get the currently open registration window if any."""
    return RegistrationWindow.objects.filter(mess_name=mess_name, is_open=True).first()


def list_registration_windows() -> QuerySet[RegistrationWindow]:
    """List all registration windows."""
    return RegistrationWindow.objects.all()


def get_student_registration(student_id: int) -> MessRegistration | None:
    """Get the active or latest registration for a student."""
    return MessRegistration.objects.filter(student_id=student_id).order_by("-created_at").first()


def list_registrations(
    status: str | None = None,
    mess_name: str | None = None,
) -> QuerySet[MessRegistration]:
    """List student registrations with optional filters."""
    qs = MessRegistration.objects.all()
    if status:
        qs = qs.filter(status=status)
    if mess_name:
        qs = qs.filter(mess_name=mess_name)
    return qs.order_by("-created_at")


def get_weekly_menu(mess_name: str = "Central Mess") -> QuerySet[DailyMenuItem]:
    """Get active weekly menu items for a mess."""
    return DailyMenuItem.objects.filter(mess_name=mess_name, is_active=True)


def list_rebate_requests(
    student_id: int | None = None,
    status: str | None = None,
) -> QuerySet[RebateRequest]:
    """List rebate requests with optional student or status filtering."""
    qs = RebateRequest.objects.all()
    if student_id:
        qs = qs.filter(student_id=student_id)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


def list_feedbacks(mess_name: str | None = None) -> QuerySet[MessFeedback]:
    """List feedbacks for mess oversight."""
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
    return qs
