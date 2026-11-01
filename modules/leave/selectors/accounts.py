"""Balances, held days and booked dates, all derived from append-only rows."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db.models import Max, Sum

from modules.leave.domain.categories import Category
from modules.leave.domain.counting import Half, Interval
from modules.leave.domain.workflow import HOLDS_DATES, PENDING, State
from modules.leave.models import LeaveRequest, LedgerEntry


def balances(user_id: int, year: int) -> dict[Category, Decimal]:
    rows = (LedgerEntry.objects.filter(user_id=user_id, year=year)
            .values("category").annotate(total=Sum("days")))
    out = {c: Decimal(0) for c in Category}
    for r in rows:
        out[Category(r["category"])] = r["total"] or Decimal(0)
    return out


def held(user_id: int, year: int) -> dict[Category, Decimal]:
    """Days in pending requests, reserved so two requests cannot spend one balance."""
    rows = (LeaveRequest.objects
            .filter(user_id=user_id, start_date__year=year, status__in=PENDING,
                    kind__in=(LeaveRequest.NEW, LeaveRequest.EXTENSION))
            .values("category").annotate(total=Sum("days")))
    out = {c: Decimal(0) for c in Category}
    for r in rows:
        out[Category(r["category"])] = r["total"] or Decimal(0)
    return out


def booked_intervals(user_ids, exclude_ids=()) -> list[tuple[int, Interval]]:
    """BR-EL-012/014: pending or approved leave, minus anything already cancelled."""
    rows = (LeaveRequest.objects
            .filter(user_id__in=list(user_ids), status__in=HOLDS_DATES,
                    kind__in=(LeaveRequest.NEW, LeaveRequest.EXTENSION))
            .exclude(id__in=list(exclude_ids))
            .values_list("user_id", "start_date", "end_date", "half"))
    return [(uid, Interval(s, e, Half(h))) for uid, s, e, h in rows]


def effective_end(leave: LeaveRequest) -> date:
    """The base end, pushed out by any approved extension (BR-EL-025)."""
    ext = (leave.children.filter(kind=LeaveRequest.EXTENSION, status=State.APPROVED)
           .aggregate(m=Max("end_date"))["m"])
    return max(leave.end_date, ext) if ext else leave.end_date
