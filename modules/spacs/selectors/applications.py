"""Selectors for scholarship applications.

Ownership and scope filtering live here — a foreign ID yields 404, not 403.
"""
from __future__ import annotations

from collections.abc import Sequence
from django.db.models import Q, QuerySet

from modules.spacs.models import ApplicationDocument, ScholarshipApplication


def visible_applications(principal) -> QuerySet[ScholarshipApplication]:
    """Visible applications for the caller.

    - Convener (spacs.application.approve): can see all applications in the module.
    - Assistant (spacs.application.review): can see submitted, under_verification,
      resubmitted, verified, or verification_concern applications.
    - Student (spacs.application.view_self): can see ONLY their own applications.
    """
    qs = ScholarshipApplication.objects.select_related("scheme", "policy_version")
    if principal is None:
        return qs.none()

    if principal.has_permission("spacs.application.approve"):
        return qs

    if principal.has_permission("spacs.application.review"):
        return qs.filter(
            Q(status__in=[
                "submitted",
                "under_verification",
                "resubmitted",
                "verified",
                "verification_concern",
                "correction_required",
            ]) | Q(assigned_assistant_user_id=principal.user_id)
        )

    # Student ownership
    return qs.filter(student_user_id=principal.user_id)


def get_application(application_id: int, principal) -> ScholarshipApplication | None:
    return visible_applications(principal).filter(pk=application_id).first()


def visible_documents(application_id: int, principal) -> QuerySet[ApplicationDocument]:
    app = get_application(application_id, principal)
    if app is None:
        return ApplicationDocument.objects.none()
    return ApplicationDocument.objects.filter(application_id=application_id)


def get_reusable_documents(student_user_id: int, doc_type: str | None = None) -> QuerySet[ApplicationDocument]:
    """Retrieves previous still-valid documents belonging to the student (BR-SPACS-003)."""
    qs = ApplicationDocument.objects.filter(
        student_user_id=student_user_id,
        verification_status="verified",
    ).order_by("-created_at")
    if doc_type:
        qs = qs.filter(doc_type=doc_type)
    return qs
