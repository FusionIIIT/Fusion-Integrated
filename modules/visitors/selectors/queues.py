"""Every list view starts from a queryset built here.

Ownership is enforced by narrowing the queryset, never by fetching a row and
then checking it — so somebody else's visit is a 404, not a 403.

Ref: 03_VMS_Use_Case_Specifications_v1.3
"""
from __future__ import annotations

from django.db.models import QuerySet
from django.utils import timezone

from modules.visitors.models import (
    BlacklistEntry,
    EmergencyMuster,
    GateLog,
    MusterRollCall,
    PreAuthorization,
    VisitRequest,
    ZoneAccessLog,
    ZoneDefinition,
)


# --- Visitor queues ----------------------------------------------------------

def my_visit_requests(actor) -> QuerySet[VisitRequest]:
    """VMS-UC-011: visitor's own requests and history."""
    return (VisitRequest.objects
            .filter(registered_by=actor.user_id)
            .order_by("-created_at"))


def visitor_by_id_doc(id_number: str) -> QuerySet[VisitRequest]:
    return (VisitRequest.objects
            .filter(visitor_id_number=id_number)
            .order_by("-created_at"))


# --- Host queues -------------------------------------------------------------

def host_pending_approvals(actor) -> QuerySet[VisitRequest]:
    """VMS-UC-013: visits awaiting this host's decision."""
    return (VisitRequest.objects
            .filter(host_user_id=actor.user_id, status="pending_host")
            .order_by("expected_date"))


def host_visitor_arrivals(actor) -> QuerySet[VisitRequest]:
    """VMS-UC-015: visitors currently on site for this host."""
    return (VisitRequest.objects
            .filter(host_user_id=actor.user_id, status="on_site")
            .order_by("-checked_in_at"))


def host_pre_authorizations(actor) -> QuerySet[PreAuthorization]:
    """VMS-UC-014: host's own pre-authorizations."""
    return (PreAuthorization.objects
            .filter(user_id=actor.user_id)
            .order_by("-created_at"))


# --- Security Personnel queues -----------------------------------------------

def gate_queue(gate_name: str | None = None) -> QuerySet[VisitRequest]:
    """VMS-UC-018: visits with active passes that may arrive at the gate."""
    qs = VisitRequest.objects.filter(status="pass_active")
    if gate_name:
        qs = qs.filter(gate_logs__gate_name=gate_name).distinct()
    return qs.order_by("expected_date")


def on_site_visitors() -> QuerySet[VisitRequest]:
    """VMS-UC-022: live visitor dashboard."""
    return (VisitRequest.objects
            .filter(status="on_site")
            .order_by("-checked_in_at"))


def gate_logs_for_visit(visit_id: int) -> QuerySet[GateLog]:
    return GateLog.objects.filter(visit_id=visit_id).order_by("-created_at")


def zone_logs_for_visit(visit_id: int) -> QuerySet[ZoneAccessLog]:
    return ZoneAccessLog.objects.filter(visit_id=visit_id).order_by("-created_at")


# --- Admin queues ------------------------------------------------------------

def admin_pending_approvals() -> QuerySet[VisitRequest]:
    """VMS-UC-033/034/035: visits needing admin decision."""
    return (VisitRequest.objects
            .filter(status="pending_admin")
            .order_by("expected_date"))


def all_visits(date_from=None, date_to=None,
               status: str | None = None) -> QuerySet[VisitRequest]:
    """VMS-UC-007: admin reporting and analytics."""
    qs = VisitRequest.objects.all()
    if date_from:
        qs = qs.filter(expected_date__gte=date_from)
    if date_to:
        qs = qs.filter(expected_date__lte=date_to)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


def blacklist_entries(active_only: bool = True) -> QuerySet[BlacklistEntry]:
    """VMS-UC-006: blacklist/watchlist registry."""
    qs = BlacklistEntry.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.order_by("-created_at")


def zone_list() -> QuerySet[ZoneDefinition]:
    return ZoneDefinition.objects.filter(is_active=True).order_by("code")


# --- Emergency muster -------------------------------------------------------

def active_musters() -> QuerySet[EmergencyMuster]:
    return (EmergencyMuster.objects
            .filter(status__in=("active", "roll_call"))
            .order_by("-created_at"))


def muster_roll_call(muster_id: int) -> QuerySet[MusterRollCall]:
    """VMS-UC-027: roll-call entries for a muster."""
    return (MusterRollCall.objects
            .filter(muster_id=muster_id)
            .select_related("visit")
            .order_by("accounted", "visit__visitor_name"))
