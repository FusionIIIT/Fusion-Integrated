"""Transactional IAA use cases. API views should delegate writes here."""

from datetime import timedelta

from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone
from core.api.exceptions import ConflictError
from core.files import drive, validators

from modules.iaa.authorization import active_role, actor_id, require
from modules.iaa.domain.workflow import (
    ANOMALY_TRANSITIONS, EXPENSE_TRANSITIONS, OBSERVATION_TRANSITIONS,
    TA_TRANSITIONS, WorkflowError, expense_completeness, is_high_value,
    ta_completeness, transition,
)
from modules.iaa.models import (
    Anomaly, ApprovalRoute, ApprovalStep, AuditObservation, BudgetAllocation,
    ExpenseRequest, IaaAuditEvent, IaaNotificationOutbox, IaaPolicy,
    IaaProcessingIssue, IaaSupportingDocument, ObservationResponse, TravelClaim,
)


class IaaConflict(ConflictError):
    """The action conflicts with the current state or configured policy."""


class BudgetReferenceUnavailable(IaaConflict):
    def __init__(self, record_type, record_id):
        super().__init__("The applicable departmental budget reference is unavailable.")
        self.record_type = record_type
        self.record_id = record_id


def _audit(actor, record_type, record_id, action, before="", after="", details=None):
    IaaAuditEvent.objects.create(
        record_type=record_type, record_id=record_id,
        actor_user_id=actor_id(actor) if actor is not None else None,
        active_role=getattr(actor, "active_role", "") if actor is not None else "system",
        action=action, from_status=before, to_status=after, details=details or {},
    )


def _notify(user_id, record_type, record_id, event, **payload):
    if user_id is not None:
        IaaNotificationOutbox.objects.create(
            recipient_user_id=user_id, record_type=record_type,
            record_id=record_id, event=event, payload=payload)


def _documents_valid(actor, documents, *, required=True):
    if not documents:
        return not required
    try:
        ids = [int(item["document_id"]) for item in documents if isinstance(item, dict)]
    except (KeyError, TypeError, ValueError):
        return False
    if len(ids) != len(documents):
        return False
    found = IaaSupportingDocument.objects.filter(
        pk__in=ids, user_id=actor_id(actor), is_active=True).count()
    return found == len(set(ids)) and len(ids) == len(set(ids))


@transaction.atomic
def attach_document(actor, *, kind, drive_url, title=""):
    require(actor, "iaa.request.create" if kind != "ta" else "iaa.ta.create",
            roles={"basic_user"})
    if kind not in {"expense", "ta", "observation"}:
        raise IaaConflict("Document kind must be expense, ta, or observation.")
    try:
        link = drive.parse(drive_url)
    except drive.InvalidDriveLink as exc:
        raise ConflictError(exc.message, code=exc.code) from exc
    safe_title = validators.sanitise_filename(title, fallback="Supporting document")[:160]
    document, _ = IaaSupportingDocument.objects.get_or_create(
        user_id=actor_id(actor), kind=kind, drive_file_id=link.file_id,
        defaults={"title": safe_title, "drive_url": link.url})
    if not document.is_active:
        raise IaaConflict("This document reference is no longer active.")
    _audit(actor, "document", document.pk, "document_attached", "", "active",
           {"kind": kind})
    return document


def _policy():
    policy = IaaPolicy.objects.filter(is_active=True).order_by("-updated_at").first()
    if policy is None:
        raise IaaConflict("IAA policy configuration is unavailable.")
    return policy


def _route(request_type, department, amount):
    matches = ApprovalRoute.objects.filter(
        request_type=request_type, is_active=True, amount_from__lte=amount,
    ).filter(Q(department=department) | Q(department=""))
    matches = matches.filter(Q(amount_through__isnull=True) | Q(amount_through__gte=amount))
    route = matches.order_by(
        Case(When(department=department, then=Value(0)), default=Value(1),
             output_field=IntegerField()), "level", "id").first()
    if route is None:
        raise IaaConflict("No configured approval route matches this record.")
    return route


def _eligible_route(route, owner_user_id):
    """Skip a configured assignee barred from approving their own record."""
    seen = set()
    while route is not None and route.pk not in seen:
        seen.add(route.pk)
        if route.is_active and route.assignee_user_id is not None and route.assignee_user_id != owner_user_id:
            return route
        route = route.next_route
    return None


def _new_step(record_type, record, route):
    if route.assignee_user_id is None:
        raise IaaConflict("The configured approval level has no eligible assignee.")
    timeout = route.timeout_hours if route.timeout_hours is not None else _policy().approval_timeout_hours
    due_at = timezone.now() + timedelta(hours=timeout) if timeout else None
    return ApprovalStep.objects.create(
        record_type=record_type, record_id=record.pk, route=route,
        level=route.level, authority_role=route.authority_role,
        assignee_user_id=route.assignee_user_id, due_at=due_at)


def _start_approval(actor, record_type, record, route_type):
    before = record.status
    owner_id = record.creator_user_id if record_type == "expense" else record.claimant_user_id
    route = _eligible_route(_route(route_type, record.department, record.amount), owner_id)
    if route is None:
        raise IaaConflict("No eligible configured approving authority is available.")
    record.assigned_route = route
    table = EXPENSE_TRANSITIONS if record_type == "expense" else TA_TRANSITIONS
    record.status = transition(table, before, "route")
    record.save(update_fields=("assigned_route", "status", "updated_at"))
    step = _new_step(record_type, record, route)
    _audit(actor, record_type, record.pk, "approval_routed", before, record.status,
           {"step_id": step.pk, "role": route.authority_role})
    _notify(step.assignee_user_id, record_type, record.pk, "approval_pending",
            role=route.authority_role)
    _notify(owner_id, record_type, record.pk, "approval_pending")


@transaction.atomic
def create_expense_draft(actor, data):
    require(actor, "iaa.request.create", roles={"basic_user"})
    request = ExpenseRequest.objects.create(
        creator_user_id=actor_id(actor), request_type=data.get("request_type", ""),
        amount=data.get("amount"), department=data.get("department", ""),
        description=data.get("description", ""),
        supporting_documents=data.get("supporting_documents", []))
    _audit(actor, "expense", request.pk, "draft_created", "", request.status)
    return request


@transaction.atomic
def update_expense_draft(actor, request_id, data):
    require(actor, "iaa.request.create", roles={"basic_user"})
    request = ExpenseRequest.objects.select_for_update().get(pk=request_id)
    if request.creator_user_id != actor_id(actor) or request.status != "draft":
        raise IaaConflict("Only the creator may edit an expense draft.")
    before = request.status
    for key in ("request_type", "amount", "department", "description", "supporting_documents"):
        if key in data:
            setattr(request, key, data[key])
    request.save()
    _audit(actor, "expense", request.pk, "draft_updated", before, request.status)
    return request


@transaction.atomic
def submit_expense(actor, request_id):
    require(actor, "iaa.request.submit", roles={"basic_user"})
    request = ExpenseRequest.objects.select_for_update().get(pk=request_id)
    if request.creator_user_id != actor_id(actor):
        raise IaaConflict("Only the request creator may submit this request.")
    complete = expense_completeness({
        "request_type": request.request_type, "amount": request.amount,
        "department": request.department, "description": request.description,
        "documents": request.supporting_documents,
    }).complete and _documents_valid(actor, request.supporting_documents)
    if not complete:
        raise IaaConflict("Complete all required fields and attach supporting documents.")
    before = request.status
    request.status = transition(EXPENSE_TRANSITIONS, before, "submit")
    request.lock_version += 1
    request.save(update_fields=("status", "lock_version", "updated_at"))
    _audit(actor, "expense", request.pk, "submitted", before, request.status)
    _notify(request.creator_user_id, "expense", request.pk, "submitted")
    return request


@transaction.atomic
def finance_review_expense(actor, request_id, *, decision, notes="", clarification=""):
    require(actor, "iaa.finance.validate", roles={"finance_staff"})
    request = ExpenseRequest.objects.select_for_update().get(pk=request_id)
    if request.status not in {"submitted", "query_responded"}:
        raise IaaConflict("The request is not awaiting Finance review.")
    before = request.status
    if decision == "query":
        if not clarification.strip():
            raise IaaConflict("A clarification question is required.")
        request.status = transition(EXPENSE_TRANSITIONS, before, "query")
        request.clarification = clarification
    elif decision == "validate":
        request.status = transition(EXPENSE_TRANSITIONS, before, "validate")
        request.finance_notes = notes
        request.assigned_finance_user_id = actor_id(actor)
        _budget_check(actor, "expense", request.pk, request.department, request.amount)
    else:
        raise IaaConflict("Finance decision must be query or validate.")
    request.save()
    _audit(actor, "expense", request.pk, f"finance_{decision}", before, request.status)
    if decision == "query":
        _notify(request.creator_user_id, "expense", request.pk, "clarification_requested")
    else:
        _start_approval(actor, "expense", request, request.request_type)
    return request


@transaction.atomic
def submit_ta_claim(actor, data):
    require(actor, "iaa.ta.create", roles={"basic_user"})
    documents = data.get("supporting_documents", [])
    complete = ta_completeness({**data, "documents": documents}).complete
    if not complete or not _documents_valid(actor, documents):
        raise IaaConflict("Complete all required fields and attach supporting documents.")
    if data["trip_end"] < data["trip_start"]:
        raise IaaConflict("Trip end date cannot be before trip start date.")
    claim = TravelClaim.objects.create(
        claimant_user_id=actor_id(actor), department=data["department"],
        trip_start=data["trip_start"], trip_end=data["trip_end"],
        purpose=data["purpose"], amount=data["amount"], supporting_documents=documents)
    _audit(actor, "ta", claim.pk, "submitted", "", claim.status)
    _notify(claim.claimant_user_id, "ta", claim.pk, "submitted")
    return claim


@transaction.atomic
def finance_review_ta(actor, claim_id, *, decision, notes="", clarification=""):
    require(actor, "iaa.ta.verify", roles={"finance_staff"})
    claim = TravelClaim.objects.select_for_update().get(pk=claim_id)
    if claim.status not in {"submitted", "query_responded"}:
        raise IaaConflict("The TA claim is not awaiting Finance verification.")
    before = claim.status
    if decision == "query":
        if not clarification.strip():
            raise IaaConflict("A clarification question is required.")
        claim.status = transition(TA_TRANSITIONS, before, "query")
        claim.clarification = clarification
        claim.save()
        _notify(claim.claimant_user_id, "ta", claim.pk, "clarification_requested")
    elif decision == "verify":
        claim.finance_notes = notes
        claim.assigned_finance_user_id = actor_id(actor)
        _budget_check(actor, "ta", claim.pk, claim.department, claim.amount)
        claim.status = transition(TA_TRANSITIONS, before, "verify")
        claim.save()
        _audit(actor, "ta", claim.pk, "finance_verified", before, claim.status)
        if is_high_value(claim.amount, _policy().ta_high_value_threshold):
            _start_approval(actor, "ta", claim, "ta")
        else:
            _notify(claim.claimant_user_id, "ta", claim.pk, "verified")
    else:
        raise IaaConflict("Finance decision must be query or verify.")
    if decision == "query":
        _audit(actor, "ta", claim.pk, "finance_query", before, claim.status)
    return claim


@transaction.atomic
def respond_to_clarification(actor, record_type, record_id, *, response, documents=None):
    require(actor, "iaa.request.submit", roles={"basic_user"})
    model, owner_field = ((ExpenseRequest, "creator_user_id") if record_type == "expense"
                          else (TravelClaim, "claimant_user_id"))
    record = model.objects.select_for_update().get(pk=record_id)
    if getattr(record, owner_field) != actor_id(actor) or record.status != "query_raised":
        raise IaaConflict("Only the owner may respond to an open clarification.")
    if not response.strip():
        raise IaaConflict("A clarification response is required.")
    if documents and not _documents_valid(actor, documents, required=False):
        raise IaaConflict("Attach only active documents owned by your account.")
    before = record.status
    table = EXPENSE_TRANSITIONS if record_type == "expense" else TA_TRANSITIONS
    record.status = transition(table, before, "respond")
    record.clarification = ""
    if documents:
        record.supporting_documents = [*record.supporting_documents, *documents]
    record.save()
    _audit(actor, record_type, record.pk, "clarification_responded", before, record.status,
           {"response": response})
    _notify(record.assigned_finance_user_id, record_type, record.pk, "clarification_response")
    return record


@transaction.atomic
def decide_approval(actor, step_id, *, decision, remarks=""):
    role = require(actor, "iaa.approval.decide", roles={"hod", "dean", "director"})
    step = ApprovalStep.objects.select_for_update().select_related("route").get(pk=step_id)
    if step.status != "pending":
        raise IaaConflict("This approval step has already been resolved.")
    if step.assignee_user_id != actor_id(actor) or step.authority_role != role:
        raise IaaConflict("Only the assigned authority acting in the assigned role may decide.")
    model = ExpenseRequest if step.record_type == "expense" else TravelClaim
    record = model.objects.select_for_update().get(pk=step.record_id)
    owner_id = record.creator_user_id if step.record_type == "expense" else record.claimant_user_id
    if owner_id == actor_id(actor):
        raise IaaConflict("A request creator cannot approve that request.")
    if decision not in {"approve", "reject"} or not remarks.strip():
        raise IaaConflict("Select approve/reject and provide remarks.")
    before = record.status
    step.status = "approved" if decision == "approve" else "rejected"
    step.decided_at, step.remarks = timezone.now(), remarks
    step.save()
    table = EXPENSE_TRANSITIONS if step.record_type == "expense" else TA_TRANSITIONS
    if decision == "reject":
        record.status = transition(table, before, "reject")
        record.decision_remarks = remarks
        record.save()
        _audit(actor, step.record_type, record.pk, "approval_rejected", before, record.status,
               {"step_id": step.pk, "remarks": remarks})
        _notify(owner_id, step.record_type, record.pk, "rejected")
        return record
    route = step.route.next_route
    owner_id = record.creator_user_id if step.record_type == "expense" else record.claimant_user_id
    route = _eligible_route(route, owner_id)
    if route is not None:
        record.assigned_route = route
        record.save(update_fields=("assigned_route", "updated_at"))
        next_step = _new_step(step.record_type, record, route)
        _audit(actor, step.record_type, record.pk, "approval_level_approved", before, before,
               {"step_id": step.pk, "next_step_id": next_step.pk})
        _notify(next_step.assignee_user_id, step.record_type, record.pk, "approval_pending",
                role=route.authority_role)
    else:
        record.status = transition(table, before, "approve")
        record.decision_remarks = remarks
        record.save()
        _audit(actor, step.record_type, record.pk, "approval_approved", before, record.status,
               {"step_id": step.pk, "remarks": remarks})
        owner_id = record.creator_user_id if step.record_type == "expense" else record.claimant_user_id
        _notify(owner_id, step.record_type, record.pk, "approved")
    return record


@transaction.atomic
def escalate_overdue_approvals(now=None):
    """Idempotent event handler to register with the platform scheduler."""
    now = now or timezone.now()
    count = 0
    due = ApprovalStep.objects.select_for_update().filter(
        status="pending", due_at__isnull=False, due_at__lte=now).select_related("route")
    for step in due:
        model = ExpenseRequest if step.record_type == "expense" else TravelClaim
        record = model.objects.select_for_update().get(pk=step.record_id)
        owner_id = record.creator_user_id if step.record_type == "expense" else record.claimant_user_id
        route = _eligible_route(step.route.next_route, owner_id)
        if route is None:
            continue
        step.status = "escalated"
        step.save(update_fields=("status", "updated_at"))
        next_step = _new_step(step.record_type, record, route)
        _audit(None, step.record_type, step.record_id, "approval_escalated",
               "approval_pending", "approval_pending",
               {"from_step_id": step.pk, "to_step_id": next_step.pk})
        _notify(route.assignee_user_id, step.record_type, step.record_id,
                "approval_escalated", role=route.authority_role)
        count += 1
    return count


@transaction.atomic
def _budget_check(actor, record_type, record_id, department, amount):
    policy = _policy()
    today = timezone.localdate()
    start_year = today.year if today.month >= policy.financial_year_start_month else today.year - 1
    financial_year = f"{start_year}-{start_year + 1}"
    budgets = list(BudgetAllocation.objects.select_for_update().filter(
        department=department, financial_year=financial_year))
    if not budgets:
        raise BudgetReferenceUnavailable(record_type, record_id)
    IaaProcessingIssue.objects.filter(
        record_type=record_type, record_id=record_id, operation="finance_budget_check",
        status="open").update(status="resolved", resolved_by_user_id=actor_id(actor),
                               resolved_at=timezone.now())
    available = sum((budget.available_amount for budget in budgets), start=0)
    if amount is None or available >= amount:
        return None
    anomaly, created = Anomaly.objects.get_or_create(
        record_type=record_type, record_id=record_id, category="budget_insufficiency",
        status="open", defaults={
            "description": "Available departmental budget is below the requested amount.",
            "is_automatic": True, "resolver_role": "finance_staff",
            "resolver_user_id": actor_id(actor),
        })
    if created:
        _audit(actor, "anomaly", anomaly.pk, "budget_insufficiency_flagged", "", "open")
        _notify(actor_id(actor), "anomaly", anomaly.pk, "anomaly_opened")
    return anomaly


@transaction.atomic
def flag_anomaly(actor, *, record_type, record_id, category, description,
                 resolver_role, resolver_user_id=None):
    require(actor, "iaa.anomaly.flag", roles={"finance_staff", "auditor"})
    if record_type == "expense":
        ExpenseRequest.objects.get(pk=record_id)
    elif record_type == "ta":
        TravelClaim.objects.get(pk=record_id)
    else:
        raise IaaConflict("Anomaly source must be an expense request or TA claim.")
    anomaly = Anomaly.objects.create(
        record_type=record_type, record_id=record_id, category=category,
        description=description, resolver_role=resolver_role,
        resolver_user_id=resolver_user_id)
    _audit(actor, "anomaly", anomaly.pk, "anomaly_flagged", "", anomaly.status)
    _notify(resolver_user_id, "anomaly", anomaly.pk, "anomaly_opened")
    return anomaly


@transaction.atomic
def create_configured_anomaly(*, rule_code, condition_met, record_type, record_id):
    """Create an anomaly for a configured condition reported by an IAA evaluator.

    The condition evaluator is intentionally injected by the caller: the
    specification defines configured material conditions but does not define
    a universal expression language for evaluating them.
    """
    if record_type == "expense":
        ExpenseRequest.objects.get(pk=record_id)
    elif record_type == "ta":
        TravelClaim.objects.get(pk=record_id)
    else:
        raise IaaConflict("Anomaly source must be an expense request or TA claim.")
    rules = _policy().parameters.get("automatic_anomaly_conditions", [])
    if not isinstance(rules, list):
        raise IaaConflict("Automatic anomaly configuration must be a list.")
    config = next((item for item in rules if isinstance(item, dict)
                   and item.get("code") == rule_code and item.get("enabled")), None)
    if config is None or not condition_met:
        return None
    if not all(config.get(key) for key in ("category", "description", "resolver_role")):
        raise IaaConflict("The configured anomaly rule is missing required routing details.")
    if config["resolver_role"] not in {"finance_staff", "auditor", "hod", "dean", "director"}:
        raise IaaConflict("The configured anomaly resolver role is not supported.")
    anomaly, created = Anomaly.objects.get_or_create(
        record_type=record_type, record_id=record_id, category=config["category"], status="open",
        defaults={
            "description": config["description"], "is_automatic": True,
            "resolver_role": config["resolver_role"],
            "resolver_user_id": config.get("resolver_user_id"),
        })
    if created:
        _audit(None, "anomaly", anomaly.pk, "automatic_anomaly_created", "", "open",
               {"rule_code": rule_code})
        _notify(anomaly.resolver_user_id, "anomaly", anomaly.pk, "anomaly_opened",
                rule_code=rule_code)
    return anomaly


@transaction.atomic
def resolve_anomaly(actor, anomaly_id, *, action, remarks, next_resolver_user_id=None,
                    next_resolver_role=None):
    require(actor, "iaa.anomaly.resolve", roles={"finance_staff", "auditor", "hod", "dean", "director"})
    anomaly = Anomaly.objects.select_for_update().get(pk=anomaly_id)
    if anomaly.resolver_user_id != actor_id(actor) or anomaly.resolver_role != active_role(actor):
        raise IaaConflict("Only the designated resolver in the assigned role may act.")
    if action not in {"resolve", "escalate"} or not remarks.strip():
        raise IaaConflict("Select resolve/escalate and provide remarks.")
    if action == "escalate" and next_resolver_user_id is None:
        raise IaaConflict("A designated next resolver is required.")
    if action == "escalate" and next_resolver_role not in {
        "finance_staff", "auditor", "hod", "dean", "director",
    }:
        raise IaaConflict("A supported next resolver role is required.")
    before = anomaly.status
    anomaly.status = transition(ANOMALY_TRANSITIONS, before, action)
    anomaly.resolution_remarks = remarks
    if action == "escalate":
        anomaly.resolver_user_id = next_resolver_user_id
        anomaly.resolver_role = next_resolver_role
    anomaly.save()
    _audit(actor, "anomaly", anomaly.pk, f"anomaly_{action}", before, anomaly.status)
    _notify(anomaly.resolver_user_id, "anomaly", anomaly.pk, f"anomaly_{action}")
    return anomaly


@transaction.atomic
def raise_observation(actor, *, record_type, record_id, finding):
    require(actor, "iaa.audit.review", roles={"auditor"})
    model = ExpenseRequest if record_type == "expense" else TravelClaim
    record = model.objects.get(pk=record_id)
    owner_id = record.creator_user_id if record_type == "expense" else record.claimant_user_id
    observation = AuditObservation.objects.create(
        record_type=record_type, record_id=record_id, auditor_user_id=actor_id(actor),
        owner_user_id=owner_id, department=record.department, finding=finding)
    _audit(actor, "observation", observation.pk, "observation_raised", "", "open")
    _notify(owner_id, "observation", observation.pk, "observation_opened")
    return observation


@transaction.atomic
def respond_observation(actor, observation_id, *, corrective_action, documents=None):
    require(actor, "iaa.observation.respond", roles={"basic_user"})
    observation = AuditObservation.objects.select_for_update().get(pk=observation_id)
    if observation.owner_user_id != actor_id(actor) or observation.status != "open":
        raise IaaConflict("Only the concerned user may respond to an open observation.")
    if not corrective_action.strip():
        raise IaaConflict("Corrective action is required.")
    if documents and not _documents_valid(actor, documents, required=False):
        raise IaaConflict("Attach only active documents owned by your account.")
    response = ObservationResponse.objects.create(
        observation=observation, responder_user_id=actor_id(actor),
        corrective_action=corrective_action, supporting_documents=documents or [])
    before = observation.status
    observation.status = transition(OBSERVATION_TRANSITIONS, before, "respond")
    observation.save(update_fields=("status", "updated_at"))
    _audit(actor, "observation", observation.pk, "observation_responded", before,
           observation.status, {"response_id": response.pk})
    _notify(observation.auditor_user_id, "observation", observation.pk, "response_received")
    return response


@transaction.atomic
def verify_observation(actor, observation_id, response_id, *, satisfactory, remarks=""):
    require(actor, "iaa.observation.verify", roles={"auditor"})
    observation = AuditObservation.objects.select_for_update().get(pk=observation_id)
    response = ObservationResponse.objects.select_for_update().get(
        pk=response_id, observation=observation, satisfactory__isnull=True)
    if observation.auditor_user_id != actor_id(actor) or observation.status != "responded":
        raise IaaConflict("Only the assigned auditor may review the current response.")
    before = observation.status
    response.auditor_user_id, response.satisfactory = actor_id(actor), bool(satisfactory)
    response.verification_remarks, response.verified_at = remarks, timezone.now()
    response.save()
    observation.status = transition(OBSERVATION_TRANSITIONS, before,
                                    "close" if satisfactory else "return")
    observation.save(update_fields=("status", "updated_at"))
    event = "observation_closed" if satisfactory else "observation_returned"
    _audit(actor, "observation", observation.pk, event, before, observation.status,
           {"response_id": response.pk, "remarks": remarks})
    _notify(observation.owner_user_id, "observation", observation.pk, event)
    return observation


@transaction.atomic
def record_financial_item(actor, record_type, record_id, *, details=None):
    require(actor, "iaa.finance.record", roles={"finance_staff"})
    model = ExpenseRequest if record_type == "expense" else TravelClaim
    record = model.objects.select_for_update().get(pk=record_id)
    allowed = {"approved"} if record_type == "expense" else {"verified", "approved"}
    if record.status not in allowed:
        raise IaaConflict("Only an approved/verified record may be internally recorded.")
    before = record.status
    table = EXPENSE_TRANSITIONS if record_type == "expense" else TA_TRANSITIONS
    record.status = transition(table, before, "record")
    record.recorded_at, record.recorded_by_user_id = timezone.now(), actor_id(actor)
    record.save()
    _audit(actor, record_type, record.pk, "internally_recorded", before, record.status,
           {"external_payment": False, **(details or {})})
    owner_id = record.creator_user_id if record_type == "expense" else record.claimant_user_id
    _notify(owner_id, record_type, record.pk, "recorded")
    return record

