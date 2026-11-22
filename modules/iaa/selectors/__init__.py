"""Read scopes shared by IAA endpoints and reports."""

from modules.iaa.authorization import active_role, actor_id
from modules.iaa.models import (
    Anomaly, ApprovalStep, AuditObservation, ExpenseRequest,
    IaaNotificationOutbox, TravelClaim,
)


def own_expenses(actor):
    return ExpenseRequest.objects.filter(creator_user_id=actor_id(actor))


def expenses_for(actor):
    role = active_role(actor)
    if role == "basic_user":
        return own_expenses(actor)
    if role in {"finance_staff", "auditor"}:
        return ExpenseRequest.objects.all()
    if role in {"hod", "dean", "director"}:
        ids = ApprovalStep.objects.filter(assignee_user_id=actor_id(actor), record_type="expense")
        return ExpenseRequest.objects.filter(pk__in=ids.values_list("record_id", flat=True))
    return ExpenseRequest.objects.none()


def claims_for(actor):
    role = active_role(actor)
    if role == "basic_user":
        return TravelClaim.objects.filter(claimant_user_id=actor_id(actor))
    if role in {"finance_staff", "auditor"}:
        return TravelClaim.objects.all()
    if role in {"hod", "dean", "director"}:
        ids = ApprovalStep.objects.filter(assignee_user_id=actor_id(actor), record_type="ta")
        return TravelClaim.objects.filter(pk__in=ids.values_list("record_id", flat=True))
    return TravelClaim.objects.none()


def assigned_approvals(actor):
    return ApprovalStep.objects.filter(assignee_user_id=actor_id(actor), status="pending")


def anomalies_for(actor):
    role = active_role(actor)
    if role in {"finance_staff", "auditor"}:
        return Anomaly.objects.all()
    if role in {"hod", "dean", "director"}:
        return Anomaly.objects.filter(resolver_user_id=actor_id(actor))
    return Anomaly.objects.none()


def observations_for(actor):
    role = active_role(actor)
    if role == "basic_user":
        return AuditObservation.objects.filter(owner_user_id=actor_id(actor))
    if role == "auditor":
        return AuditObservation.objects.filter(auditor_user_id=actor_id(actor))
    return AuditObservation.objects.none()


def notifications_for(actor):
    return IaaNotificationOutbox.objects.filter(recipient_user_id=actor_id(actor))

