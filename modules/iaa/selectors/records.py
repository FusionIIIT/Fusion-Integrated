"""Record visibility. Callers never fetch an unscoped IAA object first."""
from django.db.models import Q

from modules.iaa.domain.state_machine import (
    ADMIN, AUDITOR, BASIC_USER, DEAN, DIRECTOR, FINANCE, HOD,
)
from modules.iaa.models import (
    Anomaly, AuditObservation, ExpenseVoucherRequest, IaaNotification,
    TravelAllowanceClaim,
)


def requests_for(principal, role):
    qs = ExpenseVoucherRequest.objects.all()
    if role == BASIC_USER:
        return qs.filter(created_by_id=principal.user_id)
    if role == FINANCE:
        return qs.filter(Q(assigned_finance_user_id=principal.user_id)
                         | Q(assigned_finance_user_id__isnull=True))
    if role in (HOD, DEAN, DIRECTOR):
        from modules.iaa.models import ApprovalStep
        ids = ApprovalStep.objects.filter(
            record_type="request", assigned_user_id=principal.user_id,
            status__in=("Pending", "Escalated"),
        ).values_list("record_id", flat=True)
        return qs.filter(pk__in=ids)
    if role == AUDITOR:
        return qs
    return qs.none()


def claims_for(principal, role):
    qs = TravelAllowanceClaim.objects.all()
    if role == BASIC_USER:
        return qs.filter(claimant_user_id=principal.user_id)
    if role == FINANCE:
        return qs
    if role in (HOD, DEAN, DIRECTOR):
        from modules.iaa.models import ApprovalStep
        ids = ApprovalStep.objects.filter(
            record_type="ta_claim", assigned_user_id=principal.user_id,
            status__in=("Pending", "Escalated"),
        ).values_list("record_id", flat=True)
        return qs.filter(pk__in=ids)
    if role == AUDITOR:
        return qs
    return qs.none()


def anomalies_for(principal, role):
    qs = Anomaly.objects.all()
    if role in (FINANCE, AUDITOR, HOD, DEAN, DIRECTOR):
        return qs.filter(Q(assigned_user_id=principal.user_id)
                         | Q(assigned_user_id__isnull=True)
                         | Q(created_by_id=principal.user_id))
    return qs.none()


def observations_for(principal, role):
    qs = AuditObservation.objects.all()
    if role == AUDITOR:
        return qs
    if role == BASIC_USER:
        departments = tuple(_departments(principal.user_id))
        return qs.filter(department__in=departments) if departments else qs.none()
    return qs.none()


def notifications_for(principal, role):
    return IaaNotification.objects.filter(user_id=principal.user_id).filter(
        Q(actor_role="") | Q(actor_role=role))


def _departments(user_id):
    from modules.iaa.models import IaaRoleAssignment
    return IaaRoleAssignment.objects.filter(
        user_id=user_id, is_active=True
    ).exclude(department="").values_list("department", flat=True)
