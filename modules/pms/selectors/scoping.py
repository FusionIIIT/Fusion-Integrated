"""Row-level scoping and security filtering for PMS (BR-PMS-003, 005, 006, 126, 130).

Enforces row-level authorization in querysets: unauthorized objects return 404
rather than disclosing existence with a 403.
"""

from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.pms.models import (
    ApplicationDocument,
    DirectorAssignment,
    OfficeAction,
    PatentApplication,
    PatentAuditLog,
)

# Permission codes
P_APPLICATION_VIEW = "pms.application.view"
P_APPLICATION_ASSIGN = "pms.application.assign"
P_APPLICATION_REVIEW = "pms.application.review"
P_ATTORNEY_REVIEW = "pms.attorney.review"
P_AUDIT_VIEW = "pms.audit.view"
P_REPORT_VIEW = "pms.report.view"


def has_permission(actor, code: str) -> bool:
    if actor is None:
        return False
    checker = getattr(actor, "has_permission", None)
    if callable(checker):
        return checker(code)
    perms = getattr(actor, "permissions", None)
    if perms is not None:
        return code in perms
    return False


def is_pcc_admin(actor) -> bool:
    return (
        has_permission(actor, P_APPLICATION_ASSIGN)
        or has_permission(actor, "pms.attorney.assign")
        or has_permission(actor, "pms.budget.manage")
        or has_permission(actor, "pms.maintenance.manage")
        or has_permission(actor, "pms.attorney_panel.manage")
    )


def is_director(actor) -> bool:
    return has_permission(actor, P_APPLICATION_REVIEW)


def is_attorney(actor) -> bool:
    return (
        has_permission(actor, P_ATTORNEY_REVIEW)
        or has_permission(actor, "pms.filing.create")
        or has_permission(actor, "pms.office_action.create")
        or has_permission(actor, "pms.office_action.update")
    )


def get_actor_user_id(actor) -> int:
    uid = getattr(actor, "user_id", None)
    if uid is None:
        raise ValueError("Actor has no authenticated user_id.")
    return int(uid)


def scoped_applications(actor) -> QuerySet[PatentApplication]:
    """Return applications visible to the given actor based on role and ownership.

    - PCC_ADMIN sees all applications.
    - Director sees applications in their domain or assigned to them.
    - Attorney sees applications assigned to them or ready for filing/prosecution.
    - Applicant sees only applications they submitted or are listed on as an inventor.
    """
    if actor is None:
        return PatentApplication.objects.none()

    qs = PatentApplication.objects.all().prefetch_related("inventors")

    if is_pcc_admin(actor):
        return qs

    user_id = getattr(actor, "user_id", None)
    if user_id is None:
        return PatentApplication.objects.none()

    q_filters = Q(user_id=user_id) | Q(inventors__user_id=user_id)

    if is_director(actor) or has_permission(actor, "pms.budget.approve"):
        # Applications assigned to this director or ready for director review
        assigned_app_ids = DirectorAssignment.objects.filter(director_user_id=user_id).values_list(
            "application_id", flat=True
        )
        q_filters |= Q(id__in=assigned_app_ids)
        if has_permission(actor, "pms.budget.approve"):
            q_filters |= Q(
                status__in=[
                    "approved",
                    "attorney_assigned",
                    "budget_escalated",
                    "budget_approved",
                ]
            )

    if is_attorney(actor):
        # Applications assigned to this attorney
        from modules.pms.models import AttorneyAssignment

        assigned_to_attorney = AttorneyAssignment.objects.filter(
            attorney_user_id=user_id, status__in=["offered", "accepted"]
        ).values_list("application_id", flat=True)
        q_filters |= Q(id__in=assigned_to_attorney)

    return qs.filter(q_filters).distinct()


def scoped_documents(
    actor, application: PatentApplication | None = None
) -> QuerySet[ApplicationDocument]:
    """Documents visible for a given application under confidentiality rules (BR-PMS-130)."""
    if actor is None:
        return ApplicationDocument.objects.none()

    if application is not None:
        docs = application.documents.all()
    else:
        visible_app_ids = scoped_applications(actor).values_list("id", flat=True)
        docs = ApplicationDocument.objects.filter(application_id__in=visible_app_ids)

    # Restricted documents visible only to PCC_ADMIN and assigned Director/Attorney
    if is_pcc_admin(actor) or is_director(actor) or is_attorney(actor):
        return docs

    user_id = getattr(actor, "user_id", None)
    if application is not None:
        if user_id == application.user_id or application.inventors.filter(user_id=user_id).exists():
            return docs.exclude(sensitivity="restricted")
        return docs.filter(sensitivity="standard")

    # If application is None, filter by ownership
    owned_app_ids = PatentApplication.objects.filter(
        Q(user_id=user_id) | Q(inventors__user_id=user_id)
    ).values_list("id", flat=True)
    return docs.filter(
        Q(application_id__in=owned_app_ids, sensitivity__in=["standard", "confidential"])
        | Q(sensitivity="standard")
    )


def scoped_office_actions(actor) -> QuerySet[OfficeAction]:
    """Office actions visible to actor."""
    app_ids = scoped_applications(actor).values_list("id", flat=True)
    return OfficeAction.objects.filter(application_id__in=app_ids)


def scoped_audit_logs(
    actor, application: PatentApplication | None = None
) -> QuerySet[PatentAuditLog]:
    """Audit logs visible to actor (BR-PMS-006, 122)."""
    if application is not None:
        return application.audit_logs.all().order_by("-created_at")

    if not has_permission(actor, P_AUDIT_VIEW):
        return PatentAuditLog.objects.none()
    return PatentAuditLog.objects.all().order_by("-created_at")
