"""Scoping enforces IAA-BR-501 visibility and IAA-BR-004 sysadmin separation."""

from django.db.models import QuerySet

from modules.iaa.models import (
    Anomaly,
    AuditObservation,
    ExpenseVoucherRequest,
    TAClaim,
)


def scope_requests(
    queryset: QuerySet[ExpenseVoucherRequest], principal
) -> QuerySet[ExpenseVoucherRequest]:
    if principal is None:
        return queryset.none()

    role = getattr(principal, "active_role", "") or ""
    # System Admin has configuration access only, no operational financial data access (IAA-BR-004)
    if role in ("admin", "system_admin") or "system_admin" in getattr(principal, "roles", []):
        return queryset.none()

    # Finance Staff, Auditor, Approving Authorities see all operational requests
    if principal.has_permission("iaa.request.view_all"):
        return queryset

    # Basic users only see their own requests (IAA-BR-501)
    return queryset.filter(user_id=principal.user_id)


def scope_travel_claims(queryset: QuerySet[TAClaim], principal) -> QuerySet[TAClaim]:
    if principal is None:
        return queryset.none()

    role = getattr(principal, "active_role", "") or ""
    if role in ("admin", "system_admin") or "system_admin" in getattr(principal, "roles", []):
        return queryset.none()

    if principal.has_permission("iaa.travel.view_all"):
        return queryset

    return queryset.filter(user_id=principal.user_id)


def scope_anomalies(queryset: QuerySet[Anomaly], principal) -> QuerySet[Anomaly]:
    if principal is None:
        return queryset.none()

    role = getattr(principal, "active_role", "") or ""
    if role in ("admin", "system_admin"):
        return queryset.none()

    if principal.has_permission("iaa.anomaly.view"):
        return queryset

    return queryset.none()


def scope_audit_observations(
    queryset: QuerySet[AuditObservation], principal
) -> QuerySet[AuditObservation]:
    if principal is None:
        return queryset.none()

    role = getattr(principal, "active_role", "") or ""
    if role in ("admin", "system_admin"):
        return queryset.none()

    if principal.has_permission("iaa.audit.view"):
        return queryset

    # Basic users only see observations concerning their department or their responses
    return queryset.filter(responded_by_id=principal.user_id)
