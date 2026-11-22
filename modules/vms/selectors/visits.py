"""VMS Read Selectors and Queries."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from modules.vms.models.access import GateAlert
from modules.vms.models.visits import Visit
from modules.vms.selectors.scoping import get_visible_visits_for_principal


def get_visit_by_id(visit_id: int, principal: Any) -> Visit | None:
    qs = get_visible_visits_for_principal(principal)
    return qs.filter(id=visit_id).first()


def get_visit_by_qr_hash(qr_code_hash: str) -> Visit | None:
    return Visit.objects.select_related("visitor").filter(qr_code_hash=qr_code_hash).first()


def get_visit_by_pass_number(pass_number: str) -> Visit | None:
    return Visit.objects.select_related("visitor").filter(pass_number=pass_number).first()


def list_active_onsite_visits() -> QuerySet[Visit]:
    return (
        Visit.objects.select_related("visitor").filter(status="on_site").order_by("check_in_time")
    )


def list_pending_approvals_for_host(host_user_id: int) -> QuerySet[Visit]:
    return Visit.objects.select_related("visitor").filter(
        host_user_id=host_user_id, status="requested"
    )


def list_open_alerts() -> QuerySet[GateAlert]:
    return GateAlert.objects.filter(status="open").order_by("-created_at")
