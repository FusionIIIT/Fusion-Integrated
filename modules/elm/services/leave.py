from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.leave import (
    CATEGORY_LIMITS, Category, EMPLOYEE_KINDS, LeaveRuleError, Stage, employee_is_eligible,
    requests_overlap, validate_route, yearly_charges,
)
from modules.elm.models import (
    HolidayCalendar, HolidayDate, LeaveApplication, LeaveApplicationTransition,
    LeaveApprovalRoute, LeaveBalance, LeaveCharge, LeaveEmployeeState,
)

P_APPLY = "leave_elm.application.apply"
P_REVIEW = "leave_elm.application.review"
P_MANAGE = "leave_elm.policy.manage"


def _require(actor, code: str) -> None:
    if actor is None or not actor.has_permission(code):
        raise PermissionDeniedError("This action needs " + code + ".", code="permission_denied")


def _category(value: str) -> Category:
    try:
        return Category(value)
    except ValueError as exc:
        raise LeaveRuleError("Select one of CL, RH, SCL, EL, COL, or VL.") from exc


def _calendar_dates(start: date, end: date) -> tuple[set[date], set[date]]:
    calendar = HolidayCalendar.objects.filter(is_effective=True).first()
    if calendar is None:
        return set(), set()
    dates = HolidayDate.objects.filter(calendar=calendar, day__range=(start, end))
    return (
        set(dates.filter(kind=HolidayDate.Kind.CLOSED).values_list("day", flat=True)),
        set(dates.filter(kind=HolidayDate.Kind.RESTRICTED).values_list("day", flat=True)),
    )


def _release_reservations(application: LeaveApplication, *, spend: bool) -> None:
    for charge in application.charges.select_related("balance").select_for_update():
        balance = LeaveBalance.objects.select_for_update().get(pk=charge.balance_id)
        balance.reserved -= charge.days
        if spend:
            balance.used += charge.days
        balance.save(update_fields=("reserved", "used", "updated_at"))


def _lock_employee(employee_id: int) -> None:
    LeaveEmployeeState.objects.get_or_create(employee_id=employee_id)
    LeaveEmployeeState.objects.select_for_update().get(employee_id=employee_id)


@transaction.atomic
def set_balance(*, actor, employee_id: int, category: str, year: int, allotted: Decimal):
    _require(actor, P_MANAGE)
    from modules.directory.contracts import get_users

    leave_category = _category(category)
    employee = get_users([employee_id]).get(employee_id)
    if employee is None or not employee.is_active or employee.kind not in EMPLOYEE_KINDS:
        raise LeaveRuleError("Balances can only be configured for active Faculty or Staff.")
    if not employee_is_eligible(leave_category, employee.kind):
        raise LeaveRuleError("This leave category is not available to the employee kind.")
    if year < 2000 or year > 9999 or allotted < 0:
        raise LeaveRuleError("Year or entitlement is outside the supported range.")
    if allotted > CATEGORY_LIMITS[leave_category]:
        raise LeaveRuleError(f"{leave_category.value} entitlement exceeds its annual limit.")
    balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
        employee_id=employee_id, category=leave_category.value, year=year,
    )
    if allotted < balance.used + balance.reserved:
        raise ConflictError("Entitlement cannot be lower than used plus reserved leave.",
                            code="entitlement_in_use")
    balance.allotted = allotted
    balance.save(update_fields=("allotted", "updated_at"))
    return balance


@transaction.atomic
def set_route(*, actor, employee_id: int, category: str, steps: list[dict]):
    _require(actor, P_MANAGE)
    _lock_employee(employee_id)
    from modules.directory.contracts import get_users

    leave_category = _category(category)
    try:
        normalized = [(int(s["approver_user_id"]), Stage(s["stage"])) for s in steps]
        stages = [stage for _, stage in normalized]
        validate_route(leave_category, stages, director=(stages == [Stage.DIRECTOR_SELF]))
    except (KeyError, TypeError, ValueError, LeaveRuleError) as exc:
        raise LeaveRuleError(str(exc)) from exc
    if not normalized or any(user_id <= 0 for user_id, _ in normalized):
        raise LeaveRuleError("Each approval step needs a valid IAM user id.")
    people = get_users([employee_id, *(user_id for user_id, _ in normalized)])
    if (employee_id not in people or not people[employee_id].is_active
            or people[employee_id].kind not in EMPLOYEE_KINDS):
        raise LeaveRuleError("Approval routes can only be configured for an active Faculty or Staff member.")
    if any(user_id not in people or not people[user_id].is_active
           or people[user_id].kind not in EMPLOYEE_KINDS
           for user_id, _ in normalized):
        raise LeaveRuleError("Every approver must be an active Faculty or Staff member.")
    if stages == [Stage.DIRECTOR_SELF] and normalized[0][0] != employee_id:
        raise LeaveRuleError("Director self-sanction must be assigned to the applicant.")
    if any(user_id == employee_id for user_id, _ in normalized) and stages != [Stage.DIRECTOR_SELF]:
        raise LeaveRuleError("Applicants cannot be assigned as their own reviewer.")
    pending = LeaveApplication.objects.filter(
        employee_id=employee_id, category=leave_category.value,
        status=LeaveApplication.Status.PENDING,
    ).exists()
    if pending:
        raise ConflictError("An approval route cannot change while requests are pending.",
                            code="route_in_use")
    LeaveApprovalRoute.objects.filter(employee_id=employee_id,
                                      category=leave_category.value).delete()
    return [LeaveApprovalRoute.objects.create(
        employee_id=employee_id, category=leave_category.value,
        step_order=order, stage=stage.value, approver_user_id=user_id,
    ) for order, (user_id, stage) in enumerate(normalized, start=1)]


@transaction.atomic
def publish_calendar(*, actor, name: str, dates: list[dict]):
    _require(actor, P_MANAGE)
    parsed = []
    for item in dates:
        day = item["day"]
        kind = HolidayDate.Kind(item["kind"])
        label = item["name"].strip()
        if not label:
            raise LeaveRuleError("Every calendar date needs a name.")
        parsed.append((day, kind, label))
    if len({day for day, _, _ in parsed}) != len(parsed):
        raise LeaveRuleError("A calendar date can have only one holiday kind.")
    HolidayCalendar.objects.filter(is_effective=True).update(is_effective=False)
    calendar = HolidayCalendar.objects.create(
        name=name.strip(), is_effective=True, published_at=timezone.now(),
    )
    HolidayDate.objects.bulk_create([
        HolidayDate(calendar=calendar, day=day, kind=kind, name=label)
        for day, kind, label in parsed
    ])
    return calendar


@transaction.atomic
def apply_for_leave(*, actor, category: str, start_date: date, end_date: date,
                    reason: str, half_day: str = "", station_leave: bool = False,
                    station_details: str = "") -> LeaveApplication:
    _require(actor, P_APPLY)
    _lock_employee(actor.user_id)
    leave_category = _category(category)
    if getattr(actor, "kind", "").casefold() not in EMPLOYEE_KINDS:
        raise PermissionDeniedError("ELM leave applications are for Faculty and Staff.",
                                    code="employee_required")
    if not employee_is_eligible(leave_category, actor.kind):
        raise LeaveRuleError("This leave category is not available to your employee kind.")
    if station_leave and not station_details.strip():
        raise LeaveRuleError("Station Leave requires details in the same application.")
    if not station_leave and station_details.strip():
        raise LeaveRuleError("Station Leave details require Station Leave to be selected.")

    closed, restricted = _calendar_dates(start_date, end_date)
    charges_by_year = yearly_charges(leave_category, start_date, end_date,
                                     closed_dates=closed, restricted_dates=restricted,
                                     half_day=half_day)
    total = sum(charges_by_year.values(), Decimal())

    overlaps = LeaveApplication.objects.filter(
        employee_id=actor.user_id,
        status__in=(LeaveApplication.Status.PENDING, LeaveApplication.Status.APPROVED),
        start_date__lte=end_date, end_date__gte=start_date,
    )
    for other in overlaps:
        if requests_overlap(
            start=start_date, end=end_date, category=leave_category, half_day=half_day,
            other_start=other.start_date, other_end=other.end_date,
            other_category=Category(other.category), other_half_day=other.half_day,
        ):
            raise ConflictError("The requested dates overlap pending or approved leave.",
                                code="leave_overlap")

    route = list(LeaveApprovalRoute.objects.filter(
        employee_id=actor.user_id, category=leave_category.value,
    ).order_by("step_order"))
    director = any(str(role).casefold() == "director" for role in actor.roles)
    if director and (len(route) != 1 or route[0].approver_user_id != actor.user_id):
        raise ConflictError("Director self-sanction must route to the applicant.",
                            code="approval_route_invalid")
    try:
        validate_route(leave_category, [Stage(row.stage) for row in route], director=director)
    except LeaveRuleError as exc:
        raise ConflictError("A valid approval route is not configured for this employee and leave category.",
                            code="approval_route_missing") from exc

    balances = {}
    for year, days in charges_by_year.items():
        balance = (LeaveBalance.objects.select_for_update().filter(
            employee_id=actor.user_id, category=leave_category.value, year=year,
        ).first())
        if balance is None:
            raise ConflictError(f"No {leave_category.value} entitlement is configured for {year}.",
                                code="leave_balance_missing")
        if balance.allotted - balance.used - balance.reserved < days:
            raise ConflictError(f"Not enough {leave_category.value} balance for {year}.",
                                code="insufficient_leave_balance")
        balances[year] = (balance, days)

    application = LeaveApplication.objects.create(
        employee_id=actor.user_id, category=leave_category.value,
        start_date=start_date, end_date=end_date, half_day=half_day,
        chargeable_days=total, reason=reason.strip(), station_leave=station_leave,
        station_details=station_details.strip(), current_step_order=route[0].step_order,
        current_stage=route[0].stage,
    )
    for balance, days in balances.values():
        balance.reserved += days
        balance.save(update_fields=("reserved", "updated_at"))
        LeaveCharge.objects.create(application=application, balance=balance, days=days)
    LeaveApplicationTransition.objects.create(
        application=application, from_status="", to_status=application.status,
        to_stage=application.current_stage, actor_user_id=actor.user_id,
        action="submitted",
    )
    return application


@transaction.atomic
def decide(*, actor, application_id: int, approve: bool | None = None,
           recommended: bool | None = None, note: str = "") -> LeaveApplication:
    _require(actor, P_REVIEW)
    assigned = LeaveApprovalRoute.objects.filter(
        employee_id=OuterRef("employee_id"), category=OuterRef("category"),
        step_order=OuterRef("current_step_order"), stage=OuterRef("current_stage"),
        approver_user_id=actor.user_id,
    )
    application = (LeaveApplication.objects.select_for_update().annotate(
        _assigned=Exists(assigned)).filter(
        pk=application_id, status=LeaveApplication.Status.PENDING,
        _assigned=True,
    ).first())
    if application is None:
        raise NotFoundError("Pending assigned leave request not found.", code="not_found")
    step = LeaveApprovalRoute.objects.filter(
        employee_id=application.employee_id, category=application.category,
        step_order=application.current_step_order, approver_user_id=actor.user_id,
    ).first()
    if step is None or step.stage != application.current_stage:
        raise NotFoundError("Pending assigned leave request not found.", code="not_found")
    stage = Stage(step.stage)
    category = Category(application.category)
    is_director = any(str(role).casefold() == "director" for role in actor.roles)
    if actor.user_id == application.employee_id and not (
        stage == Stage.DIRECTOR_SELF and is_director
    ):
        raise PermissionDeniedError("You cannot review your own leave request.",
                                    code="self_review")
    if stage == Stage.DIRECTOR_SELF and (
        actor.user_id != application.employee_id or not is_director
    ):
        raise PermissionDeniedError("Director self-sanction is only available to the applicant.",
                                    code="self_review")

    if stage == Stage.ESTABLISHMENT:
        action = "routed"
        if approve is not None or recommended is not None:
            raise LeaveRuleError("Establishment routing records verification, not a sanction decision.")
    elif stage == Stage.UNIT_HEAD and category not in {Category.CL, Category.RH}:
        if recommended is None or approve is not None:
            raise LeaveRuleError("Unit Head must record Recommended or Not Recommended.")
        action = "recommended" if recommended else "not_recommended"
    else:
        if approve is None or recommended is not None:
            raise LeaveRuleError("A final reviewer must approve or reject the request.")
        action = "approved" if approve else "rejected"

    previous_stage = application.current_stage
    previous_status = application.status
    next_step = LeaveApprovalRoute.objects.filter(
        employee_id=application.employee_id, category=application.category,
        step_order__gt=step.step_order,
    ).order_by("step_order").first()
    final_decision = stage in {Stage.FINAL, Stage.DIRECTOR_SELF} or (
        stage == Stage.UNIT_HEAD and category in {Category.CL, Category.RH})
    rejected = final_decision and approve is False
    if rejected:
        application.status = LeaveApplication.Status.REJECTED
        application.current_stage = ""
        application.current_step_order = None
        application.decided_at = timezone.now()
        _release_reservations(application, spend=False)
    elif next_step is not None:
        application.current_step_order = next_step.step_order
        application.current_stage = next_step.stage
    else:
        if not final_decision:
            raise ConflictError("The configured route has no final sanction step.",
                                code="approval_route_incomplete")
        application.status = LeaveApplication.Status.APPROVED
        application.current_stage = ""
        application.current_step_order = None
        application.decided_at = timezone.now()
        _release_reservations(application, spend=True)
    application.save(update_fields=("status", "current_stage", "current_step_order",
                                    "decided_at", "updated_at"))
    LeaveApplicationTransition.objects.create(
        application=application, from_status=previous_status, to_status=application.status,
        from_stage=previous_stage, to_stage=application.current_stage,
        actor_user_id=actor.user_id, action=action, note=note.strip(),
    )
    return application


@transaction.atomic
def withdraw(*, actor, application_id: int) -> LeaveApplication:
    _require(actor, P_APPLY)
    application = LeaveApplication.objects.select_for_update().filter(
        pk=application_id, employee_id=actor.user_id,
        status=LeaveApplication.Status.PENDING,
    ).first()
    if application is None:
        raise NotFoundError("Pending leave request not found.", code="not_found")
    previous_stage = application.current_stage
    _release_reservations(application, spend=False)
    application.status = LeaveApplication.Status.WITHDRAWN
    application.current_stage = ""
    application.current_step_order = None
    application.save(update_fields=("status", "current_stage", "current_step_order", "updated_at"))
    LeaveApplicationTransition.objects.create(
        application=application, from_status=LeaveApplication.Status.PENDING,
        to_status=application.status, from_stage=previous_stage,
        actor_user_id=actor.user_id, action="withdrawn",
    )
    return application
