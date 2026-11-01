"""Database query selectors for VMS."""
from typing import Optional, List
from django.db.models import QuerySet
from modules.vms.models import (
    VisitRequest,
    VisitorPass,
    VisitLog,
    BlacklistRegistry,
    Host,
    CampusGate,
)


def get_pending_requests_for_host(host_user_id: int) -> QuerySet[VisitRequest]:
    return VisitRequest.objects.filter(
        host__user_id=host_user_id,
        status="PENDING_HOST_APPROVAL",
    ).select_related("visitor", "host").order_by("scheduled_start_time")


def get_all_requests() -> QuerySet[VisitRequest]:
    return VisitRequest.objects.all().select_related("visitor", "host").order_by("-submission_timestamp")


def get_active_passes() -> QuerySet[VisitorPass]:
    return VisitorPass.objects.filter(status="ACTIVE").select_related("request__visitor", "request__host").order_by("-valid_from")


def get_active_on_site_visits() -> QuerySet[VisitLog]:
    return VisitLog.objects.filter(status="ON_SITE").select_related(
        "visitor_pass__request__visitor",
        "visitor_pass__request__host",
        "entry_gate",
    ).order_by("-check_in_time")


def check_is_blacklisted(phone: str = "", id_doc_number: str = "") -> tuple[bool, str]:
    if phone:
        match = BlacklistRegistry.objects.filter(phone=phone, is_active=True).first()
        if match:
            return True, f"Phone flagged: {match.reason}"
    if id_doc_number:
        match = BlacklistRegistry.objects.filter(id_document_number=id_doc_number, is_active=True).first()
        if match:
            return True, f"ID Document flagged: {match.reason}"
    return False, ""


def get_all_campus_gates() -> QuerySet[CampusGate]:
    return CampusGate.objects.filter(is_operational=True).order_by("gate_name")
