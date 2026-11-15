"""IAA use cases. Every write checks a domain rule; RuleViolation becomes DomainError (422)."""
from django.db.models import Q
from django.utils import timezone

from core.api.exceptions import DomainError, NotFoundError, PermissionDeniedError
from modules.iaa import domain
from modules.iaa.models import ExpenseRequest

P_CREATE = "iaa.request.create"
P_VALIDATE = "iaa.request.validate"
P_DECIDE = "iaa.request.decide"
P_RECORD = "iaa.request.record"
ALL_PERMISSIONS = (P_CREATE, P_VALIDATE, P_DECIDE, P_RECORD)

_FINANCE_SEES = [domain.SUBMITTED, domain.FINANCE_VALIDATED, domain.APPROVED,
                 domain.REJECTED, domain.RECORDED]
_APPROVER_SEES = [domain.FINANCE_VALIDATED, domain.APPROVED, domain.REJECTED,
                  domain.RECORDED]


def _rule(check, *args):
    try:
        return check(*args)
    except domain.RuleViolation as exc:
        raise DomainError(exc.message, code=exc.code) from exc


def visible_requests(principal):
    """IAA-BR-501: creators see their own; Finance and approvers see only their queues."""
    q = Q(creator_user_id=principal.user_id)
    if principal.has_any_permission(P_VALIDATE, P_RECORD):
        q |= Q(status__in=_FINANCE_SEES)
    if principal.has_permission(P_DECIDE):
        q |= Q(status__in=_APPROVER_SEES)
    return ExpenseRequest.objects.filter(q)


def get_request(principal, pk: int) -> ExpenseRequest:
    req = visible_requests(principal).filter(pk=pk).first()
    if req is None:
        raise NotFoundError("No such expense/voucher request.")
    return req


def _own(principal, pk: int) -> ExpenseRequest:
    req = get_request(principal, pk)
    if req.creator_user_id != principal.user_id:
        raise PermissionDeniedError("Only the creator can do this.")
    return req


def create_draft(principal, data: dict) -> ExpenseRequest:
    """IAA-UC-101: save a (possibly incomplete) Draft (IAA-BR-101)."""
    return ExpenseRequest.objects.create(creator_user_id=principal.user_id, **data)


def update_draft(principal, pk: int, data: dict) -> ExpenseRequest:
    """IAA-UC-101: edit one's own Draft; locked after submission (IAA-BR-104)."""
    req = _own(principal, pk)
    _rule(domain.check_editable, req.status)
    for field, value in data.items():
        setattr(req, field, value)
    req.save()
    return req


def submit(principal, pk: int) -> ExpenseRequest:
    """IAA-UC-102: Draft to Submitted once complete (IAA-BR-101, IAA-BR-104)."""
    req = _own(principal, pk)
    _rule(domain.check_status, req.status, domain.DRAFT, "submit")
    _rule(domain.check_submission_complete, req.purpose, req.amount, req.department)
    req.status, req.submitted_at = domain.SUBMITTED, timezone.now()
    req.save(update_fields=["status", "submitted_at", "updated_at"])
    return req


def validate(principal, pk: int) -> ExpenseRequest:
    """IAA-UC-103: Finance moves Submitted to Finance Validated."""
    req = get_request(principal, pk)
    _rule(domain.check_status, req.status, domain.SUBMITTED, "validate")
    req.status, req.finance_user_id = domain.FINANCE_VALIDATED, principal.user_id
    req.validated_at = timezone.now()
    req.save(update_fields=["status", "finance_user_id", "validated_at", "updated_at"])
    return req


def decide(principal, pk: int, decision: str, remarks: str) -> ExpenseRequest:
    """IAA-UC-201: approve or reject (IAA-BR-001, IAA-BR-005)."""
    req = get_request(principal, pk)
    _rule(domain.check_status, req.status, domain.FINANCE_VALIDATED, "decide on")
    _rule(domain.check_not_self_approval, req.creator_user_id, principal.user_id)
    _rule(domain.check_remarks, remarks)
    req.status = _rule(domain.status_after_decision, decision)
    req.approver_user_id, req.decision_remarks = principal.user_id, remarks.strip()
    req.decided_at = timezone.now()
    req.save(update_fields=["status", "approver_user_id", "decision_remarks",
                            "decided_at", "updated_at"])
    return req


def record(principal, pk: int) -> ExpenseRequest:
    """IAA-UC-105: Approved to Recorded; internal record only, no payment (IAA-BR-006)."""
    req = get_request(principal, pk)
    _rule(domain.check_status, req.status, domain.APPROVED, "record")
    req.status, req.recorded_by_user_id = domain.RECORDED, principal.user_id
    req.recorded_at = timezone.now()
    req.save(update_fields=["status", "recorded_by_user_id", "recorded_at", "updated_at"])
    return req
