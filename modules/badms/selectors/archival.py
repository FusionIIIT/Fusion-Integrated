"""Read-only selectors for archival requests and special archival records."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.badms.models import ArchivalRequest, SpecialArchivalRecord


def list_archival_requests(
    *,
    user_id: int | None = None,
    department_id: int | None = None,
    status: str | None = None,
) -> QuerySet[ArchivalRequest]:
    qs = ArchivalRequest.objects.all().order_by("-created_at")
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    if department_id is not None:
        qs = qs.filter(department_id=department_id)
    if status:
        qs = qs.filter(status=status)
    return qs


def get_archival_request_by_id(request_id: int) -> ArchivalRequest | None:
    return ArchivalRequest.objects.filter(id=request_id).first()


def list_hod_archival_queue(department_id: int) -> QuerySet[ArchivalRequest]:
    """Requests pending HoD review for the specific department."""
    return ArchivalRequest.objects.filter(
        department_id=department_id,
        status="submitted",
    ).order_by("-created_at")


def list_sysadmin_classification_queue() -> QuerySet[ArchivalRequest]:
    """HoD-approved requests waiting for SysAdmin authoritative classification."""
    return ArchivalRequest.objects.filter(status="hod_approved").order_by("-created_at")


def list_it_security_encryption_queue() -> QuerySet[ArchivalRequest]:
    """Sensitive requests waiting for IT Security encryption."""
    return ArchivalRequest.objects.filter(status="classified_sensitive").order_by("-created_at")


def list_special_archival_records() -> QuerySet[SpecialArchivalRecord]:
    return SpecialArchivalRecord.objects.all().order_by("-created_at")
