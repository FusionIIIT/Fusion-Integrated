"""Reads of applications, always starting from scoping (UC-PMS-002, PMS-AFR-010, 058)."""
from __future__ import annotations

from django.db.models import Prefetch, Q, QuerySet

from modules.pms.models import Application, AuditEntry, Budget
from modules.pms.selectors import scoping

DETAIL_PREFETCH = (
    "inventors", "review_cycles", "appeals", "attorney_assignments", "filings",
    "communications", "maintenance_cycles", "assessments", "legal_requests", "legal_advice",
    "revision_responses", "office_actions__extensions", "office_actions__communication",
    Prefetch("budgets", queryset=Budget.objects.order_by("-id")),
)


def list_for(actor, *, status: str | None = None, domain_code: str | None = None,
             q: str | None = None) -> QuerySet[Application]:
    qs = scoping.applications_for(actor)
    if status:
        qs = qs.filter(status=status)
    if domain_code:
        qs = qs.filter(domain_code=domain_code)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(reference__icontains=q))
    return qs.order_by("-updated_at", "-id")


def detail(actor, pk: int) -> Application | None:
    return (scoping.applications_for(actor).prefetch_related(*DETAIL_PREFETCH)
            .filter(pk=pk).first())


def history(application: Application) -> QuerySet[AuditEntry]:
    """PMS-AFR-047: the application's own trail, oldest first."""
    return AuditEntry.objects.filter(application=application).order_by("at", "id")


def feedback_keys(application: Application) -> tuple[str, ...]:
    """BR-PMS-036 / ruling C12: the feedback a resubmission has to answer."""
    keys = ["review"] if application.review_cycles.filter(status="decided").exists() else []
    appeal = application.appeals.filter(status="decided").order_by("-decided_at").first()
    latest = application.review_cycles.filter(status="decided").order_by("-decided_at").first()
    if appeal and appeal.outcome_note and (latest is None
                                           or appeal.decided_at > latest.decided_at):
        keys.append("appeal")
    return tuple(keys)


def feedback_texts(application: Application) -> dict[str, str]:
    out = {}
    latest = application.review_cycles.filter(status="decided").order_by("-decided_at").first()
    if latest:
        out["review"] = latest.justification
    appeal = application.appeals.filter(status="decided").order_by("-decided_at").first()
    if appeal and appeal.outcome_note:
        out["appeal"] = appeal.outcome_note
    return out
