"""Roster members as assignment candidates, each with their current workload."""
from __future__ import annotations

from django.db.models import Count

from modules.pms.domain import state_machine as sm
from modules.pms.domain.assignment import Candidate
from modules.pms.models import AttorneyAssignment, DirectorProfile, PanelAttorney, ReviewCycle


def director_workloads() -> dict[int, int]:
    """BR-PMS-024: open review cycles per Director, in one query."""
    rows = (ReviewCycle.objects.filter(status="open").values("director_user_id")
            .annotate(n=Count("id")))
    return {r["director_user_id"]: r["n"] for r in rows}


def attorney_workloads() -> dict[int, int]:
    """BR-PMS-043: live assignments per attorney, in one query."""
    rows = (AttorneyAssignment.objects.filter(status__in=sorted(sm.LIVE_ASSIGNMENT))
            .values("attorney_user_id").annotate(n=Count("id")))
    return {r["attorney_user_id"]: r["n"] for r in rows}


def director_candidates() -> list[Candidate]:
    loads = director_workloads()
    return [Candidate(p.user_id, frozenset(p.domain_codes), loads.get(p.user_id, 0))
            for p in DirectorProfile.objects.filter(valid_to__isnull=True)]


def attorney_candidates() -> list[Candidate]:
    loads = attorney_workloads()
    return [Candidate(p.user_id, frozenset(p.domain_codes), loads.get(p.user_id, 0))
            for p in PanelAttorney.objects.filter(valid_to__isnull=True)]


def active_directors():
    return DirectorProfile.objects.filter(valid_to__isnull=True).order_by("user_id")


def active_panel():
    return PanelAttorney.objects.filter(valid_to__isnull=True).order_by("user_id")


def is_active_director(user_id: int) -> bool:
    return DirectorProfile.objects.filter(user_id=user_id, valid_to__isnull=True).exists()
