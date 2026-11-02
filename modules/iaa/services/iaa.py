"""Transactional IAA services. All writes are atomic and audit logged."""
from __future__ import annotations

import csv
import io
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from fusion_auth.client import IamUnavailable, get_client
from modules.iaa.domain import rules, workflow
from modules.iaa.models import (
    ActiveRoleSelection, Anomaly, ApprovalRule, ApprovalStep, AuditLog,
    AuditObservation, DashboardNotification, DepartmentBudget, FinancialRecord,
    FinanceQuery, FinancialYearPolicy, ObservationResponse, RoleAssignment,
    SupportingDocument,
)

BASIC_ROLES = {"basic_user", "employee", "faculty", "staff", "department_representative"}
FINANCE_ROLES = {"finance_staff"}
AUTHORITY_ROLES = {"hod", "dean", "director"}
AUDIT_ROLES = {"auditor"}
ADMIN_ROLES = {"system_admin"}
ROLE_ALIASES = {
    "basic user": "basic_user", "basic_user": "basic_user",
    "department representative": "department_representative",
    "finance staff": "finance_staff", "hod": "hod",
    "head of department": "hod", "head_of_department": "hod",
    "dean": "dean", "director": "director", "auditor": "auditor",
    "system admin": "system_admin", "system_admin": "system_admin",
    "administrator": "system_admin", "employee": "employee",
    "faculty": "faculty", "staff": "staff",
}


def normalize_role(value: Any) -> str:
    raw = str(value or "").strip()
    return ROLE_ALIASES.get(raw.lower(), raw.lower().replace(" ", "_"))


def actor_role(actor) -> str:
    """Use IAM's active role as authority; a local mirror can never grant a role."""
    if actor is None:
        raise PermissionDeniedError("Authentication required.", code="not_authenticated")
    roles = tuple(normalize_role(r) for r in getattr(actor, "roles", ()) if r)
    selected = normalize_role(getattr(actor, "active_role", None))
    if not selected and len(roles) == 1:
        selected = roles[0]
    if len(roles) > 1 and not selected:
        raise PermissionDeniedError(
            "Select an active IAA role in Fusion before performing a role-specific action.",
            code="active_role_required")
    if roles and selected not in roles:
        raise PermissionDeniedError("The active IAM role is not assigned to this account.",
                                    code="invalid_active_role")
    mirror = ActiveRoleSelection.objects.filter(user_id=actor.user_id).first()
    if mirror and selected and normalize_role(mirror.role) != selected:
        raise ConflictError(
            "The active role changed in IAM. Refresh the Fusion session before continuing.",
            code="active_role_refresh_required")
    if not selected:
        raise PermissionDeniedError("An active IAA role is required.",
                                    code="active_role_required")
    return selected


def require(actor, permission: str, *, roles: set[str] | None = None,
            operational: bool = True) -> str:
    role = actor_role(actor)
    if operational and role in ADMIN_ROLES:
        raise PermissionDeniedError(
            "System Admin may configure IAA but cannot access operational financial records.",
            code="admin_operational_separation")
    if roles and role not in roles:
        raise PermissionDeniedError("The active IAA role cannot perform this action.")
    checker = getattr(actor, "has_permission", None)
    if checker is None or not checker(permission):
        raise PermissionDeniedError(f"This action requires {permission}.")
    return role


def _log(actor, action: str, resource_type: str, resource_id: int | None = None,
         from_status: str = "", to_status: str = "", details: dict | None = None,
         role: str | None = None) -> AuditLog:
    return AuditLog.objects.create(
        actor_user_id=getattr(actor, "user_id", None),
        actor_role=role or (actor_role(actor) if actor is not None else "system"),
        action=action, resource_type=resource_type, resource_id=resource_id,
        from_status=from_status, to_status=to_status, details=details or {},
    )


def _notify_user(user_id: int | None, event_type: str, title: str, message: str,
                 resource_type: str = "", resource_id: int | None = None,
                 role: str = "") -> None:
    if user_id is None:
        return
    DashboardNotification.objects.create(
        recipient_user_id=user_id, recipient_role=role, event_type=event_type,
        title=title, message=message, resource_type=resource_type,
        resource_id=resource_id,
    )


def _notify_roles(roles: set[str], event_type: str, title: str, message: str,
                  resource_type: str = "", resource_id: int | None = None) -> None:
    ids = (RoleAssignment.objects.filter(is_active=True)
           .filter(role__in=roles).values_list("user_id", flat=True).distinct())
    for user_id in ids:
        _notify_user(user_id, event_type, title, message, resource_type, resource_id)


def _financial_year(today=None) -> str:
    today = today or timezone.localdate()
    policy = FinancialYearPolicy.objects.filter(
        is_active=True, starts_on__lte=today, ends_on__gte=today).first()
    if policy is None:
        raise ConflictError(
            "No active IAA financial year is configured for today's date.",
            code="financial_year_not_configured")
    return policy.financial_year


def visible_records(actor):
    role = actor_role(actor)
    if role in ADMIN_ROLES:
        raise PermissionDeniedError("System Admin cannot access operational financial records.")
    qs = FinancialRecord.objects.all().prefetch_related("attachments", "approval_steps")
    if role in BASIC_ROLES:
        return qs.filter(created_by_id=actor.user_id)
    if role in FINANCE_ROLES or role in AUDIT_ROLES:
        return qs
    if role in AUTHORITY_ROLES:
        ids = ApprovalStep.objects.filter(
            Q(assigned_user_id=actor.user_id) | Q(authority_role__iexact=role),
        ).values_list("record_id", flat=True)
        return qs.filter(pk__in=ids).distinct()
    raise PermissionDeniedError("No IAA record visibility is assigned to this role.")


def get_record(actor, record_id: int) -> FinancialRecord:
    row = visible_records(actor).filter(pk=record_id).first()
    if row is None:
        raise NotFoundError("No IAA record exists in your permitted scope.")
    return row


@transaction.atomic
def create_record(actor, payload: dict, *, kind: str) -> FinancialRecord:
    permission = "iaa.ta.create" if kind == "ta" else "iaa.request.create"
    require(actor, permission, roles=BASIC_ROLES)
    financial_year = str(payload.get("financial_year") or _financial_year())
    if not FinancialYearPolicy.objects.filter(financial_year=financial_year, is_active=True).exists():
        raise ConflictError(
            "The selected financial year is not active or configured.",
            code="financial_year_not_configured")
    row = FinancialRecord.objects.create(
        record_kind=kind, request_type=str(payload.get("request_type", "TA" if kind == "ta" else "")),
        created_by_id=actor.user_id, department=str(payload.get("department", "")).strip(),
        amount=Decimal(str(payload.get("amount", "0"))),
        description=str(payload.get("description", "")),
        financial_year=financial_year,
        trip_start_date=payload.get("trip_start_date"),
        trip_end_date=payload.get("trip_end_date"),
        trip_purpose=str(payload.get("trip_purpose", "")),
        trip_details=payload.get("trip_details") or {},
    )
    _log(actor, "record.created", "financial_record", row.pk, "", row.status,
         {"record_kind": kind})
    return row


@transaction.atomic
def update_draft(actor, record_id: int, payload: dict) -> FinancialRecord:
    role = require(actor, "iaa.request.create", roles=BASIC_ROLES)
    row = FinancialRecord.objects.select_for_update().filter(pk=record_id).first()
    if row is None:
        raise NotFoundError("IAA record not found.")
    if row.created_by_id != actor.user_id:
        raise PermissionDeniedError("Only the creator may edit this draft.")
    if row.status != workflow.DRAFT:
        raise ConflictError("Submitted records are locked; use a supported clarification response.")
    allowed = {"request_type", "department", "amount", "description", "trip_start_date",
               "trip_end_date", "trip_purpose", "trip_details"}
    for key in allowed & payload.keys():
        setattr(row, key, payload[key])
    row.save()
    _log(actor, "record.draft_updated", "financial_record", row.pk, row.status, row.status, role=role)
    return row


@transaction.atomic
def attach_document(actor, record_id: int, payload: dict) -> SupportingDocument:
    require(actor, "iaa.request.create", roles=BASIC_ROLES)
    row = FinancialRecord.objects.select_for_update().filter(
        pk=record_id, created_by_id=actor.user_id, status=workflow.DRAFT).first()
    if row is None:
        raise NotFoundError("Draft not found in your scope.")
    ref = str(payload.get("storage_reference", "")).strip()
    name = str(payload.get("name", "")).strip()
    if not ref or not name:
        raise ConflictError("Document name and storage reference are required.")
    doc = SupportingDocument.objects.create(
        record=row, uploaded_by_id=actor.user_id, name=name,
        storage_reference=ref, content_type=str(payload.get("content_type", "")),
        size_bytes=payload.get("size_bytes"),
    )
    _log(actor, "document.attached", "financial_record", row.pk, details={"document_id": doc.pk})
    return doc


@transaction.atomic
def submit_record(actor, record_id: int) -> FinancialRecord:
    row = FinancialRecord.objects.select_for_update().filter(
        pk=record_id, created_by_id=actor.user_id).first()
    if row is None:
        raise NotFoundError("Draft not found in your scope.")
    permission = "iaa.ta.submit" if row.record_kind == "ta" else "iaa.request.submit"
    role = require(actor, permission, roles=BASIC_ROLES)
    if row.status != workflow.DRAFT:
        raise ConflictError("Only a Draft can be formally submitted.")
    policy = FinancialYearPolicy.objects.filter(financial_year=row.financial_year).first()
    settings = policy.settings if policy else {}
    needs_docs = bool(settings.get("ta_requires_documents", True)) if row.record_kind == "ta" else bool(settings.get("expense_requires_documents", False))
    payload = {
        "request_type": row.request_type, "department": row.department,
        "amount": row.amount, "description": row.description,
        "trip_start_date": row.trip_start_date, "trip_end_date": row.trip_end_date,
        "trip_purpose": row.trip_purpose,
    }
    issues = rules.submission_errors(
        payload, kind=row.record_kind, attachment_count=row.attachments.count(),
        required_documents=needs_docs,
    )
    if issues:
        raise ConflictError("Submission is incomplete.", code="submission_incomplete",
                            details=[{"field": x.field, "code": x.code, "message": x.message}
                                     for x in issues])
    before = row.status
    row.status = workflow.SUBMITTED
    row.submitted_at = timezone.now()
    row.save(update_fields=["status", "submitted_at", "updated_at"])
    _log(actor, "record.submitted", "financial_record", row.pk, before, row.status, role=role)
    _notify_roles(FINANCE_ROLES, "submission", "IAA request submitted",
                  f"Financial request #{row.pk} is awaiting Finance review.",
                  "financial_record", row.pk)
    _notify_user(row.created_by_id, "submission", "Request submitted",
                 f"Your IAA request #{row.pk} was submitted.", "financial_record", row.pk)
    return row


@transaction.atomic
def request_clarification(actor, record_id: int, question: str) -> FinanceQuery:
    role = require(actor, "iaa.finance.query", roles=FINANCE_ROLES)
    row = FinancialRecord.objects.select_for_update().filter(pk=record_id).first()
    if row is None:
        raise NotFoundError("IAA record not found.")
    if row.status not in (workflow.SUBMITTED, workflow.QUERY_RESPONDED):
        raise ConflictError("Finance clarification is available only during Finance review.")
    if not question.strip():
        raise ConflictError("A clarification question is required.")
    before = row.status
    query = FinanceQuery.objects.create(record=row, asked_by_id=actor.user_id, question=question.strip())
    row.status = workflow.QUERY_RAISED
    row.save(update_fields=["status", "updated_at"])
    _log(actor, "finance.query_raised", "financial_record", row.pk, before, row.status,
         {"query_id": query.pk}, role)
    _notify_user(row.created_by_id, "clarification", "Finance clarification requested",
                 f"Please respond to clarification on IAA request #{row.pk}.",
                 "financial_record", row.pk)
    return query


@transaction.atomic
def respond_to_query(actor, query_id: int, response_text: str) -> FinanceQuery:
    require(actor, "iaa.query.respond", roles=BASIC_ROLES)
    query = FinanceQuery.objects.select_for_update().select_related("record").filter(
        pk=query_id, record__created_by_id=actor.user_id, status="open").first()
    if query is None:
        raise NotFoundError("Open Finance query not found in your scope.")
    if not response_text.strip():
        raise ConflictError("A clarification response is required.")
    query.response = response_text.strip()
    query.status = "responded"
    query.responded_by_id = actor.user_id
    query.responded_at = timezone.now()
    query.save(update_fields=["response", "status", "responded_by_id", "responded_at", "updated_at"])
    row = query.record
    before = row.status
    row.status = workflow.QUERY_RESPONDED
    row.save(update_fields=["status", "updated_at"])
    _log(actor, "finance.query_responded", "financial_record", row.pk, before, row.status,
         {"query_id": query.pk})
    _notify_roles(FINANCE_ROLES, "clarification_response", "Clarification response received",
                  f"Request #{row.pk} has a new clarification response.", "financial_record", row.pk)
    return query


def _approval_levels(record: FinancialRecord) -> list[dict]:
    qs = ApprovalRule.objects.filter(is_active=True)
    candidates = [{
        "record_kind": x.record_kind, "request_type": x.request_type,
        "department": x.department, "min_amount": x.min_amount,
        "max_amount": x.max_amount, "priority": x.priority,
        "levels": x.levels, "is_active": x.is_active,
    } for x in qs]
    selected = rules.select_approval_rule(
        candidates, kind=record.record_kind, request_type=record.request_type,
        department=record.department, amount=record.amount,
    )
    if selected is None:
        policy = FinancialYearPolicy.objects.filter(
            financial_year=record.financial_year).first()
        config = policy.settings if policy else {}
        threshold = config.get("ta_high_value_threshold")
        # A TA claim is routed only when the institution has configured the
        # high-value threshold. No monetary threshold is hard-coded here.
        if record.record_kind == "ta" and threshold in (None, ""):
            return []
        if record.record_kind == "ta" and record.amount < Decimal(str(threshold)):
            return []
        raise ConflictError(
            "No configured approval route matches this request. Ask System Admin to configure approval hierarchy and thresholds.",
            code="approval_route_not_configured")
    configured_levels = selected.get("levels") or []
    # A configured named assignee who is the claimant is ineligible under
    # segregation of duties; skip that authority and continue to the next
    # configured level instead of creating an approval that can never pass.
    levels = [level for level in configured_levels
              if level.get("user_id") in (None, "")
              or int(level["user_id"]) != int(record.created_by_id)]
    if configured_levels and not levels:
        raise ConflictError(
            "Every configured approver is ineligible under segregation of duties.",
            code="no_eligible_approver")
    if not levels:
        policy = FinancialYearPolicy.objects.filter(
            financial_year=record.financial_year).first()
        config = policy.settings if policy else {}
        threshold = config.get("ta_high_value_threshold")
        if record.record_kind != "ta" or threshold in (None, "") or record.amount >= Decimal(str(threshold)):
            raise ConflictError(
                "The configured approval route has no approval levels. Configure at least one eligible authority.",
                code="approval_route_empty")
        return []
    for level in levels:
        if normalize_role(level.get("role")) not in AUTHORITY_ROLES:
            raise ConflictError("Approval route contains an unsupported authority role.")
        if level.get("timeout_hours") not in (None, "") and int(level["timeout_hours"]) <= 0:
            raise ConflictError("Approval timeout must be a positive configured duration.")
    return levels


def _deadline(level: dict):
    hours = level.get("timeout_hours")
    return timezone.now() + timezone.timedelta(hours=int(hours)) if hours not in (None, "") else None


@transaction.atomic
def finance_validate(actor, record_id: int, *, policy_passed: bool = True,
                     remarks: str = "") -> FinancialRecord:
    row = FinancialRecord.objects.select_for_update().filter(pk=record_id).first()
    if row is None:
        raise NotFoundError("IAA record not found.")
    permission = "iaa.ta.verify" if row.record_kind == "ta" else "iaa.finance.validate"
    role = require(actor, permission, roles=FINANCE_ROLES)
    if row.status not in (workflow.SUBMITTED, workflow.QUERY_RESPONDED):
        raise ConflictError("Only submitted or query-responded records can be validated.")
    policy = FinancialYearPolicy.objects.filter(financial_year=row.financial_year).first()
    if row.record_kind == "ta":
        ta_policy = (policy.settings if policy else {}).get("ta_policy")
        if not isinstance(ta_policy, dict):
            raise ConflictError(
                "TA policy is not configured for this financial year. Configure it before verification.",
                code="ta_policy_not_configured")
        if row.trip_start_date is None or row.trip_end_date is None:
            raise ConflictError("TA trip dates are required.", code="ta_trip_dates_required")
        if row.trip_end_date < row.trip_start_date:
            raise ConflictError("TA trip end date cannot precede the start date.")
        trip_days = (row.trip_end_date - row.trip_start_date).days + 1
        max_days = ta_policy.get("max_trip_days")
        if max_days is not None and trip_days > int(max_days):
            policy_passed = False
            remarks = remarks or f"Trip duration {trip_days} exceeds configured maximum {max_days}."
        min_amount = ta_policy.get("min_claim_amount")
        max_amount = ta_policy.get("max_claim_amount")
        if min_amount is not None and row.amount < Decimal(str(min_amount)):
            policy_passed = False
            remarks = remarks or "Claim amount is below the configured minimum."
        if max_amount is not None and row.amount > Decimal(str(max_amount)):
            policy_passed = False
            remarks = remarks or "Claim amount exceeds the configured maximum."
        allowed_purposes = ta_policy.get("allowed_purposes")
        if allowed_purposes and row.trip_purpose not in allowed_purposes:
            policy_passed = False
            remarks = remarks or "Trip purpose is not allowed by the configured TA policy."
        if ta_policy.get("documents_required", True) and not row.attachments.exists():
            policy_passed = False
            remarks = remarks or "Required supporting TA documents are missing."
    if not policy_passed:
        if not remarks.strip():
            raise ConflictError("Finance rejection remarks are required.")
        before = row.status
        row.status = workflow.REJECTED
        row.save(update_fields=["status", "updated_at"])
        _log(actor, "finance.policy_rejected", "financial_record", row.pk,
             before, row.status, {"remarks": remarks.strip()}, role)
        _notify_user(row.created_by_id, "ta_rejected" if row.record_kind == "ta" else "request_rejected",
                     "IAA request rejected", f"Request #{row.pk} failed the applicable policy checks.",
                     "financial_record", row.pk)
        return row

    budget = DepartmentBudget.objects.select_for_update().filter(
        department=row.department, financial_year=row.financial_year, is_active=True).first()
    require_budget = bool((policy.settings if policy else {}).get("budget_required", False))
    if budget:
        shortfall = rules.budget_shortfall(
            amount=row.amount, allocated=budget.allocated,
            spent=budget.spent, committed=budget.committed)
        if shortfall > 0:
            before = row.status
            row.status = workflow.ANOMALY_PENDING
            row.save(update_fields=["status", "updated_at"])
            anomaly = Anomaly.objects.create(
                record=row, category="budget_shortfall", severity="high",
                title="Departmental budget insufficiency",
                details=f"Budget shortfall: {shortfall}. Request is not auto-rejected.",
                raised_by_id=None, resolver_role="finance_staff",
            )
            _log(None, "anomaly.auto_created", "anomaly", anomaly.pk, "", anomaly.status,
                 {"record_id": row.pk, "shortfall": str(shortfall)}, "system")
            _log(actor, "finance.budget_anomaly", "financial_record", row.pk,
                 before, row.status, {"anomaly_id": anomaly.pk}, role)
            _notify_roles(FINANCE_ROLES | AUDIT_ROLES, "anomaly", "Budget anomaly created",
                          f"Budget insufficiency for IAA request #{row.pk}.",
                          "anomaly", anomaly.pk)
            return row
    elif require_budget:
        raise ConflictError("No departmental budget is configured for this financial year.",
                            code="budget_not_configured")

    before = row.status
    row.validated_at = timezone.now()
    row.status = workflow.FINANCE_VALIDATED
    row.save(update_fields=["status", "validated_at", "updated_at"])
    _log(actor, "finance.validated", "financial_record", row.pk,
         before, row.status, {"policy_passed": True}, role)

    levels = _approval_levels(row)
    if levels:
        row.status = workflow.APPROVAL_PENDING
        row.current_approval_step = 1
        for index, level in enumerate(levels, start=1):
            ApprovalStep.objects.create(
                record=row, step_number=index, authority_role=normalize_role(level["role"]),
                assigned_user_id=level.get("user_id"),
                status="pending" if index == 1 else "queued",
                timeout_hours=level.get("timeout_hours") or None,
                due_at=_deadline(level) if index == 1 else None,
            )
        first = levels[0]
        _notify_roles({normalize_role(first["role"])}, "approval_pending",
                      "IAA approval assigned", f"Request #{row.pk} awaits your decision.",
                      "financial_record", row.pk)
    else:
        row.status = workflow.VERIFIED if row.record_kind == "ta" else workflow.APPROVED
    row.save(update_fields=["status", "current_approval_step", "updated_at"])
    _log(actor, "approval.route_created" if levels else "finance.directly_approved",
         "financial_record", row.pk, workflow.FINANCE_VALIDATED, row.status,
         {"approval_levels": len(levels)}, role)
    _notify_user(row.created_by_id, "finance_validated", "Finance review completed",
                 f"Your IAA request #{row.pk} passed Finance validation.",
                 "financial_record", row.pk)
    return row


@transaction.atomic
def decide_approval(actor, step_id: int, *, decision: str, remarks: str) -> ApprovalStep:
    role = require(actor, "iaa.approval.decide", roles=AUTHORITY_ROLES)
    step = ApprovalStep.objects.select_for_update().select_related("record").filter(pk=step_id).first()
    if step is None:
        raise NotFoundError("Approval step not found.")
    row = step.record
    if step.status != "pending" or row.status not in (workflow.APPROVAL_PENDING, workflow.ESCALATED):
        raise ConflictError("This approval is not currently pending.")
    if normalize_role(step.authority_role) != role:
        raise PermissionDeniedError("The active authority role does not match this approval.")
    if step.assigned_user_id and step.assigned_user_id != actor.user_id:
        raise PermissionDeniedError("This approval is assigned to another authority.")
    if not rules.may_approve(creator_id=row.created_by_id, actor_id=actor.user_id):
        raise PermissionDeniedError("A creator/claimant cannot approve their own request.",
                                    code="segregation_of_duties")
    if not remarks.strip():
        raise ConflictError("Approval or rejection remarks are mandatory.",
                            code="approval_remarks_required")
    if decision not in ("approve", "reject"):
        raise ConflictError("Decision must be approve or reject.")
    before = row.status
    step.status = "approved" if decision == "approve" else "rejected"
    step.decided_by_id = actor.user_id
    step.decided_role = role
    step.decided_at = timezone.now()
    step.remarks = remarks.strip()
    step.save(update_fields=["status", "decided_by_id", "decided_role", "decided_at", "remarks", "updated_at"])
    if decision == "reject":
        row.status = workflow.REJECTED
    else:
        next_step = ApprovalStep.objects.select_for_update().filter(
            record=row, step_number__gt=step.step_number, status="queued").order_by("step_number").first()
        if next_step:
            next_step.status = "pending"
            next_step.due_at = timezone.now() + timezone.timedelta(hours=next_step.timeout_hours) if next_step.timeout_hours else None
            next_step.save(update_fields=["status", "due_at", "updated_at"])
            row.current_approval_step = next_step.step_number
            row.status = workflow.APPROVAL_PENDING
            _notify_roles({normalize_role(next_step.authority_role)}, "approval_pending",
                          "Next IAA approval assigned", f"Request #{row.pk} awaits your decision.",
                          "financial_record", row.pk)
        else:
            row.status = workflow.APPROVED
    row.save(update_fields=["status", "current_approval_step", "updated_at"])
    _log(actor, f"approval.{decision}d", "financial_record", row.pk, before, row.status,
         {"approval_step_id": step.pk, "remarks": step.remarks}, role)
    _notify_user(row.created_by_id, f"approval_{decision}", "IAA approval decision",
                 f"Request #{row.pk} was {decision}d.", "financial_record", row.pk)
    return step


@transaction.atomic
def record_completion(actor, record_id: int) -> FinancialRecord:
    role = require(actor, "iaa.finance.record", roles=FINANCE_ROLES)
    row = FinancialRecord.objects.select_for_update().filter(pk=record_id).first()
    if row is None:
        raise NotFoundError("IAA record not found.")
    allowed = (workflow.APPROVED, workflow.VERIFIED) if row.record_kind == "ta" else (workflow.APPROVED,)
    if row.status not in allowed:
        raise ConflictError("Only verified standard TA or approved financial records may be internally recorded.")
    before = row.status
    row.status = workflow.RECORDED
    row.recorded_at = timezone.now()
    row.save(update_fields=["status", "recorded_at", "updated_at"])
    _log(actor, "record.internal_completion", "financial_record", row.pk, before, row.status,
         {"monetary_transfer_executed": False}, role)
    _notify_user(row.created_by_id, "recorded", "IAA record completed",
                 f"Request #{row.pk} was internally recorded. No payment was executed.",
                 "financial_record", row.pk)
    return row


@transaction.atomic
def _flag_anomaly_internal(actor, row: FinancialRecord, category: str, details: str,
                           *, severity: str = "medium", role: str | None = None) -> Anomaly:
    policy = (FinancialYearPolicy.objects.filter(
        financial_year=row.financial_year).first() if row else None)
    resolver_map = (policy.settings or {}).get("anomaly_resolvers", {}) if policy else {}
    resolver_role = normalize_role(resolver_map.get(category, "finance_staff"))
    if resolver_role not in FINANCE_ROLES | AUTHORITY_ROLES | AUDIT_ROLES:
        raise ConflictError("The configured anomaly resolver role is not an eligible IAA resolver.")
    anomaly = Anomaly.objects.create(
        record=row, category=category, severity=severity,
        title=category.replace("_", " ").title(), details=details,
        raised_by_id=getattr(actor, "user_id", None), resolver_role=resolver_role,
    )
    _log(actor, "anomaly.flagged", "anomaly", anomaly.pk, "", anomaly.status,
         {"record_id": row.pk, "category": category}, role)
    _notify_roles(FINANCE_ROLES | AUDIT_ROLES, "anomaly", "IAA anomaly flagged",
                  f"Anomaly #{anomaly.pk} requires review.", "anomaly", anomaly.pk)
    return anomaly


@transaction.atomic
def flag_anomaly(actor, payload: dict) -> Anomaly:
    role = require(actor, "iaa.anomaly.flag", roles=FINANCE_ROLES | AUDIT_ROLES)
    if not payload.get("record_id"):
        raise ConflictError("Select the financial record associated with this anomaly.")
    record = get_record(actor, int(payload["record_id"]))
    return _flag_anomaly_internal(
        actor, record, str(payload.get("category", "material_anomaly")),
        str(payload.get("details", "")).strip(),
        severity=str(payload.get("severity", "medium")), role=role,
    )


@transaction.atomic
def resolve_anomaly(actor, anomaly_id: int, *, action: str, resolution: str) -> Anomaly:
    role = require(actor, "iaa.anomaly.resolve",
                   roles=FINANCE_ROLES | AUTHORITY_ROLES | AUDIT_ROLES)
    anomaly = Anomaly.objects.select_for_update().select_related("record").filter(pk=anomaly_id).first()
    if anomaly is None:
        raise NotFoundError("Anomaly not found.")
    if anomaly.resolver_user_id and anomaly.resolver_user_id != actor.user_id:
        raise PermissionDeniedError("This anomaly is assigned to another resolver.")
    if anomaly.resolver_role and normalize_role(anomaly.resolver_role) != role:
        raise PermissionDeniedError("This anomaly is assigned to another resolver role.")
    if anomaly.status not in (workflow.ANOMALY_OPEN, workflow.ANOMALY_ESCALATED):
        raise ConflictError("Only Open or Escalated anomalies may be resolved.")
    if action not in ("resolve", "escalate") or not resolution.strip():
        raise ConflictError("Choose resolve/escalate and provide an outcome.")
    if action == "escalate" and anomaly.status == workflow.ANOMALY_ESCALATED:
        raise ConflictError("An anomaly may be escalated only once.")
    before = anomaly.status
    anomaly.status = workflow.ANOMALY_RESOLVED if action == "resolve" else workflow.ANOMALY_ESCALATED
    anomaly.resolution = resolution.strip()
    if action == "resolve":
        anomaly.resolved_at = timezone.now()
    anomaly.save(update_fields=["status", "resolution", "resolved_at", "updated_at"])
    _log(actor, f"anomaly.{action}d", "anomaly", anomaly.pk, before, anomaly.status, role=role)
    if action == "resolve" and anomaly.record and anomaly.record.status == workflow.ANOMALY_PENDING:
        anomaly.record.status = workflow.SUBMITTED
        anomaly.record.save(update_fields=["status", "updated_at"])
    _notify_user(anomaly.raised_by_id, "anomaly_update", "IAA anomaly updated",
                 f"Anomaly #{anomaly.pk} is now {anomaly.status}.", "anomaly", anomaly.pk)
    return anomaly


@transaction.atomic
def raise_observation(actor, payload: dict) -> AuditObservation:
    role = require(actor, "iaa.observation.create", roles=AUDIT_ROLES)
    record_kind = str(payload.get("record_kind", ""))
    record_id = int(payload.get("record_id", 0))
    record = get_record(actor, record_id)
    if record.record_kind != record_kind:
        raise NotFoundError("Financial record not found in the selected record type.")
    observation = AuditObservation.objects.create(
        record_kind=record_kind, record_id=record_id, department=record.department,
        title=str(payload.get("title", "")).strip(), details=str(payload.get("details", "")).strip(),
        raised_by_id=actor.user_id, concerned_user_id=record.created_by_id,
    )
    if not observation.title or not observation.details:
        raise ConflictError("Observation title and details are required.")
    _log(actor, "audit.observation_raised", "audit_observation", observation.pk,
         "", observation.status, {"record_id": record_id}, role)
    _notify_user(record.created_by_id, "audit_observation", "Audit observation raised",
                 f"An audit observation was raised for record #{record_id}.",
                 "audit_observation", observation.pk)
    return observation


@transaction.atomic
def respond_observation(actor, observation_id: int, *, response_text: str,
                        evidence_references: list | None = None) -> ObservationResponse:
    require(actor, "iaa.observation.respond", roles=BASIC_ROLES)
    obs = AuditObservation.objects.select_for_update().filter(
        pk=observation_id, status=workflow.OBSERVATION_OPEN).first()
    if obs is None:
        raise NotFoundError("Open observation not found.")
    if obs.concerned_user_id and obs.concerned_user_id != actor.user_id:
        raise PermissionDeniedError("Only the concerned user may respond.")
    if not response_text.strip():
        raise ConflictError("Corrective-action response is required.")
    response = ObservationResponse.objects.create(
        observation=obs, submitted_by_id=actor.user_id,
        response_text=response_text.strip(), evidence_references=evidence_references or [],
    )
    before = obs.status
    obs.status = workflow.OBSERVATION_RESPONDED
    obs.save(update_fields=["status", "updated_at"])
    _log(actor, "audit.observation_responded", "audit_observation", obs.pk,
         before, obs.status, {"response_id": response.pk})
    _notify_roles(AUDIT_ROLES, "observation_response", "Audit response received",
                  f"Observation #{obs.pk} is ready for verification.",
                  "audit_observation", obs.pk)
    return response


@transaction.atomic
def verify_observation(actor, observation_id: int, *, satisfactory: bool,
                       remarks: str) -> AuditObservation:
    role = require(actor, "iaa.observation.verify", roles=AUDIT_ROLES)
    obs = AuditObservation.objects.select_for_update().filter(
        pk=observation_id, status=workflow.OBSERVATION_RESPONDED).first()
    if obs is None:
        raise NotFoundError("Responded observation not found.")
    response = obs.responses.order_by("-created_at").first()
    has_evidence = bool(response and response.evidence_references)
    can_close = rules.may_close_observation(
        satisfactory=satisfactory, has_response=bool(response and response.response_text),
        has_evidence=has_evidence,
    )
    before = obs.status
    if satisfactory and not can_close:
        raise ConflictError("Satisfactory closure requires a response and supporting evidence.")
    obs.status = workflow.OBSERVATION_CLOSED if satisfactory else workflow.OBSERVATION_OPEN
    obs.verified_by_id = actor.user_id
    obs.verified_at = timezone.now()
    obs.verification_remarks = remarks.strip()
    obs.closed_at = timezone.now() if satisfactory else None
    obs.save(update_fields=["status", "verified_by_id", "verified_at",
                            "verification_remarks", "closed_at", "updated_at"])
    _log(actor, "audit.observation_verified", "audit_observation", obs.pk,
         before, obs.status, {"satisfactory": satisfactory, "remarks": remarks}, role)
    _notify_user(obs.concerned_user_id, "observation_verified", "Audit response reviewed",
                 f"Observation #{obs.pk} is now {obs.status}.", "audit_observation", obs.pk)
    return obs


@transaction.atomic
def switch_active_role(actor, role_name: str, auth_token: str | None) -> ActiveRoleSelection:
    if actor is None:
        raise PermissionDeniedError("Authentication required.", code="not_authenticated")
    chosen = normalize_role(role_name)
    assigned = {normalize_role(r) for r in getattr(actor, "roles", ())}
    if chosen not in assigned:
        raise PermissionDeniedError("You cannot activate a role that is not assigned by IAM.")
    if not auth_token:
        raise ConflictError("A session token is required to change the active IAM role.")
    iam_role = next(
        (str(role) for role in getattr(actor, "roles", ())
         if normalize_role(role) == chosen),
        role_name,
    )
    try:
        get_client().set_active_role(auth_token, iam_role)
    except IamUnavailable as exc:
        raise ConflictError(f"Fusion IAM could not update the active role: {exc}",
                            code="iam_role_switch_unavailable") from exc
    except ValueError as exc:
        raise ConflictError(str(exc), code="invalid_active_role") from exc
    selection, _ = ActiveRoleSelection.objects.update_or_create(
        user_id=actor.user_id, defaults={"role": chosen})
    _log(actor, "role.active_role_switched", "active_role", actor.user_id,
         normalize_role(getattr(actor, "active_role", "")), chosen,
         {"selected_role": chosen, "identity_provider": "Fusion IAM"}, chosen)
    return selection


@transaction.atomic
def assign_role(actor, *, user_id: int, role_name: str, active: bool = True) -> RoleAssignment:
    role = require(actor, "iaa.configuration.manage", roles=ADMIN_ROLES, operational=False)
    assignment, _ = RoleAssignment.objects.update_or_create(
        user_id=user_id, role=normalize_role(role_name),
        defaults={"assigned_by_id": actor.user_id, "is_active": active},
    )
    _log(actor, "configuration.role_assignment", "role_assignment", assignment.pk,
         details={"user_id": user_id, "role": assignment.role, "active": active}, role=role)
    return assignment


@transaction.atomic
def configure_approval_rule(actor, payload: dict) -> ApprovalRule:
    role = require(actor, "iaa.configuration.manage", roles=ADMIN_ROLES, operational=False)
    levels = payload.get("levels") or []
    if any(normalize_role(x.get("role")) not in AUTHORITY_ROLES for x in levels):
        raise ConflictError("Routes may assign only distinct HoD, Dean, or Director authorities.")
    if len({normalize_role(x.get("role")) for x in levels}) != len(levels):
        raise ConflictError("An approval route cannot repeat the same authority role.")
    minimum = payload.get("min_amount")
    maximum = payload.get("max_amount")
    if minimum is not None and maximum is not None and Decimal(str(minimum)) > Decimal(str(maximum)):
        raise ConflictError("Approval route minimum amount cannot exceed its maximum.")
    for level in levels:
        timeout = level.get("timeout_hours")
        if timeout not in (None, "") and int(timeout) <= 0:
            raise ConflictError("Approval timeout hours must be positive.")
        assigned_user = level.get("user_id")
        if assigned_user not in (None, "") and int(assigned_user) <= 0:
            raise ConflictError("Approval assignee must be a valid positive IAM user id.")
    rule = ApprovalRule.objects.create(
        record_kind=str(payload.get("record_kind", "")),
        request_type=str(payload.get("request_type", "")),
        department=str(payload.get("department", "")),
        min_amount=payload.get("min_amount"), max_amount=payload.get("max_amount"),
        levels=levels, priority=int(payload.get("priority", 100)),
        is_active=bool(payload.get("is_active", True)),
    )
    _log(actor, "configuration.approval_rule_created", "approval_rule", rule.pk,
         details={"levels": levels}, role=role)
    return rule


@transaction.atomic
def configure_financial_year(actor, payload: dict) -> FinancialYearPolicy:
    role = require(actor, "iaa.configuration.manage", roles=ADMIN_ROLES, operational=False)
    if payload.get("starts_on") and payload.get("ends_on") and payload["ends_on"] < payload["starts_on"]:
        raise ConflictError("Financial year end must be on or after its start.")
    overlapping = FinancialYearPolicy.objects.exclude(
        financial_year=str(payload["financial_year"])
    ).filter(starts_on__lte=payload["ends_on"], ends_on__gte=payload["starts_on"]).exists()
    if overlapping:
        raise ConflictError("Financial year dates overlap another configured financial year.")
    policy, _ = FinancialYearPolicy.objects.update_or_create(
        financial_year=str(payload["financial_year"]),
        defaults={"starts_on": payload["starts_on"], "ends_on": payload["ends_on"],
                  "settings": payload.get("settings") or {},
                  "is_active": bool(payload.get("is_active", True))},
    )
    _log(actor, "configuration.financial_year_updated", "financial_year_policy",
         policy.pk, details={"financial_year": policy.financial_year}, role=role)
    return policy


@transaction.atomic
def escalate_overdue_approvals(now=None) -> int:
    """IAA-UC-203: event worker for configured overdue authority decisions."""
    now = now or timezone.now()
    steps = (ApprovalStep.objects.select_for_update().select_related("record")
             .filter(status="pending", due_at__isnull=False, due_at__lte=now))
    count = 0
    for step in steps:
        next_step = ApprovalStep.objects.select_for_update().filter(
            record=step.record, step_number__gt=step.step_number, status="queued"
        ).exclude(assigned_user_id=step.record.created_by_id).order_by("step_number").first()
        before = step.record.status
        step.status = "escalated"
        step.save(update_fields=["status", "updated_at"])
        if next_step:
            next_step.status = "pending"
            next_step.due_at = now + timezone.timedelta(hours=next_step.timeout_hours) if next_step.timeout_hours else None
            next_step.save(update_fields=["status", "due_at", "updated_at"])
            step.record.current_approval_step = next_step.step_number
        step.record.status = workflow.ESCALATED
        step.record.save(update_fields=["status", "current_approval_step", "updated_at"])
        _log(None, "approval.timeout_escalated", "financial_record", step.record_id,
             before, step.record.status, {"from_role": step.authority_role,
                                          "to_role": next_step.authority_role if next_step else None},
             "system")
        if next_step:
            _notify_roles({normalize_role(next_step.authority_role)}, "approval_escalated",
                          "Overdue IAA approval escalated",
                          f"Request #{step.record_id} was escalated to your role.",
                          "financial_record", step.record_id)
        _notify_user(step.record.created_by_id, "approval_escalated", "IAA approval escalated",
                     f"Request #{step.record_id} was escalated to the next authority.",
                     "financial_record", step.record_id)
        count += 1
    return count


def visible_anomalies(actor):
    role = actor_role(actor)
    if role in ADMIN_ROLES:
        raise PermissionDeniedError("System Admin cannot access operational anomaly records.")
    qs = Anomaly.objects.select_related("record")
    if role in BASIC_ROLES:
        return qs.filter(record__created_by_id=actor.user_id)
    if role in FINANCE_ROLES | AUDIT_ROLES:
        return qs
    if role in AUTHORITY_ROLES:
        record_ids = visible_records(actor).values_list("pk", flat=True)
        return qs.filter(Q(record_id__in=record_ids) |
                         Q(resolver_role=role) |
                         Q(resolver_user_id=actor.user_id))
    raise PermissionDeniedError("No anomaly visibility is assigned to this role.")


def visible_observations(actor):
    role = actor_role(actor)
    if role in ADMIN_ROLES:
        raise PermissionDeniedError("System Admin cannot access operational audit content.")
    qs = AuditObservation.objects.all().prefetch_related("responses")
    if role in AUDIT_ROLES:
        return qs
    if role in BASIC_ROLES:
        return qs.filter(concerned_user_id=actor.user_id)
    return qs.none()


def report_summary(actor) -> dict:
    role = require(actor, "iaa.report.view", roles=FINANCE_ROLES | AUTHORITY_ROLES | AUDIT_ROLES)
    qs = FinancialRecord.objects.all()
    decision_qs = ApprovalStep.objects.all()
    if role in AUTHORITY_ROLES:
        scoped_ids = ApprovalStep.objects.filter(
            Q(authority_role=role) | Q(assigned_user_id=actor.user_id)
        ).values_list("record_id", flat=True)
        qs = qs.filter(pk__in=scoped_ids).distinct()
        decision_qs = decision_qs.filter(
            Q(authority_role=role) | Q(assigned_user_id=actor.user_id)
        )
    counts = {state: qs.filter(status=state).count()
              for state, _ in FinancialRecord.STATUSES}
    record_ids = qs.values_list("pk", flat=True)
    if role in AUTHORITY_ROLES:
        anomalies_qs = Anomaly.objects.filter(
            Q(record_id__in=record_ids) | Q(resolver_role=role) |
            Q(resolver_user_id=actor.user_id))
    else:
        anomalies_qs = Anomaly.objects.all()
    observations_qs = AuditObservation.objects.filter(record_id__in=record_ids)
    decisions = decision_qs.exclude(decided_at__isnull=True)
    turnaround = [
        (step.decided_at - step.created_at).total_seconds()
        for step in decisions
    ]
    avg_hours = (sum(turnaround) / len(turnaround) / 3600) if turnaround else None
    return {
        "record_status_counts": counts, "total_records": qs.count(),
        "total_anomalies": anomalies_qs.count(),
        "open_anomalies": anomalies_qs.filter(status="open").count(),
        "total_observations": observations_qs.count(),
        "open_observations": observations_qs.filter(status="open").count(),
        "average_approval_turnaround_hours": round(avg_hours, 2) if avg_hours is not None else None,
    }


@transaction.atomic
def configure_department_budget(actor, payload: dict) -> DepartmentBudget:
    role = require(actor, "iaa.configuration.manage", roles=ADMIN_ROLES, operational=False)
    budget, _ = DepartmentBudget.objects.update_or_create(
        department=str(payload["department"]).strip(),
        financial_year=str(payload["financial_year"]),
        defaults={
            "allocated": payload["allocated"],
            "spent": payload.get("spent", Decimal("0")),
            "committed": payload.get("committed", Decimal("0")),
            "is_active": bool(payload.get("is_active", True)),
        },
    )
    if min(budget.allocated, budget.spent, budget.committed) < 0:
        raise ConflictError("Budget amounts cannot be negative.")
    _log(actor, "configuration.department_budget_updated", "department_budget",
         budget.pk, details={"department": budget.department,
                             "financial_year": budget.financial_year}, role=role)
    return budget


def audit_logs_for(actor):
    require(actor, "iaa.audit.review", roles=AUDIT_ROLES)
    return AuditLog.objects.all().order_by("-created_at")


def build_csv_report(actor) -> str:
    require(actor, "iaa.report.export",
            roles=FINANCE_ROLES | AUTHORITY_ROLES | AUDIT_ROLES)
    data = report_summary(actor)
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["metric", "value"])
    writer.writerow(["total_records", data["total_records"]])
    writer.writerow(["total_anomalies", data["total_anomalies"]])
    writer.writerow(["open_anomalies", data["open_anomalies"]])
    writer.writerow(["total_observations", data["total_observations"]])
    writer.writerow(["open_observations", data["open_observations"]])
    writer.writerow(["average_approval_turnaround_hours", data["average_approval_turnaround_hours"] or ""])
    for key, value in data["record_status_counts"].items():
        writer.writerow([f"records_{key}", value])
    return stream.getvalue()
