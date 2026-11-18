"""Creation, validation, withdrawal and extension of leave requests."""
from datetime import date, timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from modules.directory import contracts as directory
from modules.elm.domain import counting, overlap, routing
from modules.elm.domain.state_machine import transition as require_transition
from modules.elm.domain.policy import check_eligible, merged_params, PolicyViolation
from modules.elm.models import CalendarVersion, LeaveAccountLock, LeaveRequest, LeaveTransition
from modules.elm.services import ledger, notifications


def _calendar(on_date: date | None = None):
    on_date = on_date or date.today()
    return CalendarVersion.objects.filter(status="published", effective_from__lte=on_date).order_by("-effective_from", "-id").first()


def _calendar_dates(calendar, kind: str, start: date, end: date) -> set[date]:
    if not calendar:
        return set()
    out = set()
    for entry in calendar.entries.filter(kind=kind, start_date__lte=end, end_date__gte=start):
        cursor = max(start, entry.start_date)
        last = min(end, entry.end_date)
        while cursor <= last:
            out.add(cursor)
            cursor += timedelta(days=1)
    return out


def validate(*, user_id: int, category: str, start_date: date, end_date: date,
             half: str = "", substitute_user_id: int | None = None,
             evidence: list | None = None, exclude_request_id: int | None = None) -> Decimal:
    if end_date < start_date:
        raise PolicyViolation("invalid_dates", "End date must not be before start date.")
    if half and category != "CL":
        raise PolicyViolation("half_day_only_cl", "Half-day selection is only valid for CL.")
    if substitute_user_id is not None and substitute_user_id <= 0:
        raise PolicyViolation("invalid_substitute", "Substitute employee ID must be positive.")
    lock_ids = sorted({user_id, *([substitute_user_id] if substitute_user_id else [])})
    for lock_id in lock_ids:
        LeaveAccountLock.objects.get_or_create(user_id=lock_id)
        LeaveAccountLock.objects.select_for_update().get(user_id=lock_id)
    user = directory.get_users([user_id]).get(user_id)
    if not user or not user.is_active or user.kind not in {"faculty", "staff"}:
        raise PolicyViolation("employee_only", "Only active institute employees may apply for leave.")
    policy = ledger.current_policy()
    check_eligible(category, user.kind, policy.params)
    calendar = _calendar(start_date)
    if not calendar:
        raise PolicyViolation("calendar_missing", "No effective published holiday/RH/vacation calendar is available.")
    closed = _calendar_dates(calendar, "closed_holiday", start_date, end_date)
    restricted = _calendar_dates(calendar, "restricted_holiday", start_date, end_date)
    vacations = [(e.start_date, e.end_date) for e in (calendar.entries.filter(kind="vacation") if calendar else [])]
    if category == "RH":
        counting.validate_rh_dates(start_date, end_date, restricted)
    if category == "VL":
        counting.validate_vacation(start_date, end_date, vacations)
    try:
        days = counting.chargeable_days(category, start_date, end_date, half=half, closed_dates=closed)
    except ValueError as exc:
        raise PolicyViolation("invalid_counting", str(exc)) from exc
    if days <= 0:
        raise PolicyViolation("zero_chargeable_days", "The selected dates contain no chargeable leave days.")
    active = LeaveRequest.objects.filter(user_id=user_id, status__in=overlap.ACTIVE_STATUSES)
    if exclude_request_id:
        active = active.exclude(pk=exclude_request_id)
    if overlap.overlaps(start_date, end_date, half, category, active):
        raise PolicyViolation("leave_overlap", "This leave overlaps another pending or approved leave request.")
    if substitute_user_id:
        if substitute_user_id == user_id:
            raise PolicyViolation("invalid_substitute", "You cannot nominate yourself as substitute.")
        sub = directory.get_users([substitute_user_id]).get(substitute_user_id)
        if not sub or not sub.is_active or sub.kind not in {"faculty", "staff"}:
            raise PolicyViolation("invalid_substitute", "Substitute must be another active institute employee.")
        sub_leave = LeaveRequest.objects.filter(user_id=substitute_user_id, status__in=overlap.ACTIVE_STATUSES, start_date__lte=end_date, end_date__gte=start_date).exists()
        if sub_leave:
            raise PolicyViolation("substitute_unavailable", "The nominated substitute has overlapping leave.")
    params = merged_params(policy.params)
    if category == "COL" and params["COL"].get("evidence_required") and not evidence:
        raise PolicyViolation("evidence_required", "Supporting medical evidence is required for this COL request.")
    ledger.ensure_annual_credits(user_id, start_date.year, kind=user.kind)
    if ledger.balance(user_id, category, start_date.year) < days:
        raise PolicyViolation("insufficient_balance", f"Insufficient {category} balance for this request.")
    return days


@transaction.atomic
def create(*, user_id: int, actor_role: str, category: str, start_date: date,
          end_date: date, purpose: str = "", half: str = "",
          substitute_user_id: int | None = None, station_leave: bool = False,
          station_leave_from: date | None = None, station_leave_to: date | None = None,
          station_leave_address: str = "", evidence: list | None = None) -> LeaveRequest:
    if station_leave:
        if not station_leave_from or not station_leave_to or station_leave_to < station_leave_from:
            raise PolicyViolation("invalid_station_leave", "Station Leave requires a valid from/to date range.")
        if station_leave_from < start_date or station_leave_to > end_date:
            raise PolicyViolation("invalid_station_leave", "Station Leave dates must fall within the leave application dates.")
        if not station_leave_address.strip():
            raise PolicyViolation("invalid_station_leave", "Station Leave requires an address or destination.")
    days = validate(user_id=user_id, category=category, start_date=start_date, end_date=end_date,
                    half=half, substitute_user_id=substitute_user_id, evidence=evidence)
    user = directory.get_users([user_id]).get(user_id)
    if not user or not user.is_active:
        raise PolicyViolation("employee_only", "Only active institute employees may apply for leave.")
    policy = ledger.current_policy()
    route = routing.resolve_route(category=category, applicant_role=actor_role,
                                  department=user.department, hierarchy=policy.hierarchy)
    needs_substitute = bool(substitute_user_id)
    first = route[0]
    status = "awaiting_substitute" if needs_substitute else ("awaiting_director" if first["kind"] == "self_sanction" else ("awaiting_unit_head" if first["kind"] == "review" else "awaiting_sanction"))
    event = "submit_with_substitute" if needs_substitute else ("director_submit" if status == "awaiting_director" else "submit")
    require_transition("", event, "director" if event == "director_submit" else "employee")
    req = LeaveRequest.objects.create(
        user_id=user_id, category=category, start_date=start_date, end_date=end_date,
        half=half, days=days, purpose=purpose, station_leave=station_leave,
        station_leave_from=station_leave_from, station_leave_to=station_leave_to,
        station_leave_address=station_leave_address, substitute_user_id=substitute_user_id,
        substitute_status="pending" if needs_substitute else "not_required", status=status,
        route=route, stage=0,
        current_role="Substitute" if needs_substitute else first["role"],
        submitted_at=timezone.now(), policy_snapshot={"params": policy.params, "hierarchy": policy.hierarchy},
        evidence=evidence or [])
    LeaveTransition.objects.create(request=req, from_status="", to_status=status, event=event, actor_user_id=user_id, actor_role=actor_role)
    if needs_substitute:
        notifications.notify(topic="substitute_request", title="Substitute response requested", body=f"Please respond to leave request #{req.pk}.", user_id=substitute_user_id, payload={"request_id": req.pk})
    else:
        notifications.notify(topic="leave_submitted", title="Leave request submitted", body=f"Leave request #{req.pk} is awaiting review.", role=first["role"], payload={"request_id": req.pk})
    return req


@transaction.atomic
def withdraw(*, request_id: int, actor_user_id: int) -> LeaveRequest:
    req = LeaveRequest.objects.select_for_update().get(pk=request_id, user_id=actor_user_id)
    if req.status not in {"awaiting_substitute", "substitute_declined", "awaiting_unit_head", "awaiting_establishment", "awaiting_sanction", "awaiting_director"}:
        raise PolicyViolation("not_withdrawable", "Only a pending leave request may be withdrawn.")
    require_transition(req.status, "withdraw", "employee")
    old = req.status
    req.status, req.current_role = "withdrawn", ""
    req.save(update_fields=["status", "current_role", "updated_at"])
    LeaveTransition.objects.create(request=req, from_status=old, to_status="withdrawn", event="withdraw", actor_user_id=actor_user_id)
    notifications.notify(topic="leave_withdrawn", title="Leave request withdrawn", body=f"Leave request #{req.pk} was withdrawn.", user_id=actor_user_id, payload={"request_id": req.pk})
    return req


@transaction.atomic
def apply_extension(*, request_id: int, actor_user_id: int, end_date: date, purpose: str = "", evidence: list | None = None) -> LeaveRequest:
    parent = LeaveRequest.objects.select_for_update().get(pk=request_id, user_id=actor_user_id, kind="leave", status="approved")
    if parent.category not in {"EL", "COL", "VL"}:
        raise PolicyViolation("extension_not_allowed", "Only ongoing EL, COL, or VL may be extended.")
    today = timezone.localdate()
    effective_end = max([parent.end_date, *parent.extensions.filter(status="approved").values_list("end_date", flat=True)])
    if not (parent.start_date <= today <= effective_end):
        raise PolicyViolation("not_ongoing", "Only an ongoing leave may be extended.")
    if end_date <= effective_end:
        raise PolicyViolation("invalid_extension", "Extension end date must be after the current leave period.")
    new_start = effective_end + timedelta(days=1)
    days = validate(user_id=actor_user_id, category=parent.category, start_date=new_start, end_date=end_date,
                    evidence=evidence, exclude_request_id=parent.pk)
    user = directory.get_users([actor_user_id]).get(actor_user_id)
    if not user or not user.is_active:
        raise PolicyViolation("employee_only", "Only active institute employees may extend leave.")
    policy = ledger.current_policy()
    route = (parent.route if parent.route and parent.route[0].get("kind") == "self_sanction"
             else routing.resolve_route(category=parent.category, applicant_role="employee", department=user.department, hierarchy=policy.hierarchy))
    initial_status = "awaiting_director" if route and route[0].get("kind") == "self_sanction" else "awaiting_unit_head"
    require_transition("", "director_extension_submit" if initial_status == "awaiting_director" else "extension_submit",
                       "director" if initial_status == "awaiting_director" else "employee")
    req = LeaveRequest.objects.create(user_id=actor_user_id, category=parent.category, kind="extension", parent=parent,
        start_date=new_start, end_date=end_date, days=days, purpose=purpose, evidence=evidence or [],
        status=initial_status, route=route, current_role=route[0]["role"], submitted_at=timezone.now(),
        policy_snapshot={"params": policy.params, "hierarchy": policy.hierarchy})
    extension_event = "director_extension_submit" if initial_status == "awaiting_director" else "extension_submit"
    LeaveTransition.objects.create(request=req, from_status="", to_status=req.status, event=extension_event, actor_user_id=actor_user_id)
    notifications.notify(topic="leave_extension_submitted", title="Leave extension submitted", body=f"Extension request #{req.pk} is awaiting review.", role=req.current_role, payload={"request_id": req.pk})
    return req
