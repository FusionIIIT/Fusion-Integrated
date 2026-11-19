"""Core request, TA, approval, anomaly, and audit-observation workflows."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from modules.iaa.domain import state_machine as sm
from modules.iaa.models import (
    ActionHistory, Anomaly, ApprovalDecision, ApprovalRouteRule, ApprovalStep,
    AuditObservation, AuditResponse, AutomaticAnomalyEvent, DepartmentBudget,
    ExpenseVoucherRequest, FinancialYear, IaaNotification, IaaRoleAssignment,
    Evidence, PolicyParameter, TravelAllowanceClaim,
)
from modules.iaa.services.authz import IaaAccessError, require


class IaaRuleError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid_iaa_action"):
        super().__init__(message)
        self.code = code


def _audit(*, record_type, record_id, action, actor=None, role="System",
           source="", destination="", remarks="", details=None):
    return ActionHistory.objects.create(
        record_type=record_type, record_id=record_id, action=action,
        actor_user_id=getattr(actor, "user_id", None), actor_role=role,
        source_status=source, destination_status=destination,
        remarks=remarks or "", details=details or {},
    )


def _notify(user_id, role, event, title, message, record_type="", record_id=None):
    if user_id is None:
        return None
    return IaaNotification.objects.create(
        user_id=user_id, actor_role=role or "", event=event, title=title,
        message=message, record_type=record_type, record_id=record_id)


def _eligible_users(role, department, exclude=()):
    scopes = IaaRoleAssignment.objects.filter(role=role, is_active=True)
    exact = scopes.filter(department=department)
    scopes = exact if exact.exists() else scopes.filter(department="")
    return list(scopes.exclude(user_id__in=exclude).order_by("user_id")
                .values_list("user_id", flat=True).distinct())


def _matching_route(record, *, record_type, request_type):
    amount = record.amount if record_type == "request" else record.claimed_amount
    candidates = list(ApprovalRouteRule.objects.filter(is_active=True).filter(
        Q(request_type=request_type) | Q(request_type="")
    ).filter(Q(department=record.department) | Q(department="")).filter(
        Q(minimum_amount__isnull=True) | Q(minimum_amount__lte=amount)
    ).filter(Q(maximum_amount__isnull=True) | Q(maximum_amount__gte=amount)))
    candidates.sort(key=lambda r: (r.priority,
                                   bool(r.department), bool(r.request_type)), reverse=True)
    if not candidates:
        return None
    rank = (candidates[0].priority, bool(candidates[0].department),
            bool(candidates[0].request_type))
    tied = [r for r in candidates if (r.priority, bool(r.department),
                                      bool(r.request_type)) == rank]
    if len(tied) > 1:
        raise IaaRuleError("Approval route configuration is ambiguous.",
                           code="ambiguous_approval_route")
    route = candidates[0]
    if not isinstance(route.levels, list) or not route.levels:
        raise IaaRuleError("Approval route has no configured authority levels.",
                           code="invalid_approval_route")
    if any(role not in sm.AUTHORITIES for role in route.levels):
        raise IaaRuleError("Approval route contains an unsupported authority role.",
                           code="invalid_approval_role")
    return route


def _make_steps(record, *, record_type, route):
    created = []
    for level, authority_role in enumerate(route.levels, start=1):
        assigned = _eligible_users(authority_role, record.department,
                                   exclude=(record.created_by_id if record_type == "request"
                                            else record.claimant_user_id,))
        if not assigned:
            continue
        created.append(ApprovalStep.objects.create(
            record_type=record_type, record_id=record.pk, level=level,
            authority_role=authority_role, assigned_user_id=assigned[0],
            status="Queued", due_at=None, timeout_seconds=route.timeout_seconds,
            escalation_roles=route.escalation_roles))
    if not created:
        raise IaaRuleError("No eligible configured authority is assigned to this route.",
                           code="approval_route_unassigned")
    return created


def _activate_first(steps):
    first = steps[0]
    first.status = "Pending"
    if first.timeout_seconds:
        first.due_at = timezone.now() + timezone.timedelta(
            seconds=first.timeout_seconds)
    first.save(update_fields=("status", "due_at"))
    return first


def _active_step(record_type, record_id, actor):
    step = ApprovalStep.objects.filter(
        record_type=record_type, record_id=record_id,
        assigned_user_id=actor.user_id, status__in=("Pending", "Escalated"),
    ).order_by("level", "id").first()
    if step is None:
        raise IaaRuleError("No approval action is assigned to this user.",
                           code="approval_not_assigned")
    return step


def _target_exists(record_type, record_id):
    model = {"request": ExpenseVoucherRequest,
             "ta_claim": TravelAllowanceClaim}.get(record_type)
    return bool(model and model.objects.filter(pk=record_id).exists())


def _activate_next(record_type, record_id):
    step = (ApprovalStep.objects.filter(record_type=record_type, record_id=record_id,
                                        status="Queued")
            .order_by("level", "id").first())
    if step is None:
        return None
    step.status = "Pending"
    if step.timeout_seconds:
        step.due_at = timezone.now() + timezone.timedelta(
            seconds=step.timeout_seconds)
    step.save(update_fields=("status", "due_at"))
    return step


def _transition(record, *, record_type, destination, role, actor, values,
                action, remarks="", details=None):
    source = record.status
    transition = sm.validate_transition(record_type, source, destination, role,
                                        values=values)
    record.status = transition.destination
    record.updated_at = timezone.now()
    record.save()
    _audit(record_type=record_type, record_id=record.pk, action=action,
           actor=actor, role=role, source=source, destination=record.status,
           remarks=remarks, details=details)
    return record


@transaction.atomic
def save_request(*, principal, role, values, request_id=None):
    require(principal, role, "iaa.request.create" if request_id is None
            else "iaa.request.update")
    if role != sm.BASIC_USER:
        raise IaaAccessError("Only a Basic User may create or edit a request.")
    if request_id:
        record = ExpenseVoucherRequest.objects.select_for_update().filter(
            pk=request_id, created_by_id=principal.user_id, status="Draft").first()
        if record is None:
            raise IaaRuleError("Draft request was not found.", code="request_not_found")
    else:
        record = ExpenseVoucherRequest(created_by_id=principal.user_id)
    for field in ("department", "request_type", "amount", "description",
                  "supporting_information"):
        if field in values:
            setattr(record, field, values[field])
    record.updated_at = timezone.now()
    record.save()
    _audit(record_type="request", record_id=record.pk,
           action="draft_saved", actor=principal, role=role,
           source="Draft" if request_id else "", destination="Draft")
    return record


@transaction.atomic
def submit_request(*, principal, role, request_id):
    require(principal, role, "iaa.request.create")
    record = ExpenseVoucherRequest.objects.select_for_update().filter(
        pk=request_id, created_by_id=principal.user_id).first()
    if record is None:
        raise IaaRuleError("Draft request was not found.", code="request_not_found")
    complete = bool(record.request_type and record.department
                    and record.amount is not None and record.description.strip())
    sm.validate_transition("request", record.status, "Submitted", role,
                           values={"complete": complete})
    record.submitted_at = timezone.now()
    record.updated_at = record.submitted_at
    record.status = "Submitted"
    finance_ids = _eligible_users(sm.FINANCE, record.department)
    record.assigned_finance_user_id = None
    record.save()
    _audit(record_type="request", record_id=record.pk, action="submitted",
           actor=principal, role=role, source="Draft", destination="Submitted",
           details={"routing_issue": "finance_assignment_missing" if not finance_ids else ""})
    for user_id in finance_ids:
        _notify(user_id, sm.FINANCE, "request_submitted", "Request submitted",
                "An expense/voucher request is ready for Finance validation.",
                "request", record.pk)
    return record


def _budget_check(*, department, amount, record_type, record_id):
    year = FinancialYear.objects.filter(is_active=True).order_by("-starts_on").first()
    if year is None:
        raise IaaRuleError("No active financial year is configured.",
                           code="financial_year_unconfigured")
    budget = DepartmentBudget.objects.filter(
        financial_year=year, department=department).first()
    if budget is None:
        raise IaaRuleError("No budget is configured for this department and year.",
                           code="department_budget_unconfigured")
    sufficient = budget.available_amount >= amount
    if not sufficient:
        AutomaticAnomalyEvent.objects.get_or_create(
            record_type=record_type, record_id=record_id,
            condition="budget_insufficient",
            defaults={"context": {"department": department,
                                  "available": str(budget.available_amount),
                                  "amount": str(amount)}})
    return sufficient


def _begin_approval(record, *, record_type, request_type, actor, role):
    route = _matching_route(record, record_type=record_type, request_type=request_type)
    if route is None:
        if record_type == "ta_claim":
            return None
        raise IaaRuleError("No configured approval route matches this request.",
                           code="approval_route_missing")
    steps = _make_steps(record, record_type=record_type, route=route)
    first = _activate_first(steps)
    record.active_route_id = route.pk
    record.current_approval_level = first.level
    return route, first


@transaction.atomic
def review_request(*, principal, role, request_id, action, remarks=""):
    require(principal, role, "iaa.request.review")
    record = ExpenseVoucherRequest.objects.select_for_update().filter(
        pk=request_id).first()
    if record is None:
        raise IaaRuleError("Request was not found.", code="request_not_found")
    if record.assigned_finance_user_id not in (None, principal.user_id):
        raise IaaAccessError("This request is assigned to another Finance reviewer.")
    if record.assigned_finance_user_id is None:
        record.assigned_finance_user_id = principal.user_id
        record.save(update_fields=("assigned_finance_user_id",))
    if action == "clarification":
        return _transition(record, record_type="request", destination="Query Raised",
                           role=role, actor=principal,
                           values={"remarks": remarks}, action="clarification_requested",
                           remarks=remarks)
    if action != "validate":
        raise IaaRuleError("Unknown Finance review action.")
    if not record.department or record.amount is None:
        raise IaaRuleError("Request department and amount are required for review.",
                           code="request_incomplete")
    sufficient = _budget_check(department=record.department, amount=record.amount,
                               record_type="request", record_id=record.pk)
    source = record.status
    if source not in ("Submitted", "Query Responded"):
        raise IaaRuleError("Request is not awaiting Finance validation.",
                           code="request_not_reviewable")
    try:
        route_and_step = _begin_approval(record, record_type="request",
                                         request_type=record.request_type,
                                         actor=principal, role=role)
    except IaaRuleError:
        # Keep the request in its current review state and leave an attributable
        # configuration issue rather than losing a successful budget check.
        _audit(record_type="request", record_id=record.pk,
               action="approval_route_unavailable", actor=principal, role=role,
               source=source, destination=source)
        return record
    result = _transition(record, record_type="request", destination="Finance Validated",
                         role=role, actor=principal,
                         values={"passed": True}, action="finance_validated",
                         details={"budget_sufficient": sufficient})
    if route_and_step:
        route, step = route_and_step
        step.status = "Pending"
        step.save(update_fields=("status",))
        result.status = "Approval Pending"
        result.current_approval_level = step.level
        result.active_route_id = route.pk
        result.save(update_fields=("status", "current_approval_level", "active_route_id", "updated_at"))
        _audit(record_type="request", record_id=record.pk, action="approval_routed",
               actor=principal, role=role, source="Finance Validated",
               destination="Approval Pending", details={"assigned_user_id": step.assigned_user_id,
                                                        "authority_role": step.authority_role})
        _notify(step.assigned_user_id, step.authority_role, "approval_pending",
                "Approval required", "An IAA request is awaiting your decision.",
                "request", record.pk)
    return result


@transaction.atomic
def respond_request(*, principal, role, request_id, response, details=None):
    require(principal, role, "iaa.request.update")
    record = ExpenseVoucherRequest.objects.select_for_update().filter(
        pk=request_id, created_by_id=principal.user_id, status="Query Raised").first()
    if record is None:
        raise IaaRuleError("No open Finance clarification was found.",
                           code="clarification_not_found")
    result = _transition(record, record_type="request", destination="Query Responded",
                         role=role, actor=principal,
                         values={"response": response}, action="clarification_responded",
                         remarks=response, details=details)
    if record.assigned_finance_user_id:
        _notify(record.assigned_finance_user_id, sm.FINANCE,
                "clarification_response", "Clarification response received",
                "The request creator has responded to your query.",
                "request", record.pk)
    return result


@transaction.atomic
def decide_request(*, principal, role, request_id, decision, remarks=""):
    require(principal, role, "iaa.request.approve")
    record = ExpenseVoucherRequest.objects.select_for_update().filter(pk=request_id).first()
    if record is None:
        raise IaaRuleError("Request was not found.", code="request_not_found")
    if principal.user_id == record.created_by_id:
        raise IaaAccessError("A request creator cannot approve their own request.")
    step = _active_step("request", record.pk, principal)
    if step.authority_role != role:
        raise IaaAccessError("The approval is assigned to a different authority role.")
    if decision not in ("Approved", "Rejected"):
        raise IaaRuleError("Decision must be Approved or Rejected.")
    next_step = ApprovalStep.objects.filter(
        record_type="request", record_id=record.pk, status="Queued",
        level__gt=step.level).order_by("level", "id").first()
    destination = ("Rejected" if decision == "Rejected" else
                   "Approval Pending" if next_step else "Approved")
    source = record.status
    transition = sm.validate_transition(
        "request", source, destination, role,
        values={"remarks": remarks, "more_levels": bool(next_step)})
    step.status = decision
    step.resolved_at = timezone.now()
    step.save(update_fields=("status", "resolved_at"))
    ApprovalDecision.objects.create(step=step, decision=decision,
                                    remarks=remarks, actor_user_id=principal.user_id,
                                    actor_role=role)
    record.status = transition.destination
    record.current_approval_level = next_step.level if next_step and decision == "Approved" else record.current_approval_level
    record.updated_at = timezone.now()
    record.save()
    if next_step and decision == "Approved":
        _activate_next("request", record.pk)
    _audit(record_type="request", record_id=record.pk,
           action=decision.lower(), actor=principal, role=role,
           source=source, destination=record.status, remarks=remarks)
    _notify(record.created_by_id, sm.BASIC_USER, "request_decision",
            f"Request {decision.lower()}", f"Your request was {decision.lower()}.",
            "request", record.pk)
    if next_step and decision == "Approved":
        _notify(next_step.assigned_user_id, next_step.authority_role,
                "approval_pending", "Approval required",
                "An IAA request is awaiting your decision.", "request", record.pk)
    return record


@transaction.atomic
def record_request(*, principal, role, request_id, processing_details=""):
    require(principal, role, "iaa.request.review")
    record = ExpenseVoucherRequest.objects.select_for_update().filter(
        pk=request_id, status="Approved").first()
    if record is None:
        raise IaaRuleError("Only an approved request can be recorded.",
                           code="request_not_approved")
    result = _transition(record, record_type="request", destination="Recorded",
                         role=role, actor=principal,
                         values={"complete": bool(processing_details.strip())},
                         action="internally_processed", remarks=processing_details,
                         details={"monetary_transfer": False})
    result.recorded_at = timezone.now()
    result.save(update_fields=("recorded_at",))
    _notify(result.created_by_id, sm.BASIC_USER, "request_recorded",
            "Request recorded", "Internal processing has been recorded.",
            "request", result.pk)
    return result


@transaction.atomic
def submit_ta_claim(*, principal, role, values, evidence_files=()):
    require(principal, role, "iaa.ta_claim.create")
    if role != sm.BASIC_USER or getattr(principal, "kind", "") not in ("faculty", "staff"):
        raise IaaAccessError("Only an eligible faculty or staff Basic User may submit a TA claim.")
    required = (values.get("department"), values.get("trip_start"),
                values.get("trip_end"), values.get("purpose"),
                values.get("claimed_amount"), bool(evidence_files))
    if not all(required):
        raise IaaRuleError("TA trip details, amount, department, and supporting evidence are required.",
                           code="ta_submission_incomplete")
    claim = TravelAllowanceClaim.objects.create(
        claimant_user_id=principal.user_id,
        department=values["department"], trip_start=values["trip_start"],
        trip_end=values["trip_end"], purpose=values["purpose"],
        claimed_amount=values["claimed_amount"], trip_details=values.get("trip_details", {}))
    from core.files.validators import sanitise_filename
    for uploaded in evidence_files:
        Evidence.objects.create(
            record_type="ta_claim", record_id=claim.pk,
            purpose="supporting_document", file=uploaded,
            original_filename=sanitise_filename(uploaded.name),
            uploaded_by_id=principal.user_id)
    _audit(record_type="ta_claim", record_id=claim.pk, action="submitted",
           actor=principal, role=role, destination="Submitted")
    sufficient = _budget_check(department=claim.department, amount=claim.claimed_amount,
                               record_type="ta_claim", record_id=claim.pk)
    _audit(record_type="ta_claim", record_id=claim.pk, action="budget_checked",
           actor=principal, role=role, source="Submitted", destination="Submitted",
           details={"budget_sufficient": sufficient})
    return claim


@transaction.atomic
def review_ta_claim(*, principal, role, claim_id, action, policy_passed=True,
                    remarks=""):
    require(principal, role, "iaa.ta_claim.review")
    claim = TravelAllowanceClaim.objects.select_for_update().filter(pk=claim_id).first()
    if claim is None:
        raise IaaRuleError("TA claim was not found.", code="ta_claim_not_found")
    if action == "clarification":
        return _transition(claim, record_type="ta_claim", destination="Query Raised",
                           role=role, actor=principal, values={"remarks": remarks},
                           action="clarification_requested", remarks=remarks)
    if action != "verify":
        raise IaaRuleError("Unknown TA verification action.")
    if not policy_passed:
        return _transition(claim, record_type="ta_claim", destination="Rejected",
                           role=role, actor=principal, values={"passed": False},
                           action="policy_verification_failed", remarks=remarks)
    _budget_check(department=claim.department, amount=claim.claimed_amount,
                  record_type="ta_claim", record_id=claim.pk)
    route = _matching_route(claim, record_type="ta_claim", request_type="ta_claim")
    if route:
        steps = _make_steps(claim, record_type="ta_claim", route=route)
        step = _activate_first(steps)
        claim.active_route_id = route.pk
        claim.current_approval_level = step.level
        dest = "Approval Pending"
    else:
        dest = "Verified"
    result = _transition(claim, record_type="ta_claim", destination=dest,
                         role=role, actor=principal,
                         values={"passed": True}, action="verified",
                         details={"approval_required": bool(route)})
    if route:
        claim.active_route_id = route.pk
        claim.current_approval_level = step.level
        claim.save(update_fields=("active_route_id", "current_approval_level"))
        _notify(step.assigned_user_id, step.authority_role, "approval_pending",
                "TA approval required", "A TA claim is awaiting your decision.",
                "ta_claim", claim.pk)
    return result


@transaction.atomic
def respond_ta_claim(*, principal, role, claim_id, response):
    require(principal, role, "iaa.ta_claim.update")
    claim = TravelAllowanceClaim.objects.select_for_update().filter(
        pk=claim_id, claimant_user_id=principal.user_id,
        status="Query Raised").first()
    if claim is None:
        raise IaaRuleError("No open TA clarification was found.",
                           code="clarification_not_found")
    return _transition(claim, record_type="ta_claim", destination="Query Responded",
                       role=role, actor=principal, values={"response": response},
                       action="clarification_responded", remarks=response)


@transaction.atomic
def decide_ta_claim(*, principal, role, claim_id, decision, remarks=""):
    require(principal, role, "iaa.ta_claim.approve")
    claim = TravelAllowanceClaim.objects.select_for_update().filter(pk=claim_id).first()
    if claim is None:
        raise IaaRuleError("TA claim was not found.", code="ta_claim_not_found")
    if claim.claimant_user_id == principal.user_id:
        raise IaaAccessError("A claimant cannot approve their own TA claim.")
    step = _active_step("ta_claim", claim.pk, principal)
    if step.authority_role != role:
        raise IaaAccessError("The approval is assigned to a different authority role.")
    if decision not in ("Approved", "Rejected"):
        raise IaaRuleError("Decision must be Approved or Rejected.")
    next_step = ApprovalStep.objects.filter(record_type="ta_claim", record_id=claim.pk,
                                            status="Queued", level__gt=step.level).first()
    dest = "Rejected" if decision == "Rejected" else "Approval Pending" if next_step else "Approved"
    transition = sm.validate_transition("ta_claim", claim.status, dest, role,
                                        values={"remarks": remarks, "more_levels": bool(next_step)})
    step.status = decision; step.resolved_at = timezone.now()
    step.save(update_fields=("status", "resolved_at"))
    ApprovalDecision.objects.create(step=step, decision=decision, remarks=remarks,
                                    actor_user_id=principal.user_id, actor_role=role)
    source = claim.status; claim.status = transition.destination
    claim.current_approval_level = next_step.level if next_step and decision == "Approved" else claim.current_approval_level
    claim.updated_at = timezone.now(); claim.save()
    if next_step and decision == "Approved": _activate_next("ta_claim", claim.pk)
    _audit(record_type="ta_claim", record_id=claim.pk, action=decision.lower(),
           actor=principal, role=role, source=source, destination=claim.status,
           remarks=remarks)
    _notify(claim.claimant_user_id, sm.BASIC_USER, "ta_decision",
            f"TA claim {decision.lower()}", f"Your TA claim was {decision.lower()}.",
            "ta_claim", claim.pk)
    return claim


@transaction.atomic
def record_ta_claim(*, principal, role, claim_id, processing_details=""):
    require(principal, role, "iaa.ta_claim.review")
    claim = TravelAllowanceClaim.objects.select_for_update().filter(
        pk=claim_id, status__in=("Verified", "Approved")).first()
    if claim is None:
        raise IaaRuleError("Only a verified or approved TA claim can be recorded.",
                           code="ta_claim_not_verified")
    result = _transition(claim, record_type="ta_claim", destination="Recorded",
                         role=role, actor=principal,
                         values={"complete": bool(processing_details.strip())},
                         action="internally_processed", remarks=processing_details,
                         details={"monetary_transfer": False})
    result.recorded_at = timezone.now(); result.save(update_fields=("recorded_at",))
    return result


@transaction.atomic
def flag_anomaly(*, principal, role, record_type, record_id, category,
                 description, resolver_role, assigned_user_id=None):
    require(principal, role, "iaa.anomaly.create")
    if role not in (sm.FINANCE, sm.AUDITOR):
        raise IaaAccessError("Only Finance Staff or an Auditor may flag an anomaly.")
    if resolver_role not in (sm.FINANCE, *sm.AUTHORITIES, sm.AUDITOR):
        raise IaaRuleError("Anomaly resolver role is not permitted.")
    if not _target_exists(record_type, record_id):
        raise IaaRuleError("The financial record for this anomaly was not found.",
                           code="anomaly_target_not_found")
    anomaly = Anomaly.objects.create(
        record_type=record_type, record_id=record_id, category=category,
        description=description, resolver_role=resolver_role,
        assigned_user_id=assigned_user_id, created_by_id=principal.user_id,
        created_by_role=role)
    _audit(record_type="anomaly", record_id=anomaly.pk, action="flagged",
           actor=principal, role=role, destination="Open",
           details={"target_type": record_type, "target_id": record_id,
                    "category": category})
    return anomaly


@transaction.atomic
def resolve_anomaly(*, principal, role, anomaly_id, outcome, remarks):
    require(principal, role, "iaa.anomaly.update")
    anomaly = Anomaly.objects.select_for_update().filter(pk=anomaly_id).first()
    if anomaly is None:
        raise IaaRuleError("Anomaly was not found.", code="anomaly_not_found")
    if anomaly.resolver_role != role or anomaly.assigned_user_id not in (None, principal.user_id):
        raise IaaAccessError("This anomaly is assigned to another resolver.")
    if outcome not in ("Resolved", "Escalated"):
        raise IaaRuleError("Anomaly outcome must be Resolved or Escalated.")
    source = anomaly.status
    transition = sm.validate_transition("anomaly", source, outcome, role,
                                        values={"remarks": remarks})
    anomaly.status = transition.destination
    anomaly.resolved_at = timezone.now() if outcome == "Resolved" else None
    anomaly.save(update_fields=("status", "resolved_at"))
    _audit(record_type="anomaly", record_id=anomaly.pk, action=outcome.lower(),
           actor=principal, role=role, source=source, destination=outcome,
           remarks=remarks)
    return anomaly


@transaction.atomic
def raise_observation(*, principal, role, record_type, record_id,
                      department, title, description):
    require(principal, role, "iaa.audit_observation.create")
    if role != sm.AUDITOR:
        raise IaaAccessError("Only an Auditor may raise an audit observation.")
    if not _target_exists(record_type, record_id):
        raise IaaRuleError("The financial record for this observation was not found.",
                           code="observation_target_not_found")
    observation = AuditObservation.objects.create(
        record_type=record_type, record_id=record_id,
        auditor_user_id=principal.user_id, department=department,
        title=title, description=description)
    _audit(record_type="audit_observation", record_id=observation.pk,
           action="raised", actor=principal, role=role, destination="Open",
           details={"target_type": record_type, "target_id": record_id})
    for assignment in IaaRoleAssignment.objects.filter(
            role=sm.BASIC_USER, department__in=(department, ""), is_active=True):
        _notify(assignment.user_id, sm.BASIC_USER, "audit_observation_open",
                "Audit observation requires a response", title,
                "audit_observation", observation.pk)
    return observation


@transaction.atomic
def respond_observation(*, principal, role, observation_id, response):
    require(principal, role, "iaa.audit_observation.update")
    observation = AuditObservation.objects.select_for_update().filter(
        pk=observation_id, status="Open").first()
    if observation is None:
        raise IaaRuleError("Open audit observation was not found.",
                           code="observation_not_found")
    if role != sm.BASIC_USER:
        raise IaaAccessError("Only a concerned Basic User may respond.")
    if observation.department:
        allowed = IaaRoleAssignment.objects.filter(
            user_id=principal.user_id, role=sm.BASIC_USER,
            department=observation.department, is_active=True).exists()
        if not allowed:
            raise IaaAccessError("This observation is outside your department.")
    transition = sm.validate_transition("observation", "Open", "Responded", role,
                                        values={"response": response})
    answer = AuditResponse.objects.create(observation=observation,
                                          response=response,
                                          actor_user_id=principal.user_id,
                                          actor_role=role)
    observation.status = transition.destination
    observation.save(update_fields=("status",))
    _audit(record_type="audit_observation", record_id=observation.pk,
           action="response_submitted", actor=principal, role=role,
           source="Open", destination="Responded", remarks=response,
           details={"response_id": answer.pk})
    _notify(observation.auditor_user_id, sm.AUDITOR, "audit_response_received",
            "Audit response received", observation.title,
            "audit_observation", observation.pk)
    return answer


@transaction.atomic
def verify_observation(*, principal, role, observation_id, satisfactory, remarks):
    require(principal, role, "iaa.audit_observation.update")
    observation = AuditObservation.objects.select_for_update().filter(
        pk=observation_id, status="Responded").first()
    if observation is None:
        raise IaaRuleError("Responded audit observation was not found.",
                           code="observation_not_responded")
    if role != sm.AUDITOR or principal.user_id != observation.auditor_user_id:
        raise IaaAccessError("Only the assigned Auditor may verify this response.")
    destination = "Closed" if satisfactory else "Open"
    transition = sm.validate_transition("observation", "Responded", destination,
                                        role, values={"satisfactory": satisfactory})
    source = observation.status; observation.status = transition.destination
    if satisfactory: observation.closed_at = timezone.now()
    observation.save(update_fields=("status", "closed_at"))
    _audit(record_type="audit_observation", record_id=observation.pk,
           action="verification_satisfactory" if satisfactory else "verification_unsatisfactory",
           actor=principal, role=role, source=source, destination=destination,
           remarks=remarks)
    return observation


@transaction.atomic
def switch_role(*, principal, role):
    require(principal, role, "iaa.role.update")
    if role not in (sm.BASIC_USER, sm.FINANCE, sm.HOD, sm.DEAN,
                    sm.DIRECTOR, sm.AUDITOR, sm.ADMIN):
        raise IaaAccessError("That IAA role is not assigned to this user.")
    from modules.iaa.services.authz import available_roles
    if role not in available_roles(principal):
        raise IaaAccessError("That IAA role is not assigned to this user.")
    _audit(record_type="role", record_id=principal.user_id, action="active_role_switched",
           actor=principal, role=role, details={"active_role": role})
    return role
