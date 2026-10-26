"""Record synchronisation, never a sanction (EL-UC-016/017, BR-EL-029, BR-EL-037)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.directory import contracts as directory
from modules.leave.domain import categories as cat
from modules.leave.domain import state_machine as sm
from modules.leave.domain import validation as v
from modules.leave.domain.overlap import Interval, first_collision
from modules.leave.models import LeaveRequest, LedgerEntry, RequestEvent
from modules.leave.services import accounts, applications, authz, configuration, workflow

OFFLINE_REASONS = ("illness", "connectivity", "server_unavailable", "other")


def _employee(user_id: int, actor):
    if user_id == actor.user_id:
        raise PermissionDeniedError("You cannot maintain your own leave record.",
                                    code="own_record")
    person = directory.get_users([user_id]).get(user_id)
    if person is None or person.kind not in cat.EMPLOYEE_KINDS:
        raise ConflictError("That person is not a faculty or staff member on record.",
                            code="not_an_employee")
    return person


@transaction.atomic
def record_offline(*, actor, data: dict) -> LeaveRequest:
    """Leave already sanctioned on paper: evidence, consistency, then the ledger — no workflow."""
    authz.require(actor, "leave.record.import")
    person = _employee(int(data["user_id"]), actor)
    category, start, end = data.get("category", ""), data["start_date"], data["end_date"]
    half = data.get("half", "") or ""
    reference = (data.get("sanction_reference") or "").strip()
    reason = (data.get("reason") or "").strip()
    if reason not in OFFLINE_REASONS:
        raise ConflictError("Say why ELM could not be used: illness, connectivity, "
                            "server_unavailable or other.", code="reason_required")
    if not reference:
        raise ConflictError("Enter the sanction order or reference this leave was approved "
                            "under.", code="sanction_reference_required")
    if not cat.applicable(category, person.kind):
        raise ConflictError(f"{category} is not available to {person.kind}.",
                            code="category_not_applicable")
    if end < start or start > workflow.today():
        raise ConflictError("Only leave that has already begun can be recorded "
                            "retrospectively, and it cannot end before it starts.",
                            code="invalid_period")
    if half and (not cat.get(category).half_day or start != end):
        raise ConflictError("Only single-day Casual Leave can be a half day.",
                            code="half_day_not_allowed")
    policy = configuration.current_policy()
    effective = configuration.calendar_for(start, end)
    if not effective.view.published:
        raise ConflictError(f"Publish the {start.year} holiday calendar before recording leave "
                            f"in it.", code="calendar_not_published")
    draft = v.Draft(category=category, start=start, end=end, half=half)
    ctx = v.Context(applicant_id=person.user_id, applicant_kind=person.kind,
                    today=workflow.today(), policy=policy, calendar=effective.view,
                    available=Decimal(0))
    days = v.chargeable(draft, ctx)
    accounts.lock(person.user_id, employee_kind=person.kind)
    accounts.ensure_annual_credit(user_id=person.user_id, employee_kind=person.kind,
                                  year=start.year, policy=policy)
    clash = first_collision(Interval(start, end, half),
                            applications.leave_intervals([person.user_id])[person.user_id])
    if clash is not None:
        raise ConflictError(f"This overlaps leave already on record from {clash.start} to "
                            f"{clash.end}. Correct that record first.", code="overlaps_own_leave")
    if days <= 0 or days > accounts.available(person.user_id, start.year, category):
        raise ConflictError(f"The record needs {days} day(s) of {category}, which the balance "
                            f"does not hold. Adjust the balance first if it is wrong.",
                            code="insufficient_balance")
    req = LeaveRequest.objects.create(
        user_id=person.user_id, kind=sm.NEW, category=category, start_date=start, end_date=end,
        half=half, days=days, leave_year=start.year, status=sm.APPROVED,
        purpose=(data.get("purpose") or "").strip(), applicant_kind=person.kind,
        applicant_department=person.department, source="offline",
        offline_reference=reference[:200],
        offline_reason=f"{reason}: {(data.get('reason_detail') or '').strip()}"[:300],
        recorded_by_user_id=actor.user_id, submitted_at=timezone.now())
    RequestEvent.objects.create(request=req, event="offline_recorded", to_status=sm.APPROVED,
                                actor_user_id=actor.user_id, actor_role=authz.acting_role(actor),
                                remarks=f"Sanctioned offline: {reference}"[:500])
    accounts.post(user_id=person.user_id, year=start.year, category=category, delta=-days,
                  entry_type="debit", key=f"debit:{req.pk}", request=req,
                  note=f"Offline sanction {reference}", actor_id=actor.user_id)
    return req


@transaction.atomic
def adjust(*, actor, user_id: int, year: int, category: str, delta, reference: str,
           note: str) -> LedgerEntry:
    """A correcting entry, never an edit; the reference makes a double submit harmless."""
    authz.require(actor, "leave.record.update")
    person = _employee(int(user_id), actor)
    if category not in cat.CATEGORIES:
        raise ConflictError(f"{category} is not a leave category.", code="unknown_category")
    try:
        amount = Decimal(str(delta))
    except InvalidOperation as exc:
        raise ConflictError("The adjustment must be a number of days.",
                            code="invalid_adjustment") from exc
    if not amount or amount % Decimal("0.5") or abs(amount) > 400:
        raise ConflictError("Adjust by whole or half days, and not by zero.",
                            code="invalid_adjustment")
    if not reference.strip() or not note.strip():
        raise ConflictError("Give the office reference and the reason for the correction.",
                            code="reason_required")
    accounts.lock(person.user_id, employee_kind=person.kind)
    held = accounts.balances([person.user_id], year)[person.user_id][category]
    if held + amount < 0:
        raise ConflictError(f"This would leave {category} at {held + amount} for {year}; a "
                            f"balance cannot go below zero.", code="insufficient_balance")
    entry = accounts.post(user_id=person.user_id, year=year, category=category, delta=amount,
                          entry_type="adjustment",
                          key=f"adjust:{person.user_id}:{reference.strip()[:80]}",
                          note=note.strip(), actor_id=actor.user_id)
    if entry is None:
        raise ConflictError("An adjustment with this reference has already been recorded.",
                            code="duplicate_reference")
    return entry
