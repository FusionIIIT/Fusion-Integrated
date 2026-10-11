"""Leave applications: creation, validation, submission
(EL-UC-001).

Validation is the BR set the specification makes *encoded*:
category applicability, entitlement and balance, counting and
calendar conditions, overlap, and substitute eligibility.
SCL admissibility is deliberately **not** encoded — the
problem statement reserves that judgement for the Sanctioning
Authority (PS §3), so nothing here pre-vets an SCL request
beyond the balance check.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.elm.domain.errors import (
    CalendarViolation,
    InsufficientBalance,
    OverlappingLeave,
    SubstituteIneligible,
)
from modules.elm.domain.leave_types import (
    CL,
    COL,
    HALF_FULL,
    KIND_FACULTY,
    KIND_NEW,
    RH,
    VL,
)
from modules.elm.domain.policy import (
    LeaveInterval,
    count_days,
    intervals_overlap,
)
from modules.elm.domain.routing import ApplicantContext, HierarchyProfile, Route, resolve_route
from modules.elm.models import (
    LeaveRecord,
    LeaveRequest,
    SubstituteNomination,
    VacationPeriod,
)
from modules.elm.selectors.requests import closed_dates
from modules.elm.services import authz, workflow
from modules.elm.services import policy as policy_service

log = logging.getLogger("fusion.elm.applications")

ZERO = Decimal("0")


def _translate(exc: Exception) -> Exception:
    """Domain errors carry no HTTP shape; the API envelope
    does. One translation point, so nothing below this layer
    imports DRF."""
    if isinstance(exc, InsufficientBalance):
        return ConflictError(str(exc), code=exc.code)
    if isinstance(exc, OverlappingLeave):
        return ConflictError(str(exc), code=exc.code)
    if isinstance(exc, CalendarViolation):
        return ConflictError(str(exc), code=exc.code)
    if isinstance(exc, SubstituteIneligible):
        return ConflictError(str(exc), code=exc.code)
    return exc


def create_draft(principal, *, category: str, **fields) -> LeaveRequest:
    """A draft application — not yet validated, not yet
    consuming any balance."""
    authz.require_permission(principal, "elm.leave.apply")
    return LeaveRequest.objects.create(
        user_id=principal.user_id, kind=KIND_NEW,
        category=category, status="draft", **fields)


def submit(request: LeaveRequest, principal, *,
             substitute_user_id: int | None = None,
             substitute_required: bool = False,
             reason: str = "") -> LeaveRequest:
    """Validate and submit a draft application.

    The request must belong to the caller and still be a
    draft; every business rule is checked before the first
    state change, so a rejected submission leaves no trace.
    """
    authz.require_permission(principal, "elm.leave.apply")
    if principal.user_id != request.user_id:
        raise PermissionDeniedError(
            "Only the applicant may submit this request.",
            code="not_actor")
    if request.status != "draft":
        raise ConflictError(
            "Only a draft application can be submitted.",
            code="invalid_transition")

    try:
        _validate_submission(request)
    except Exception as exc:
        raise _translate(exc) from exc

    request.substitute_required = substitute_required
    if substitute_required:
        if substitute_user_id is None:
            raise ConflictError(
                "Responsibility coverage is required: nominate "
                "a substitute.", code="substitute_required")
        _validate_nominee(request, substitute_user_id)
        SubstituteNomination.objects.create(
            request=request, nominee_user_id=substitute_user_id)

    request.days = _counted_days(request)
    request.leave_year = policy_service.leave_year_for(
        request.start_date)
    request.route = _resolve_route_dict(request)
    request.save()

    if substitute_required:
        guard = "submit_substitute_required"
    elif _is_director_request(request):
        guard = "submit_no_substitute_director"
    else:
        guard = "submit_no_substitute_not_director"

    return workflow.apply_transition(
        request, actor="employee", guard=guard,
        outcome="submitted", reason=reason, principal=principal)


# -- validation ------------------------------------------------------------


def _validate_submission(request: LeaveRequest) -> None:
    profile = authz.employee_profile(request.user_id)
    if profile is None:
        raise ConflictError(
            "Your employee profile is not set up in ELM yet.",
            code="no_employee_profile")

    if request.end_date < request.start_date:
        raise ConflictError(
            "The leave period ends before it starts.",
            code="invalid_period")

    category = request.category

    # BR-EL-006: VL is faculty-only and vacation-bound.
    if category == VL:
        if profile.employee_kind != KIND_FACULTY:
            raise CalendarViolation(
                "Vacation Leave applies to faculty only.")
        if not VacationPeriod.objects.filter(
                start_date__lte=request.start_date,
                end_date__gte=request.end_date).exists():
            raise CalendarViolation(
                "Vacation Leave is applicable only during a "
                "published Academic Calendar vacation period.")

    # BR-EL-010: half days exist only for CL.
    if category != CL and (request.start_half != HALF_FULL
                             or request.end_half != HALF_FULL):
        raise CalendarViolation(
            "Half-day leave is supported for Casual Leave only.")

    interval = LeaveInterval(
        category=category, start=request.start_date,
        end=request.end_date, start_half=request.start_half,
        end_half=request.end_half)
    days = count_days(interval, closed=closed_dates(),
                        restricted_holidays=_rh_dates())
    if days <= ZERO:
        raise CalendarViolation(
            "The requested period contains no countable leave "
            "days.")

    # BR-EL-003: an RH request must correspond to Restricted
    # Holidays in the currently effective published calendar.
    if category == RH:
        requested = _every_date(request.start_date,
                                  request.end_date)
        if not requested <= _rh_dates():
            raise CalendarViolation(
                "Restricted Holiday leave must correspond to "
                "Restricted Holidays in the currently effective "
                "published calendar.")

    # Entitlement and balance (BR-EL-002/004/005/008/009).
    balance = None
    from modules.elm.selectors import balances as balance_selector

    balance = balance_selector.balance_for(
        request.user_id, request.leave_year or
        policy_service.leave_year_for(request.start_date),
        category)
    if balance is None:
        available = policy_service.entitlement_for(
            category, profile.employee_kind)
    else:
        available = balance.available_days
    if available < days:
        raise InsufficientBalance(category, available, days)

    # BR-EL-013: no overlapping pending or approved leave,
    # with the CL half-day exception built into the overlap
    # rule itself.
    _validate_no_overlap(request, interval)
    if request.station_leave:
        details = request.station_details or {}
        if not (details.get("destination")
                and details.get("from") and details.get("to")):
            raise ConflictError(
                "Station Leave requires a destination and "
                "travel dates in the application.",
                code="station_details_required")

    # PS §3: COL may require medical evidence.
    if (category == COL
            and policy_service.current_policy()
            .medical_evidence_required
            and not (request.evidence or {}).get("medical")):
        raise ConflictError(
            "Commuted Leave requires a medical evidence "
            "reference.", code="medical_evidence_required")

    # SCL admissibility (PS §3): no encoded rule — the
    # Sanctioning Authority decides. Nothing to check.


def _validate_no_overlap(request: LeaveRequest,
                           interval: LeaveInterval) -> None:
    own_pending = LeaveRequest.objects.filter(
        user_id=request.user_id).exclude(
            id=request.id).exclude(status__in=(
                "approved", "rejected", "withdrawn"))
    for other in own_pending:
        other_interval = LeaveInterval(
            category=other.category, start=other.start_date,
            end=other.end_date, start_half=other.start_half,
            end_half=other.end_half)
        if intervals_overlap(interval, other_interval):
            raise OverlappingLeave(
                f"Overlaps your pending {other.category} "
                f"request ({other.start_date} → {other.end_date}).")
    own_records = LeaveRecord.objects.filter(
        user_id=request.user_id, status="ongoing")
    for record in own_records:
        record_interval = LeaveInterval(
            category=record.category, start=record.start_date,
            end=record.end_date, start_half=record.start_half,
            end_half=record.end_half)
        if intervals_overlap(interval, record_interval):
            raise OverlappingLeave(
                f"Overlaps your approved {record.category} "
                f"leave ({record.start_date} → {record.end_date}).")

    # PS §2: Station Leave details, inside the same
    # application.
    if request.station_leave:
        details = request.station_details or {}
        if not (details.get("destination")
                and details.get("from") and details.get("to")):
            raise ConflictError(
                "Station Leave requires a destination and "
                "travel dates in the application.",
                code="station_details_required")


def _validate_nominee(request: LeaveRequest,
                        nominee_user_id: int) -> None:
    """BR-EL-014: the substitute is another employee, not the
    applicant, with no overlapping pending or approved leave
    during the responsibility period."""
    if nominee_user_id == request.user_id:
        raise SubstituteIneligible(
            "You cannot substitute for yourself.")
    profile = authz.employee_profile(nominee_user_id)
    if profile is None:
        raise SubstituteIneligible(
            "The nominee is not an active employee.")
    interval = LeaveInterval(
        category=request.category, start=request.start_date,
        end=request.end_date, start_half=request.start_half,
        end_half=request.end_half)
    for other in LeaveRequest.objects.filter(
            user_id=nominee_user_id).exclude(
                status__in=("approved", "rejected", "withdrawn")):
        other_interval = LeaveInterval(
            category=other.category, start=other.start_date,
            end=other.end_date, start_half=other.start_half,
            end_half=other.end_half)
        if intervals_overlap(interval, other_interval):
            raise SubstituteIneligible(
                f"The nominee has overlapping pending "
                f"{other.category} leave.")
    from modules.elm.models import LeaveRecord

    for record in LeaveRecord.objects.filter(
            user_id=nominee_user_id, status="ongoing"):
        record_interval = LeaveInterval(
            category=record.category, start=record.start_date,
            end=record.end_date, start_half=record.start_half,
            end_half=record.end_half)
        if intervals_overlap(interval, record_interval):
            raise SubstituteIneligible(
                f"The nominee has overlapping approved "
                f"{record.category} leave.")


# -- counting and routing helpers --------------------------------------------


def _counted_days(request: LeaveRequest) -> Decimal:
    interval = LeaveInterval(
        category=request.category, start=request.start_date,
        end=request.end_date, start_half=request.start_half,
        end_half=request.end_half)
    return count_days(interval, closed=closed_dates(),
                        restricted_holidays=_rh_dates())


def _rh_dates() -> frozenset:
    """Restricted Holiday dates in the effective calendar."""
    calendar = None
    from modules.elm.selectors import requests as request_selectors

    calendar = request_selectors.effective_calendar()
    if calendar is None:
        return frozenset()
    return frozenset(
        calendar.holidays.filter(
            kind="restricted_holiday").values_list(
                "date", flat=True))


def _every_date(start, end) -> frozenset:
    days = set()
    current = start
    while current <= end:
        days.add(current)
        current += timedelta(days=1)
    return frozenset(days)


def _is_director_request(request: LeaveRequest) -> bool:
    profile = authz.employee_profile(request.user_id)
    if profile is None:
        return False
    return profile.designation_name in (
        policy_service.director_designations())


def _resolve_route_dict(request: LeaveRequest) -> list[dict]:
    """Resolve and snapshot the sanctioning path."""
    profile = authz.employee_profile(request.user_id)
    unit = None
    if profile is not None and profile.unit_code_id:
        from modules.elm.models import OrgUnit

        unit = OrgUnit.objects.filter(
            code=profile.unit_code_id).first()
    hierarchy = _hierarchy_for(request.category, unit)
    applicant = ApplicantContext(
        user_id=request.user_id,
        employee_kind=profile.employee_kind if profile
        else "staff",
        designation_name=profile.designation_name if profile
        else "",
        unit_code=profile.unit_code_id if profile else "",
    )
    route: Route = resolve_route(applicant, request.category,
                                   hierarchy)
    return [{"role": step.role, "decision": step.decision,
             "authority": step.authority}
            for step in route.steps]


def _hierarchy_for(category: str,
                     unit) -> HierarchyProfile:
    """The configured hierarchy for this category group and
    unit type, with safe defaults when nothing is configured
    yet."""
    from modules.elm.models import HierarchyConfig

    group = ("cl_rh" if category in ("CL", "RH")
             else "higher_sanction")
    unit_type = unit.unit_type if unit is not None else "department"
    row = HierarchyConfig.objects.filter(
        category_group=group, unit_type=unit_type).first()
    if row is not None:
        return HierarchyProfile(
            establishment_required=row.establishment_required,
            establishment_designations=tuple(
                policy_service.establishment_designations()),
            sanctioning_authority=row.sanctioning_authority,
            director_designations=tuple(
                policy_service.director_designations()),
        )
    return HierarchyProfile(
        establishment_required=(group == "higher_sanction"),
        establishment_designations=tuple(
            policy_service.establishment_designations()),
        sanctioning_authority="Dean",
        director_designations=tuple(
            policy_service.director_designations()),
    )
