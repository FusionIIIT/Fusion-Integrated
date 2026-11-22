"""The dashboard: recent notifications and what is waiting on the active role (UC-604)."""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from modules.iaa.domain import roles
from modules.iaa.domain import state_machine as sm
from modules.iaa.models import AuditObservation
from modules.iaa.selectors import policy as policy_selectors
from modules.iaa.selectors import scoping

RECENT = 50


def recent(actor) -> list:
    return list(scoping.notifications_for(actor).order_by("-created_at", "-id")[:RECENT])


def pending_actions(actor) -> dict[str, int]:
    role = getattr(actor, "active_role", None)
    kind = roles.actor_kind(role)
    records = scoping.records_for(actor)
    if kind == roles.FINANCE_ACTOR:
        return {
            "to_review": records.filter(status__in=[sm.SUBMITTED, sm.QUERY_RESPONDED]).count(),
            "to_record": records.filter(status__in=[sm.APPROVED, sm.VERIFIED]).count(),
            "anomalies": scoping.anomalies_for(actor).filter(assigned_role=role)
            .exclude(status=sm.ANOMALY_RESOLVED).count(),
        }
    if kind == roles.APPROVER_ACTOR:
        steps = scoping.pending_steps_for(actor)
        version = policy_selectors.current_version()
        overdue = 0
        if version is not None:
            cutoff = timezone.now() - timedelta(hours=version.approval_timeout_hours)
            overdue = steps.filter(assigned_at__lt=cutoff).count()
        return {"to_decide": steps.count(), "overdue": overdue,
                "anomalies": scoping.anomalies_for(actor).filter(assigned_role=role)
                .exclude(status=sm.ANOMALY_RESOLVED).count()}
    if kind == roles.AUDITOR_ACTOR:
        return {"to_verify": AuditObservation.objects.filter(status=sm.OBS_RESPONDED).count(),
                "anomalies": scoping.anomalies_for(actor).filter(assigned_role=role)
                .exclude(status=sm.ANOMALY_RESOLVED).count()}
    if kind == roles.ADMIN_ACTOR:
        return {}
    return {
        "queries_to_answer": records.filter(status=sm.QUERY_RAISED).count(),
        "drafts": records.filter(status=sm.DRAFT).count(),
        "observations_to_answer": scoping.observations_for(actor)
        .filter(status=sm.OBS_OPEN).count(),
    }
