"""IAA use cases. Writes, role checks, row locks, audit, and notifications are atomic."""

import json
from dataclasses import dataclass
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction
from django.db.models import Q, Sum
from django.forms.models import model_to_dict
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.directory import contracts as directory
from modules.iaa import selectors
from modules.iaa.domain.rules import (
    AUTHORITIES,
    DECIDABLE,
    REPORTERS,
    REVIEWABLE,
    Role,
    State,
    eligible_steps,
    missing_submission,
    overdue,
)
from modules.iaa.models import (
    Anomaly,
    ApprovalRoute,
    AuditEntry,
    Budget,
    Clarification,
    Department,
    FinancialRequest,
    FinancialYear,
    Notification,
    Observation,
    Policy,
    RoleAssignment,
)


@dataclass(frozen=True)
class Context:
    user_id: int
    role: str


def context(principal, requested_role=None):
    """IAA-BR-003: roles are selected explicitly and checked against live grants."""
    roles = set(selectors.assignments(principal.user_id).values_list("role", flat=True))
    role = requested_role or (next(iter(roles)) if len(roles) == 1 else None)
    if role not in roles:
        raise PermissionDeniedError(
            "Select an assigned IAA role before continuing.", code="active_role_required"
        )
    return Context(principal.user_id, role)


def _allowed(ctx, roles):
    selectors.require_role(ctx, roles)
    if not selectors.assignments(ctx.user_id).filter(role=ctx.role).exists():
        raise PermissionDeniedError("The active IAA role has been revoked.")


def _text(value, field="remarks"):
    if not value or not value.strip():
        raise BadRequestError(f"{field} is required.", code="required_information")
    return value.strip()


def audit(ctx, action, obj, *, request=None, before="", details=None):
    """IAA-BR-502/503: historical roles and action details are immutable snapshots."""
    AuditEntry.objects.create(
        actor_id=ctx.user_id if ctx else None,
        active_role=ctx.role if ctx else "System",
        action=action,
        object_type=obj._meta.model_name,
        object_id=obj.pk,
        request=request,
        from_status=before,
        to_status=getattr(obj, "status", ""),
        details=details or {},
    )


def notify(req, recipients, event):
    """IAA-BR-504: dashboard messages are identity AND role scoped."""
    Notification.objects.bulk_create(
        [
            Notification(
                user_id=uid,
                role=str(role),
                request=req,
                event=event,
                message=f"IAA record #{req.pk}: {event.replace('_', ' ')}",
            )
            for uid, role in set(recipients)
            if uid is not None
        ]
    )


def _status(ctx, req, target, action, *, details=None):
    before = req.status
    req.status = target
    req.save()
    audit(ctx, action, req, request=req, before=before, details=details)
    recipients = [(req.creator_id, Role.BASIC)]
    if req.assignee_id:
        recipients.append((req.assignee_id, req.assignee_role))
    elif req.finance_user_id:
        recipients.append((req.finance_user_id, Role.FINANCE))
    notify(req, recipients, action)


def _request(ctx, pk, roles):
    _allowed(ctx, roles)
    req = selectors.requests_for(ctx).select_for_update().filter(pk=pk).first()
    if req is None:
        raise NotFoundError("That IAA request does not exist.")
    return req


def _state(req, states):
    if req.status not in states:
        raise ConflictError(
            "This action is not available in the current state.", code="invalid_transition"
        )


def _policy():
    policies = list(Policy.objects.filter(active=True)[:2])
    if len(policies) != 1:
        raise ConflictError("Configure exactly one active IAA policy.", code="policy_missing")
    return policies[0]


def _snapshot(policy):
    return {
        k: (str(v) if isinstance(v, Decimal) else v)
        for k, v in vars(policy).items()
        if not k.startswith("_") and k != "id"
    }


@transaction.atomic
def switch_role(principal, role):
    ctx = context(principal, role)
    assignment = selectors.assignments(ctx.user_id).filter(role=role).first()
    audit(ctx, "switch_role", assignment, details={"role": role})
    return ctx


@transaction.atomic
def create_request(ctx, data):
    """IAA-UC-101/401: expense drafts may be incomplete; TA submits atomically."""
    _allowed(ctx, {Role.BASIC})
    department = data.get("department", "")
    if department and not selectors.has_scope(ctx.user_id, ctx.role, department):
        raise PermissionDeniedError("This department is outside your assigned scope.")
    if data["kind"] == "ta":
        user = directory.get_users([ctx.user_id]).get(ctx.user_id)
        if user is None or user.kind not in ("staff", "faculty"):
            raise PermissionDeniedError("TA claims are available to employees only.")
    req = FinancialRequest.objects.create(creator_id=ctx.user_id, creator_role=ctx.role, **data)
    audit(ctx, "create_draft", req, request=req)
    if req.kind == "ta":
        return submit(ctx, req.pk)
    return req


@transaction.atomic
def edit_draft(ctx, pk, data):
    req = _request(ctx, pk, {Role.BASIC})
    _state(req, {State.DRAFT})  # IAA-BR-104
    if data.get("department") and not selectors.has_scope(
        ctx.user_id, ctx.role, data["department"]
    ):
        raise PermissionDeniedError("This department is outside your assigned scope.")
    for key, value in data.items():
        if key != "kind":
            setattr(req, key, value)
    req.save()
    audit(ctx, "edit_draft", req, request=req)
    return req


@transaction.atomic
def submit(ctx, pk):
    req = _request(ctx, pk, {Role.BASIC})
    _state(req, {State.DRAFT})
    policy = _policy()
    missing = missing_submission(req, require_documents=policy.documents_required)
    if missing:
        raise BadRequestError(
            "Complete the required submission information.",
            code="incomplete_submission",
            details=[{"field": field, "message": "Required or invalid."} for field in missing],
        )
    today = timezone.localdate()
    year = FinancialYear.objects.filter(
        active=True, starts_on__lte=today, ends_on__gte=today
    ).first()
    if year is None:
        raise ConflictError("No active financial year covers today.", code="financial_year_missing")
    req.year = year
    req.policy_snapshot = _snapshot(policy)
    dept = Department.objects.filter(code=req.department).first()
    if dept and selectors.has_scope(dept.finance_user_id, Role.FINANCE, req.department):
        req.finance_user_id = dept.finance_user_id
    else:
        req.recovery_note = (
            "Finance routing unavailable; configure department then recover routing."
        )
    req.submitted_at = timezone.now()
    _status(ctx, req, State.SUBMITTED, "submit")
    return req


@transaction.atomic
def recover_routing(ctx, pk):
    # Metadata-only administrative recovery never returns request content.
    _allowed(ctx, {Role.ADMIN})
    req = FinancialRequest.objects.select_for_update().filter(pk=pk).first()
    if req is None:
        raise NotFoundError()
    _state(req, REVIEWABLE)
    dept = Department.objects.filter(code=req.department).first()
    if not dept or not selectors.has_scope(dept.finance_user_id, Role.FINANCE, req.department):
        raise ConflictError("An eligible Finance assignee is still missing.")
    req.finance_user_id, req.recovery_note = dept.finance_user_id, ""
    req.save(update_fields=["finance_user_id", "recovery_note"])
    audit(ctx, "recover_finance_routing", req, request=req)
    notify(req, [(req.finance_user_id, Role.FINANCE)], "routing_recovered")


@transaction.atomic
def query(ctx, pk, remarks):
    req = _request(ctx, pk, {Role.FINANCE})
    _state(req, REVIEWABLE)
    Clarification.objects.create(request=req, query=_text(remarks, "query"), asked_by=ctx.user_id)
    _status(ctx, req, State.QUERY_RAISED, "query_raised", details={"query": remarks})
    return req


@transaction.atomic
def respond(ctx, pk, response, evidence):
    req = _request(ctx, pk, {Role.BASIC})
    _state(req, {State.QUERY_RAISED})
    item = req.clarifications.filter(responded_at__isnull=True).order_by("-id").first()
    if item is None:
        raise ConflictError("No clarification is awaiting a response.")
    item.response, item.evidence, item.responded_at = (
        _text(response, "response"),
        evidence,
        timezone.now(),
    )
    item.save()
    _status(
        ctx,
        req,
        State.QUERY_RESPONDED,
        "query_responded",
        details={"response": response, "evidence": evidence},
    )
    return req


def _unresolved(req):
    if req.anomalies.exclude(status="resolved").exists():
        raise ConflictError(
            "Resolve linked material anomalies before proceeding.", code="open_anomaly"
        )


def _anomaly(ctx, req, category, description, automatic=False):
    policy = _policy()
    if automatic:
        existing = req.anomalies.filter(category=category).exclude(status="resolved").first()
        if existing:
            return existing
    if not selectors.has_scope(
        policy.anomaly_resolver_id, policy.anomaly_resolver_role, req.department
    ):
        raise ConflictError("Configure an eligible anomaly resolver.")
    anomaly = Anomaly.objects.create(
        request=req,
        category=category,
        description=_text(description, "description"),
        resolver_id=policy.anomaly_resolver_id,
        resolver_role=policy.anomaly_resolver_role,
        escalation_id=policy.anomaly_escalation_id,
        escalation_role=policy.anomaly_escalation_role,
        automatic=automatic,
    )
    audit(
        None if automatic else ctx,
        "automatic_anomaly" if automatic else "flag_anomaly",
        anomaly,
        request=req,
        details={"category": category, "description": description},
    )
    notify(
        req,
        [(req.creator_id, Role.BASIC), (anomaly.resolver_id, anomaly.resolver_role)],
        "anomaly_opened",
    )
    return anomaly


@transaction.atomic
def flag_anomaly(ctx, pk, category, description):
    req = _request(ctx, pk, {Role.FINANCE, Role.AUDITOR})
    return _anomaly(ctx, req, category, description)


def _reserve(req):
    if not req.policy_snapshot["budget_required"]:
        return True
    budget = (
        Budget.objects.select_for_update().filter(department=req.department, year=req.year).first()
    )
    if budget is None:
        raise ConflictError("The applicable department budget is missing.", code="budget_missing")
    used = FinancialRequest.objects.filter(budget=budget).exclude(pk=req.pk).aggregate(
        value=Sum("reservation")
    )["value"] or Decimal(0)
    if req.amount > budget.allocated - used:
        # IAA-BR-102: do not reject; create the independent anomaly lifecycle.
        _anomaly(None, req, "budget", "Department budget is insufficient.", automatic=True)
        return False
    req.budget, req.reservation = budget, req.amount
    return True


def _route(req):
    routes = ApprovalRoute.objects.filter(active=True, kind=req.kind, minimum__lte=req.amount)
    routes = routes.filter(Q(maximum__isnull=True) | Q(maximum__gt=req.amount))
    routes = routes.filter(Q(department="") | Q(department=req.department))
    routes = routes.filter(Q(request_type="") | Q(request_type=req.request_type))
    matches = list(routes.order_by("priority", "id"))
    if not matches:
        raise ConflictError("No matching approval route is configured.", code="route_missing")
    chosen = matches[0]
    if len(matches) > 1 and matches[1].priority == chosen.priority:
        raise ConflictError(
            "Matching approval routes have ambiguous priorities.", code="route_ambiguous"
        )
    steps = eligible_steps(chosen.steps, req.creator_id)
    if not steps:
        raise ConflictError("No eligible non-creator authority remains.", code="self_routing")
    req.route_snapshot, req.route_index = steps, 0
    _assign(req, 0)


def _assign(req, index):
    step = req.route_snapshot[index]
    if step["user_id"] == req.creator_id or not selectors.has_scope(
        step["user_id"], step["role"], req.department
    ):
        raise ConflictError(
            "The configured authority is no longer eligible; update the route.",
            code="authority_unavailable",
        )
    req.route_index = index
    req.assignee_id, req.assignee_role = step["user_id"], step["role"]
    req.assigned_at = timezone.now()


@transaction.atomic
def validate_finance(ctx, pk, remarks, *, compliant=True):
    """IAA-UC-103/402: documentary/policy attestation and real budget validation."""
    req = _request(ctx, pk, {Role.FINANCE})
    _state(req, REVIEWABLE)
    _text(remarks)
    if not compliant:
        if req.kind != "ta":
            raise BadRequestError("Use a clarification or material anomaly for expense validation.")
        _status(ctx, req, State.REJECTED, "ta_policy_rejected", details={"remarks": remarks})
        return req
    _unresolved(req)
    missing = missing_submission(req, require_documents=req.policy_snapshot["documents_required"])
    if missing:
        raise ConflictError("Submitted information no longer satisfies documentary policy.")
    cap = req.policy_snapshot.get("ta_max_daily_amount")
    if (
        req.kind == "ta"
        and cap
        and req.amount > Decimal(cap) * ((req.trip_end - req.trip_start).days + 1)
    ):
        raise ConflictError(
            "TA exceeds the configured daily limit; clarify or reject.", code="ta_policy"
        )
    if not _reserve(req):
        audit(ctx, "budget_validation_failed", req, request=req, details={"remarks": remarks})
        return req
    if req.kind == "ta" and req.amount < Decimal(req.policy_snapshot["ta_approval_threshold"]):
        target = State.VERIFIED
    else:
        _route(req)
        target = State.APPROVAL_PENDING if req.kind == "ta" else State.FINANCE_VALIDATED
    _status(ctx, req, target, "finance_validated", details={"remarks": remarks})
    return req


@transaction.atomic
def decide(ctx, pk, approve, remarks):
    req = _request(ctx, pk, AUTHORITIES)
    _state(req, DECIDABLE)
    _text(remarks)  # IAA-BR-005
    if (
        req.assignee_id != ctx.user_id
        or req.assignee_role != ctx.role
        or req.creator_id == ctx.user_id
    ):
        raise PermissionDeniedError("Only the eligible assigned authority may decide.")
    _unresolved(req)
    decision_time = timezone.now()
    decision_details = {
        "remarks": remarks,
        "assigned_at": req.assigned_at.isoformat(),
        "decided_at": decision_time.isoformat(),
        "turnaround_seconds": (decision_time - req.assigned_at).total_seconds(),
    }
    target = State.REJECTED
    if approve:
        next_index = req.route_index + 1
        if next_index < len(req.route_snapshot):
            _assign(req, next_index)
            target = State.APPROVAL_PENDING
        else:
            target = State.APPROVED
            req.assignee_id, req.assignee_role, req.assigned_at = None, "", None
    else:
        req.reservation = 0
        req.assignee_id, req.assignee_role, req.assigned_at = None, "", None
    _status(ctx, req, target, "approve" if approve else "reject", details=decision_details)
    return req


@transaction.atomic
def record(ctx, pk, reference):
    """IAA-BR-006: internal recording only. No payment execution is performed."""
    req = _request(ctx, pk, {Role.FINANCE})
    _state(req, {State.APPROVED, State.VERIFIED} if req.kind == "ta" else {State.APPROVED})
    _unresolved(req)
    req.processing_reference = _text(reference, "processing reference")
    req.recorded_at = timezone.now()
    _status(
        ctx,
        req,
        State.RECORDED,
        "record_internal_completion",
        details={"reference": reference, "monetary_transfer": False},
    )
    return req


@transaction.atomic
def resolve_anomaly(ctx, pk, escalate, remarks):
    _allowed(ctx, REPORTERS)
    anomaly = Anomaly.objects.select_for_update().filter(pk=pk).first()
    if anomaly is None or not selectors.has_scope(
        ctx.user_id, ctx.role, anomaly.request.department
    ):
        raise NotFoundError()
    if anomaly.resolver_id != ctx.user_id or anomaly.resolver_role != ctx.role:
        raise PermissionDeniedError("Only the designated resolver may act.")
    if anomaly.status not in ("open", "escalated") or (escalate and anomaly.status != "open"):
        raise ConflictError("This anomaly cannot take that action.")
    before = anomaly.status
    anomaly.resolution = _text(remarks)
    if escalate:
        if not anomaly.escalation_id or not selectors.has_scope(
            anomaly.escalation_id, anomaly.escalation_role, anomaly.request.department
        ):
            raise ConflictError("No eligible next resolver is configured.")
        anomaly.resolver_id, anomaly.resolver_role = anomaly.escalation_id, anomaly.escalation_role
    anomaly.status = "escalated" if escalate else "resolved"
    anomaly.save()
    audit(
        ctx,
        "escalate_anomaly" if escalate else "resolve_anomaly",
        anomaly,
        request=anomaly.request,
        before=before,
        details={"remarks": remarks},
    )
    notify(
        anomaly.request,
        [(anomaly.resolver_id, anomaly.resolver_role), (anomaly.request.creator_id, Role.BASIC)],
        "anomaly_" + anomaly.status,
    )
    return anomaly


@transaction.atomic
def raise_observation(ctx, pk, description, respondent_id=None):
    req = _request(ctx, pk, {Role.AUDITOR})
    respondent = respondent_id or req.creator_id
    if not selectors.has_scope(respondent, Role.BASIC, req.department):
        raise BadRequestError("The respondent needs a Basic User role for this department.")
    obs = Observation.objects.create(
        request=req,
        auditor_id=ctx.user_id,
        respondent_id=respondent,
        description=_text(description, "observation"),
    )
    audit(ctx, "raise_observation", obs, request=req, details={"description": description})
    notify(req, [(respondent, Role.BASIC)], "observation_opened")
    return obs


@transaction.atomic
def respond_observation(ctx, pk, response, evidence):
    _allowed(ctx, {Role.BASIC})
    obs = selectors.observations_for(ctx).select_for_update().filter(pk=pk).first()
    if obs is None:
        raise NotFoundError()
    if obs.status != "open":
        raise ConflictError("Only an Open observation accepts a response.")
    if not evidence:
        raise BadRequestError("Supporting corrective evidence is required.")
    obs.response, obs.evidence, obs.status = (
        _text(response, "corrective action"),
        evidence,
        "responded",
    )
    obs.save()
    audit(
        ctx,
        "respond_observation",
        obs,
        request=obs.request,
        before="open",
        details={"response": response, "evidence": evidence},
    )
    notify(obs.request, [(obs.auditor_id, Role.AUDITOR)], "observation_responded")
    return obs


@transaction.atomic
def review_observation(ctx, pk, satisfactory, verification):
    _allowed(ctx, {Role.AUDITOR})
    obs = (
        selectors.observations_for(ctx)
        .select_for_update()
        .filter(pk=pk, auditor_id=ctx.user_id)
        .first()
    )
    if obs is None:
        raise NotFoundError()
    if obs.status != "responded":
        raise ConflictError("Only a Responded observation may be verified.")
    obs.verification = _text(verification, "verification")
    obs.status = "closed" if satisfactory else "open"  # IAA-BR-301/302: never Reopened
    obs.save()
    audit(
        ctx,
        "review_observation",
        obs,
        request=obs.request,
        before="responded",
        details={"verification": verification, "satisfactory": satisfactory},
    )
    notify(obs.request, [(obs.respondent_id, Role.BASIC)], "observation_" + obs.status)
    return obs


def escalate_overdue(now=None):
    """IAA-UC-203: idempotent per assignment; no automatic rejection at the top."""
    now = now or timezone.now()
    result = {"escalated": 0, "blocked": 0}
    ids = FinancialRequest.objects.filter(status__in=DECIDABLE).values_list("id", flat=True)
    for pk in list(ids):
        with transaction.atomic():
            req = FinancialRequest.objects.select_for_update().get(pk=pk)
            if req.status not in DECIDABLE or not req.route_snapshot:
                continue
            step = req.route_snapshot[req.route_index]
            if not overdue(req.assigned_at, step["timeout_hours"], now):
                continue
            following = req.route_index + 1
            while following < len(req.route_snapshot):
                candidate = req.route_snapshot[following]
                if candidate["user_id"] != req.creator_id and selectors.has_scope(
                    candidate["user_id"], candidate["role"], req.department
                ):
                    break
                following += 1
            if following >= len(req.route_snapshot):
                key = f"escalation_blocked:{req.route_index}"
                if not req.history.filter(action=key).exists():
                    audit(None, key, req, request=req)
                    notify(
                        req,
                        [(req.assignee_id, req.assignee_role), (req.finance_user_id, Role.FINANCE)],
                        "approval_overdue",
                    )
                result["blocked"] += 1
                continue
            _assign(req, following)
            req.assigned_at = now
            _status(None, req, State.ESCALATED, "approval_escalated")
            result["escalated"] += 1
    return result


CONFIG_MODELS = {
    "roles": RoleAssignment,
    "years": FinancialYear,
    "departments": Department,
    "policies": Policy,
    "routes": ApprovalRoute,
    "budgets": Budget,
}


@transaction.atomic
def configure(ctx, resource, data, pk=None):
    """IAA-UC-702..704: configuration never edits financial request contents."""
    _allowed(ctx, {Role.ADMIN})
    # One config transaction at a time, including empty-table initialization.
    with connection.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s, %s)", [8312, 0])
    model = CONFIG_MODELS[resource]
    obj = model.objects.select_for_update().filter(pk=pk).first() if pk else model()
    if obj is None:
        raise NotFoundError()
    previous_values = model_to_dict(obj) if obj.pk else None
    for key, value in data.items():
        setattr(obj, key, value)
    if resource == "roles":
        _require_person(obj.user_id)
        if (
            previous_values
            and previous_values.get("role") == Role.ADMIN
            and (obj.role != Role.ADMIN or not obj.active)
            and not RoleAssignment.objects.filter(role=Role.ADMIN, active=True)
            .exclude(pk=obj.pk)
            .exists()
        ):
            raise ConflictError("The last IAA administrator cannot be revoked.")
    elif resource == "years":
        if obj.ends_on < obj.starts_on:
            raise BadRequestError("Financial year dates are reversed.")
        if (
            obj.active
            and FinancialYear.objects.filter(
                active=True, starts_on__lte=obj.ends_on, ends_on__gte=obj.starts_on
            )
            .exclude(pk=pk)
            .exists()
        ):
            raise ConflictError("Active financial years must not overlap.")
    elif resource == "departments":
        if not selectors.has_scope(obj.finance_user_id, Role.FINANCE, obj.code):
            raise BadRequestError(
                "Assign Finance Staff to this department before configuring routing."
            )
    elif resource == "policies":
        if obj.active and Policy.objects.filter(active=True).exclude(pk=pk).exists():
            raise ConflictError("Only one policy can be active.")
        if obj.anomaly_resolver_role not in REPORTERS:
            raise BadRequestError(
                "The anomaly resolver must be Finance, an authority, or an Auditor."
            )
        _require_assignment(obj.anomaly_resolver_id, obj.anomaly_resolver_role)
        if obj.anomaly_escalation_id:
            if obj.anomaly_escalation_role not in REPORTERS:
                raise BadRequestError("Invalid escalation role.")
            _require_assignment(obj.anomaly_escalation_id, obj.anomaly_escalation_role)
        if obj.ta_max_daily_amount is not None and obj.ta_max_daily_amount <= 0:
            raise BadRequestError("TA daily limit must be positive.")
    elif resource == "routes":
        if not obj.steps:
            raise BadRequestError("At least one approval step is required.")
        ids = set()
        for step in obj.steps:
            if step["role"] not in AUTHORITIES or step["user_id"] in ids:
                raise BadRequestError("Each authority must be distinct and have an approving role.")
            ids.add(step["user_id"])
            if not selectors.has_scope(step["user_id"], step["role"], obj.department):
                # A wildcard route requires global authority assignments.
                raise BadRequestError("Approval authority lacks the required department scope.")
    elif resource == "budgets":
        if not Department.objects.filter(code=obj.department).exists():
            raise BadRequestError("Configure the department first.")
        used = (
            FinancialRequest.objects.filter(budget=obj).aggregate(total=Sum("reservation"))["total"]
            if obj.pk
            else Decimal(0)
        )
        if obj.allocated < (used or Decimal(0)):
            raise ConflictError("Allocation cannot be below committed/reserved internal budget.")
    obj.full_clean()
    obj.save()
    audit(
        ctx,
        "configure_" + resource,
        obj,
        details=json.loads(
            json.dumps(
                {"before": previous_values, "after": model_to_dict(obj)}, cls=DjangoJSONEncoder
            )
        ),
    )
    return obj


def _require_person(user_id):
    if user_id not in directory.get_users([user_id]):
        raise BadRequestError("Select an existing Fusion user.")


def _require_assignment(user_id, role):
    if not selectors.assignments(user_id).filter(role=role).exists():
        raise BadRequestError("The configured user does not hold that IAA role.")
