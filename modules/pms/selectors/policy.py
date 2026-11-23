"""The settings version in effect; built-in defaults until PCC_ADMIN publishes one."""
from __future__ import annotations

from datetime import datetime

from django.db.models import QuerySet
from django.utils import timezone

from modules.pms.domain import policy as pol
from modules.pms.models import PmsPolicy


def current(now: datetime | None = None) -> pol.PolicySpec:
    row = (PmsPolicy.objects.filter(effective_from__lte=now or timezone.now())
           .order_by("-effective_from", "-version").first())
    return pol.parse(row.payload, version=row.version) if row else pol.DEFAULTS


def latest_version() -> int:
    row = PmsPolicy.objects.order_by("-version").values_list("version", flat=True).first()
    return row or 0


def history() -> QuerySet[PmsPolicy]:
    return PmsPolicy.objects.order_by("-version")
