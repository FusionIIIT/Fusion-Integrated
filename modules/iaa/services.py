"""ALL writes. Transaction boundaries live here. Thin wrapper over domain.py rules."""
from django.db import transaction

from modules.iaa import domain
from modules.iaa.models import (
    Anomaly, ApprovalDecision, AuditLogEntry, AuditObservation,
    ExpenseVoucherRequest, RequestStatus, TAClaim, TaStatus,
)

HIGH_VALUE_THRESHOLD = 25000
EXPENSE_REQUIRED_FIELDS = ("request_type", "amount", "department", "description")


def _log(user_id, role, action, status=""):
    AuditLogEntry.objects.create(user_id=user_id, active_role=role, action=action,
                                  resulting_status=status)


# ---- Expense / Voucher (UC-101..105, UC-201..203) -------------------------

def create_draft_expense(creator_id, **fields):
    req = ExpenseVoucherRequest.objects.create(creator_id=creator_id, **fields)
    _log(creator_id, "basic_user", "iaa.expense.create_draft", req.status)
    return req


def submit_expense(request_id, actor_id):
    with transaction.atomic():
        req = ExpenseVoucherRequest.objects.select_for_update().get(pk=request_id)
        fields = {"request_type": req.request_type, "amount": req.amount,
                  "department": req.department, "description": req.description}
        domain.check_submission_completeness(fields, EXPENSE_REQUIRED_FIELDS, is_draft=False)
        req.status = RequestStatus.SUBMITTED
        req.save()
        _log(actor_id, "basic_user", "iaa.expense.submit", req.status)
        return req


def finance_review_expense(request_id, actor_id, approved, available_budget=None, query_text=""):
    with transaction.atomic():
        req = ExpenseVoucherRequest.objects.select_for_update().get(pk=request_id)
        if not approved:
            req.status = RequestStatus.QUERY_RAISED
            req.query_text = query_text
            req.save()
            _log(actor_id, "finance_staff", "iaa.expense.query_raised", req.status)
            return req
        if available_budget is not None and not domain.check_budget_available(
                req.amount, available_budget):
            Anomaly.objects.create(expense_request=req, category="BUDGET_INSUFFICIENT")
            _log(actor_id, "finance_staff", "iaa.expense.budget_anomaly", req.status)
            return req
        req.status = RequestStatus.FINANCE_VALIDATED
        req.save()
        _log(actor_id, "finance_staff", "iaa.expense.finance_validated", req.status)
        return req


def respond_query_expense(request_id, actor_id, response_text):
    with transaction.atomic():
        req = ExpenseVoucherRequest.objects.select_for_update().get(pk=request_id)
        req.query_text = response_text
        req.status = RequestStatus.SUBMITTED
        req.save()
        _log(actor_id, "basic_user", "iaa.expense.query_responded", req.status)
        return req


def decide_expense(request_id, actor_id, approved, remarks):
    with transaction.atomic():
        req = ExpenseVoucherRequest.objects.select_for_update().get(pk=request_id)
        domain.check_segregation_of_duties(req.creator_id, actor_id)
        domain.require_remarks(remarks)
        req.approval_level += 1
        ApprovalDecision.objects.create(
            expense_request=req, approver_id=actor_id,
            decision="APPROVED" if approved else "REJECTED",
            remarks=remarks, level=req.approval_level)
        if not approved:
            req.status = RequestStatus.REJECTED
        elif domain.more_approval_levels_required(req.approval_level,
                                                    req.approval_levels_required):
            req.status = RequestStatus.APPROVAL_PENDING
        else:
            req.status = RequestStatus.APPROVED
        req.save()
        _log(actor_id, "approving_authority", "iaa.expense.decide", req.status)
        return req


def escalate_overdue_expense(request_id, next_authority_id):
    with transaction.atomic():
        req = ExpenseVoucherRequest.objects.select_for_update().get(pk=request_id)
        req.status = RequestStatus.ESCALATED
        req.current_approver_id = next_authority_id
        req.save()
        _log(0, "system", "iaa.expense.escalate_overdue", req.status)
        return req


def process_record_expense(request_id, actor_id):
    """BR-006: internal governance completion only — no payment is invoked here."""
    with transaction.atomic():
        req = ExpenseVoucherRequest.objects.select_for_update().get(pk=request_id)
        if req.status != RequestStatus.APPROVED:
            raise ValueError("Only an Approved request can be recorded")
        req.status = RequestStatus.RECORDED
        req.save()
        _log(actor_id, "finance_staff", "iaa.expense.recorded", req.status)
        return req


# ---- TA Claims (UC-401..404) ----------------------------------------------

def submit_ta_claim(employee_id, **fields):
    claim = TAClaim.objects.create(
        employee_id=employee_id,
        is_high_value=domain.is_high_value(fields.get("claimed_amount", 0),
                                            HIGH_VALUE_THRESHOLD),
        **fields)
    _log(employee_id, "basic_user", "iaa.ta.submit", claim.status)
    return claim


def verify_ta_claim(claim_id, actor_id, approved, available_budget=None, query_text=""):
    with transaction.atomic():
        claim = TAClaim.objects.select_for_update().get(pk=claim_id)
        if not approved:
            claim.status = TaStatus.QUERY_RAISED
            claim.query_text = query_text
            claim.save()
            _log(actor_id, "finance_staff", "iaa.ta.query_raised", claim.status)
            return claim
        if available_budget is not None and not domain.check_budget_available(
                claim.claimed_amount, available_budget):
            Anomaly.objects.create(ta_claim=claim, category="BUDGET_INSUFFICIENT")
            _log(actor_id, "finance_staff", "iaa.ta.budget_anomaly", claim.status)
            return claim
        claim.status = (TaStatus.APPROVAL_PENDING if claim.is_high_value
                         else TaStatus.VERIFIED)
        claim.save()
        _log(actor_id, "finance_staff", "iaa.ta.verified", claim.status)
        return claim


def decide_ta_claim(claim_id, actor_id, approved, remarks):
    with transaction.atomic():
        claim = TAClaim.objects.select_for_update().get(pk=claim_id)
        domain.check_segregation_of_duties(claim.employee_id, actor_id)
        domain.require_remarks(remarks)
        claim.approval_level += 1
        ApprovalDecision.objects.create(
            ta_claim=claim, approver_id=actor_id,
            decision="APPROVED" if approved else "REJECTED",
            remarks=remarks, level=claim.approval_level)
        if not approved:
            claim.status = TaStatus.REJECTED
        elif domain.more_approval_levels_required(claim.approval_level,
                                                     claim.approval_levels_required):
            claim.status = TaStatus.APPROVAL_PENDING
        else:
            claim.status = TaStatus.APPROVED
        claim.save()
        _log(actor_id, "approving_authority", "iaa.ta.decide", claim.status)
        return claim


def process_record_ta_claim(claim_id, actor_id):
    with transaction.atomic():
        claim = TAClaim.objects.select_for_update().get(pk=claim_id)
        if claim.status not in (TaStatus.VERIFIED, TaStatus.APPROVED):
            raise ValueError("Only a Verified or Approved claim can be recorded")
        claim.status = TaStatus.RECORDED
        claim.save()
        _log(actor_id, "finance_staff", "iaa.ta.recorded", claim.status)
        return claim


# ---- Anomalies (UC-302, UC-303) -------------------------------------------

def flag_anomaly(actor_id, category, description="", expense_request_id=None, ta_claim_id=None):
    anomaly = Anomaly.objects.create(
        expense_request_id=expense_request_id, ta_claim_id=ta_claim_id,
        category=category, description=description)
    _log(actor_id, "finance_staff_or_auditor", "iaa.anomaly.flag", anomaly.status)
    return anomaly


def resolve_or_escalate_anomaly(anomaly_id, actor_id, escalate, notes=""):
    with transaction.atomic():
        anomaly = Anomaly.objects.select_for_update().get(pk=anomaly_id)
        anomaly.resolver_id = actor_id
        anomaly.resolution_notes = notes
        anomaly.status = "ESCALATED" if escalate else "RESOLVED"
        anomaly.save()
        _log(actor_id, "designated_resolver", "iaa.anomaly.resolve", anomaly.status)
        return anomaly


# ---- Audit Observations (UC-501..503) --------------------------------------

def raise_audit_observation(auditor_id, description, expense_request_id=None, ta_claim_id=None):
    obs = AuditObservation.objects.create(
        auditor_id=auditor_id, description=description,
        expense_request_id=expense_request_id, ta_claim_id=ta_claim_id)
    _log(auditor_id, "auditor", "iaa.audit.raise", obs.status)
    return obs


def respond_audit_observation(observation_id, actor_id, response_text):
    with transaction.atomic():
        obs = AuditObservation.objects.select_for_update().get(pk=observation_id)
        obs.response_text = response_text
        obs.status = "RESPONDED"
        obs.save()
        _log(actor_id, "basic_user", "iaa.audit.respond", obs.status)
        return obs


def review_close_audit_observation(observation_id, actor_id, satisfactory):
    with transaction.atomic():
        obs = AuditObservation.objects.select_for_update().get(pk=observation_id)
        domain.can_close_observation(obs.status)
        obs.status = "CLOSED" if satisfactory else "OPEN"
        obs.save()
        _log(actor_id, "auditor", "iaa.audit.review_close", obs.status)
        return obs
