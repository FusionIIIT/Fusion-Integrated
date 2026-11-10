"""SPACS Selectors - Read models with ownership and scope enforcement."""

from ..domain.rules import assert_ownership, check_application_review_access
from ..models import (
    SpacsApplication,
    SpacsAuditLog,
    SpacsAwardCycle,
    SpacsCatalogueEntry,
)


def visible_catalogue():
    """All users may browse published schemes (AFR-SPACS-001)."""
    return SpacsCatalogueEntry.objects.filter(status="published")


def visible_applications_for_student(student_user_id: int):
    """Students see only their own applications (AFR-SPACS-035, BR-SPACS-010)."""
    return SpacsApplication.objects.filter(applicant_user_id=student_user_id).order_by("-created_at")


def get_application_by_id(application_id: str, acting_user_id: int, user_roles: list[str]):
    """Fetch application if owned by student or if staff has review access (BR-SPACS-005, 010)."""
    app = SpacsApplication.objects.get(application_id=application_id)
    if app.applicant_user_id != acting_user_id:
        check_application_review_access(user_roles)
    return app


def get_verification_queue(assistant_user_id: int | None = None):
    """List applications pending verification."""
    qs = SpacsApplication.objects.filter(
        state__in=["submitted", "resubmitted", "renewal_submitted"]
    )
    if assistant_user_id:
        qs = qs.filter(verification_assigned_to_user_id=assistant_user_id)
    return qs


def get_convener_queue():
    """List applications ready for convener decision."""
    return SpacsApplication.objects.filter(
        state__in=["verified", "verification_concern", "renewal_verified"]
    )


def get_audit_trail_for_auditor(user_roles: list[str]):
    """Restrict audit trail view to authorized roles (AFR-SPACS-050, BR-SPACS-021)."""
    if not any(r in {"spacs_convener", "spacs_auditor", "admin"} for r in user_roles):
        raise PermissionError("Access to audit trail restricted to authorized personnel.")
    return SpacsAuditLog.objects.all().order_by("-timestamp")
