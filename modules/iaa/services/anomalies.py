"""Anomaly flagging and resolution (UC-302/303/304, BR-103)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.iaa.domain import roles
from modules.iaa.domain import state_machine as sm
from modules.iaa.domain.policy import ANOMALY_CATEGORIES, Policy
from modules.iaa.models import Anomaly, FinancialRecord
from modules.iaa.selectors import scoping
from modules.iaa.services import notify, trail
from modules.iaa.services.authz import require, role_of
from modules.iaa.services.common import current_policy, domain_errors, lock, now

P_CREATE = "iaa.anomaly.create"
P_REVIEW = "iaa.anomaly.review"
ANOMALY_NOT_FOUND = "That anomaly does not exist, or is not assigned to your role."


def _open(record: FinancialRecord | None, category: str, source: str, description: str,
          policy: Policy, actor=None) -> Anomaly:
    chain = list(policy.anomaly_resolvers[category])
    anomaly = Anomaly.objects.create(
        record=record, category=category, source=source, description=description,
        resolver_chain=chain, resolver_level=0, assigned_role=chain[0],
        raised_by=getattr(actor, "user_id", None),
        raised_role=role_of(actor) if actor is not None else trail.SYSTEM_ROLE)
    trail.log("anomaly", anomaly.pk, "flag" if actor else "auto_flag", actor=actor,
              to=sm.ANOMALY_OPEN, remarks=description)
    notify.to_role(chain[0], "anomaly",
                   f"Anomaly #{anomaly.pk} ({category}) needs your review.", "anomaly", anomaly.pk)
    if record is not None:
        trail.log("record", record.pk, "anomaly_flagged", actor=actor, frm=record.status,
                  to=record.status, remarks=f"Anomaly #{anomaly.pk}: {description}")
    return anomaly


@transaction.atomic
def flag(actor, *, category: str, description: str, record_id: int | None = None) -> Anomaly:
    require(actor, P_CREATE)
    if roles.actor_kind(role_of(actor)) not in (roles.FINANCE_ACTOR, roles.AUDITOR_ACTOR):
        raise ConflictError("Only Finance Staff or an Auditor may flag an anomaly.",
                            code="actor_not_allowed")
    if category not in ANOMALY_CATEGORIES:
        raise DomainError(f"Choose a category: {', '.join(ANOMALY_CATEGORIES)}.",
                          code="invalid_category")
    if not description.strip():
        raise DomainError("Describe what is anomalous.", code="description_required")
    record = None
    if record_id is not None:
        record = scoping.records_for(actor).filter(pk=record_id).first()
        if record is None:
            raise NotFoundError("That request or claim is not visible to your role.")
    return _open(record, category, Anomaly.MANUAL, description, current_policy(), actor)


def raise_automatic(record: FinancialRecord, category: str, description: str,
                    policy: Policy) -> Anomaly:
    existing = Anomaly.objects.filter(record=record, category=category, source=Anomaly.AUTOMATIC
                                      ).exclude(status=sm.ANOMALY_RESOLVED).first()
    if existing is not None:
        return existing
    return _open(record, category, Anomaly.AUTOMATIC, description, policy)


def _assigned(actor, pk: int) -> Anomaly:
    require(actor, P_REVIEW)
    anomaly = lock(scoping.anomalies_for(actor), pk, ANOMALY_NOT_FOUND)
    if anomaly.status == sm.ANOMALY_RESOLVED:
        raise ConflictError("This anomaly is already resolved.", code="invalid_transition")
    if anomaly.assigned_role != role_of(actor):
        raise ConflictError(
            f"This anomaly is with {anomaly.assigned_role}, not your active role.",
            code="not_assigned")
    return anomaly


@transaction.atomic
def resolve(actor, pk: int, *, resolution: str) -> Anomaly:
    if not resolution.strip():
        raise DomainError("Explain how the anomaly was resolved.", code="resolution_required")
    anomaly = _assigned(actor, pk)
    with domain_errors():
        t = sm.resolve_anomaly(anomaly.status, sm.RESOLVE)
    anomaly.status, anomaly.resolution = t.to, resolution
    anomaly.resolved_by, anomaly.resolved_role, anomaly.resolved_at = (
        actor.user_id, role_of(actor), now())
    anomaly.save()
    trail.log("anomaly", anomaly.pk, "resolve", actor=actor, frm=t.frm, to=t.to,
              remarks=resolution)
    notify.to_user(anomaly.raised_by, "anomaly_resolved", f"Anomaly #{anomaly.pk} was resolved.",
                   "anomaly", anomaly.pk)
    return anomaly


@transaction.atomic
def escalate(actor, pk: int, *, remarks: str) -> Anomaly:
    if not remarks.strip():
        raise DomainError("Say why this needs escalation.", code="remarks_required")
    anomaly = _assigned(actor, pk)
    with domain_errors():
        t = sm.resolve_anomaly(anomaly.status, sm.ESCALATE)
    nxt = anomaly.resolver_level + 1
    if nxt >= len(anomaly.resolver_chain):
        raise ConflictError(
            "No further resolver is configured for this category, so resolve it here.",
            code="no_further_resolver")
    anomaly.status, anomaly.resolver_level = t.to, nxt
    anomaly.assigned_role = anomaly.resolver_chain[nxt]
    anomaly.save()
    trail.log("anomaly", anomaly.pk, "escalate", actor=actor, frm=t.frm, to=t.to,
              remarks=remarks)
    notify.to_role(anomaly.assigned_role, "anomaly_escalated",
                   f"Anomaly #{anomaly.pk} was escalated to you.", "anomaly", anomaly.pk)
    return anomaly
