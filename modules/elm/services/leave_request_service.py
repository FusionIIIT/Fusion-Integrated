"""Transactional ELM request creation and policy validation."""
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from fusion_auth.client import IamUnavailable
from modules.directory.contracts import get_users
from modules.elm.domain.policy import (
    LeaveInterval,
    LeavePolicyError,
    intervals_overlap,
    require_sufficient_balance,
)
from modules.elm.models import (
    LeaveApprovalTask,
    LeaveAuthorityRule,
    LeaveBalance,
    LeaveBalanceEvent,
    LeaveCalendar,
    LeavePolicy,
    LeaveRequest,
    LeaveRequestEvent,
)

ACTIVE_STATUSES = (
    "SUBMITTED",
    "PENDING_SUBSTITUTE",
    "PENDING_SUBSTITUTE_REPLACEMENT",
    "PENDING_UNIT_HEAD",
    "PENDING_ESTABLISHMENT",
    "PENDING_SANCTION",
    "APPROVED",
)


def _active_calendar(kind, day):
    query = LeaveCalendar.objects.filter(
        kind=kind,
        year=day.year,
        status="PUBLISHED",
        effective_from__lte=day,
    ).filter(
        Q(effective_through__isnull=True)
        | Q(effective_through__gte=day)
    )
    calendar = query.order_by("-effective_from", "-revision").first()
    if calendar is None:
        raise LeavePolicyError(
            f"No effective published {kind.lower()} calendar covers {day}."
        )
    return calendar


def _date_range(start, end):
    for offset in range((end - start).days + 1):
        yield start + timedelta(days=offset)


def _chargeable_days(policy, start, end, day_part):
    if policy.day_counting == "CALENDAR_DAYS":
        if day_part != "FULL":
            raise LeavePolicyError("This leave policy does not permit half-days.")
        return Decimal((end - start).days + 1)

    if policy.day_counting == "RH_DATE":
        if start != end or day_part != "FULL":
            raise LeavePolicyError("An RH request must be for one full day.")
        calendar = _active_calendar("RH", start)
        if not calendar.dates.filter(day=start).exists():
            raise LeavePolicyError(
                "The requested date is not in the effective published RH calendar."
            )
        return Decimal("1")

    if policy.day_counting == "VACATION_DAYS":
        if day_part != "FULL":
            raise LeavePolicyError("Vacation leave does not permit half-days.")
        for day in _date_range(start, end):
            calendar = _active_calendar("VACATION", day)
            if not calendar.dates.filter(day=day).exists():
                raise LeavePolicyError(
                    f"{day} is outside the effective published vacation calendar."
                )
        return Decimal((end - start).days + 1)

    if policy.day_counting != "WORKING_DAYS":
        raise LeavePolicyError("The configured leave-counting rule is invalid.")

    total = Decimal("0")
    calendar_cache = {}
    for day in _date_range(start, end):
        calendar = calendar_cache.get(day.year)
        if calendar is None:
            calendar = _active_calendar("HOLIDAY", day)
            calendar_cache[day.year] = calendar
        weekdays = calendar.working_weekdays
        if (
            not isinstance(weekdays, list)
            or not weekdays
            or any(type(value) is not int or value not in range(7) for value in weekdays)
        ):
            raise LeavePolicyError(
                f"Configure working weekdays in the {day.year} holiday calendar."
            )
        if day.weekday() not in weekdays or calendar.dates.filter(day=day).exists():
            continue
        total += Decimal("0.5") if day_part != "FULL" else Decimal("1")
    if total <= 0:
        raise LeavePolicyError("The requested period contains no chargeable days.")
    if day_part != "FULL" and start != end:
        raise LeavePolicyError("A half-day request must be for one date.")
    return total


def _validate_substitute(
    applicant_id,
    substitute_id,
    start_date,
    end_date,
    excluding_request_id=None,
):
    if substitute_id is None:
        raise LeavePolicyError("Nominate one employee as the leave substitute.")
    if int(substitute_id) == int(applicant_id):
        raise LeavePolicyError("An employee cannot nominate themselves as substitute.")
    try:
        employees = get_users([substitute_id])
    except IamUnavailable as exc:
        raise LeavePolicyError(
            "The employee directory is unavailable; try again later."
        ) from exc
    substitute = employees.get(int(substitute_id))
    if substitute is None or substitute.kind not in ("faculty", "staff"):
        raise LeavePolicyError("The nominated substitute must be an active employee.")

    conflicts = LeaveRequest.objects.filter(
        user_id=substitute_id,
        status__in=ACTIVE_STATUSES,
        requested_start_date__lte=end_date,
        requested_end_date__gte=start_date,
    )
    if excluding_request_id is not None:
        conflicts = conflicts.exclude(pk=excluding_request_id)
    if conflicts.exists():
        raise LeavePolicyError(
            "The nominated substitute has pending or approved leave in this period."
        )


def _employee_record(user_id):
    try:
        employee = get_users([user_id]).get(int(user_id))
    except IamUnavailable as exc:
        raise LeavePolicyError(
            "The employee directory is unavailable; try again later."
        ) from exc
    if employee is None or employee.kind not in ("faculty", "staff"):
        raise LeavePolicyError("The applicant must be an active employee.")
    return employee


def _status_for_stage(stage):
    return {
        "UNIT_HEAD": "PENDING_UNIT_HEAD",
        "ESTABLISHMENT": "PENDING_ESTABLISHMENT",
        "SANCTION": "PENDING_SANCTION",
    }[stage]


def _approval_rules_for(request):
    candidates = LeaveAuthorityRule.objects.filter(
        department=request.applicant_department,
        for_director=request.applicant_is_director,
        is_active=True,
    )
    by_category = candidates.filter(leave_type_code=request.leave_type_code)
    if not by_category.exists():
        by_category = candidates.filter(leave_type_code="")
    if not by_category.exists():
        return []
    by_role = by_category.filter(applicant_role=request.applicant_role)
    if by_role.exists():
        return list(by_role.order_by("step_order"))
    return list(by_category.filter(applicant_role="").order_by("step_order"))


def _create_approval_tasks(request):
    if request.approval_tasks.exists():
        return
    rules = _approval_rules_for(request)
    if not rules:
        raise LeavePolicyError(
            "No active approval route is configured for the employee department and leave type."
        )

    if request.applicant_is_director:
        if (
            len(rules) != 1
            or rules[0].stage != "SANCTION"
            or rules[0].decision_mode != "FINAL"
            or not rules[0].is_self_sanction
        ):
            raise LeavePolicyError(
                "The Director route must be one configured self-sanction decision."
            )
    elif request.leave_type_code in ("CL", "RH"):
        if (
            len(rules) != 1
            or rules[0].stage != "UNIT_HEAD"
            or rules[0].decision_mode != "FINAL"
        ):
            raise LeavePolicyError(
                "CL and RH require one final Unit Head decision."
            )
    else:
        if (
            len(rules) < 2
            or rules[0].stage != "UNIT_HEAD"
            or rules[0].decision_mode != "RECOMMEND"
            or rules[-1].stage != "SANCTION"
            or rules[-1].decision_mode != "FINAL"
            or any(
                rule.stage != "ESTABLISHMENT" or rule.decision_mode != "VERIFY"
                for rule in rules[1:-1]
            )
        ):
            raise LeavePolicyError(
                "Higher leave routes need Unit Head recommendation, "
                "optional Establishment verification, and final sanction."
            )

    tasks = []
    for index, rule in enumerate(rules):
        assignee = (
            request.user_id if rule.is_self_sanction
            else rule.approver_user_id
        )
        if assignee is None:
            raise LeavePolicyError("Every approval step needs an assigned employee.")
        tasks.append(
            LeaveApprovalTask(
                request=request,
                rule=rule,
                step_order=rule.step_order,
                stage=rule.stage,
                decision_mode=rule.decision_mode,
                assignee_user_id=assignee,
                status="PENDING" if index == 0 else "BLOCKED",
            )
        )
    LeaveApprovalTask.objects.bulk_create(tasks)
    first_status = _status_for_stage(rules[0].stage)
    old_status = request.status
    request.status = first_status
    request.save(update_fields=("status", "updated_at"))
    for task in tasks:
        LeaveRequestEvent.objects.create(
            request=request,
            event_type="TASK_ASSIGNED",
            from_status=old_status,
            to_status=first_status,
            actor_user_id=None,
            note=f"{task.stage} task assigned to user {task.assignee_user_id}",
        )


def _annual_entitlement(policy, employee_kind):
    by_kind = policy.annual_entitlement_by_kind or {}
    if employee_kind in by_kind:
        return Decimal(str(by_kind[employee_kind]))
    return policy.annual_entitlement or Decimal("0")


def _annual_account(user_id, policy, year, employee_kind):
    defaults = {
        "annual_credit": _annual_entitlement(policy, employee_kind),
    }
    if policy.carries_forward:
        previous = LeaveBalance.objects.filter(
            user_id=user_id,
            leave_type_code=policy.leave_type_code,
            year=year - 1,
        ).first()
        if previous is not None:
            defaults["opening_balance"] = max(
                Decimal("0"), previous.available_days
            )
    account, created = LeaveBalance.objects.select_for_update().get_or_create(
        user_id=user_id,
        leave_type_code=policy.leave_type_code,
        year=year,
        defaults=defaults,
    )
    if created and account.annual_credit:
        LeaveBalanceEvent.objects.create(
            balance=account,
            event_type="CREDIT",
            amount=account.annual_credit,
            note="Configured annual entitlement",
        )
    return account


def _allocate_by_year(policy, start, end, day_part):
    allocations = {}
    cursor = start
    while cursor <= end:
        year_end = date(cursor.year, 12, 31)
        segment_end = min(end, year_end)
        segment_part = day_part if cursor == start and segment_end == end else "FULL"
        amount = _chargeable_days(policy, cursor, segment_end, segment_part)
        allocations[cursor.year] = amount
        cursor = segment_end + timedelta(days=1)
    return allocations




def _settle_reservations(leave_request, event_type, actor_user_id):
    reservations = LeaveBalanceEvent.objects.select_for_update().filter(
        request=leave_request,
        event_type="RESERVE",
    )
    for event in reservations:
        balance = LeaveBalance.objects.select_for_update().get(
            pk=event.balance_id
        )
        if balance.reserved_days < event.amount:
            raise LeavePolicyError(
                "The reserved balance no longer matches the request."
            )
        balance.reserved_days -= event.amount
        if event_type == "USE":
            balance.used_days += event.amount
        balance.save(
            update_fields=("reserved_days", "used_days", "updated_at")
        )
        LeaveBalanceEvent.objects.create(
            balance=balance,
            request=leave_request,
            event_type=event_type,
            amount=event.amount,
            actor_user_id=actor_user_id,
            note=(
                "Approved leave charged to balance"
                if event_type == "USE"
                else "Reservation released after final rejection"
            ),
        )

class LeaveRequestService:
    @staticmethod
    @transaction.atomic
    def submit_request(
        user_id,
        employee_kind,
        leave_type_code,
        requested_start_date,
        requested_end_date,
        substitute_user_id,
        active_role=None,
        actor_roles=(),
        day_part="FULL",
    ):
        if isinstance(requested_start_date, str):
            requested_start_date = date.fromisoformat(requested_start_date)
        if isinstance(requested_end_date, str):
            requested_end_date = date.fromisoformat(requested_end_date)

        if requested_end_date < requested_start_date:
            raise LeavePolicyError("The end date must be on or after the start date.")

        try:
            policy = LeavePolicy.objects.get(
                leave_type_code=leave_type_code,
                is_active=True,
            )
        except LeavePolicy.DoesNotExist as exc:
            raise LeavePolicyError("No active policy is configured for this leave type.") from exc

        applicant = _employee_record(user_id)
        if applicant.kind != employee_kind:
            raise LeavePolicyError("The authenticated employee category is out of date.")
        if employee_kind not in policy.employee_kinds:
            raise LeavePolicyError(
                "The employee is not eligible for this leave category."
            )
        _validate_substitute(
            user_id,
            substitute_user_id,
            requested_start_date,
            requested_end_date,
        )
        if day_part not in ("FULL", "FIRST_HALF", "SECOND_HALF"):
            raise LeavePolicyError("Invalid day part.")
        if day_part != "FULL" and not policy.half_day_allowed:
            raise LeavePolicyError("The configured leave policy does not permit half-days.")

        overlapping = LeaveRequest.objects.select_for_update().filter(
            user_id=user_id,
            status__in=ACTIVE_STATUSES,
            requested_start_date__lte=requested_end_date,
            requested_end_date__gte=requested_start_date,
        )
        new_interval = LeaveInterval(
            leave_type_code=leave_type_code,
            start_date=requested_start_date,
            end_date=requested_end_date,
            day_part=day_part,
        )
        for existing in overlapping:
            old_interval = LeaveInterval(
                leave_type_code=existing.leave_type_code,
                start_date=existing.requested_start_date,
                end_date=existing.requested_end_date,
                day_part=existing.day_part,
                status=existing.status,
            )
            if intervals_overlap(new_interval, old_interval):
                raise LeavePolicyError(
                    "The requested period overlaps another pending or approved leave."
                )

        allocations = _allocate_by_year(
            policy, requested_start_date, requested_end_date, day_part
        )
        if (policy.annual_entitlement is None
                and employee_kind not in (policy.annual_entitlement_by_kind or {})):
            raise LeavePolicyError(
                "Configure an annual entitlement before accepting this leave type."
            )
        accounts = []
        for year, days in allocations.items():
            account = _annual_account(user_id, policy, year, employee_kind)
            require_sufficient_balance(account.available_days, days)
            accounts.append((account, days))

        total_days = sum(allocations.values(), Decimal("0"))
        leave_request = LeaveRequest.objects.create(
            user_id=user_id,
            leave_type_code=leave_type_code,
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
            day_part=day_part,
            total_days=total_days,
            substitute_user_id=substitute_user_id,
            substitute_status="PENDING",
            substitute_replacement_count=0,
            applicant_department=(applicant.department or "").strip(),
            applicant_role=(active_role or "").lower(),
            applicant_is_director=(
                (active_role or "").lower() == "director"
                or any(str(role).lower() == "director" for role in actor_roles)
            ),
            status="PENDING_SUBSTITUTE",
        )
        for account, days in accounts:
            account.reserved_days += days
            account.save(update_fields=("reserved_days", "updated_at"))
            LeaveBalanceEvent.objects.create(
                balance=account,
                request=leave_request,
                event_type="RESERVE",
                amount=days,
                actor_user_id=user_id,
                note="Pending leave request",
            )
        LeaveRequestEvent.objects.create(
            request=leave_request,
            event_type="SUBMITTED",
            to_status=leave_request.status,
            note="Waiting for nominated substitute consent",
            actor_user_id=user_id,
        )
        return leave_request

    @staticmethod
    @transaction.atomic
    def withdraw_request(request_id, user_id):
        try:
            leave_request = LeaveRequest.objects.select_for_update().get(
                pk=request_id,
                user_id=user_id,
            )
        except LeaveRequest.DoesNotExist as exc:
            raise LeavePolicyError("Leave request was not found.") from exc

        if leave_request.status not in ACTIVE_STATUSES:
            raise LeavePolicyError(
                "Only a pending request can be withdrawn."
            )

        reservations = LeaveBalanceEvent.objects.select_for_update().filter(
            request=leave_request,
            event_type="RESERVE",
        )
        for event in reservations:
            balance = LeaveBalance.objects.select_for_update().get(
                pk=event.balance_id
            )
            if balance.reserved_days < event.amount:
                raise LeavePolicyError(
                    "The reserved balance no longer matches the request."
                )
            balance.reserved_days -= event.amount
            balance.save(update_fields=("reserved_days", "updated_at"))
            LeaveBalanceEvent.objects.create(
                balance=balance,
                request=leave_request,
                event_type="RELEASE",
                amount=event.amount,
                actor_user_id=user_id,
                note="Pending leave request withdrawn",
            )

        LeaveApprovalTask.objects.filter(
            request=leave_request,
            status__in=("PENDING", "BLOCKED"),
        ).update(
            status="CANCELLED",
            decided_at=timezone.now(),
            decision_note="Request withdrawn by employee",
        )
        previous_status = leave_request.status
        leave_request.status = "WITHDRAWN"
        leave_request.save(update_fields=("status", "updated_at"))
        LeaveRequestEvent.objects.create(
            request=leave_request,
            event_type="WITHDRAWN",
            from_status=previous_status,
            to_status=leave_request.status,
            actor_user_id=user_id,
        )
        return leave_request

    @staticmethod
    @transaction.atomic
    def respond_to_substitute(request_id, actor_user_id, action):
        try:
            leave_request = LeaveRequest.objects.select_for_update().get(
                pk=request_id,
                substitute_user_id=actor_user_id,
            )
        except LeaveRequest.DoesNotExist as exc:
            raise LeavePolicyError("Substitute task was not found.") from exc

        if (
            leave_request.status != "PENDING_SUBSTITUTE"
            or leave_request.substitute_status != "PENDING"
        ):
            raise LeavePolicyError("This substitute request is no longer pending.")
        action = action.upper()
        if action not in ("ACCEPT", "DECLINE"):
            raise LeavePolicyError("Substitute action must be ACCEPT or DECLINE.")

        previous_status = leave_request.status
        if action == "ACCEPT":
            leave_request.substitute_status = "ACCEPTED"
            leave_request.status = "PENDING_UNIT_HEAD"
        else:
            leave_request.substitute_status = "DECLINED"
            leave_request.status = "PENDING_SUBSTITUTE_REPLACEMENT"
        leave_request.save(
            update_fields=("substitute_status", "status", "updated_at")
        )
        if action == "ACCEPT":
            _create_approval_tasks(leave_request)
        LeaveRequestEvent.objects.create(
            request=leave_request,
            event_type=f"SUBSTITUTE_{action}",
            from_status=previous_status,
            to_status=leave_request.status,
            actor_user_id=actor_user_id,
        )
        return leave_request

    @staticmethod
    @transaction.atomic
    def replace_substitute(request_id, user_id, new_substitute_user_id):
        try:
            leave_request = LeaveRequest.objects.select_for_update().get(
                pk=request_id,
                user_id=user_id,
            )
        except LeaveRequest.DoesNotExist as exc:
            raise LeavePolicyError("Leave request was not found.") from exc

        if leave_request.status != "PENDING_SUBSTITUTE_REPLACEMENT":
            raise LeavePolicyError(
                "A substitute can be replaced only after the current one declines."
            )
        if leave_request.substitute_replacement_count >= 1:
            raise LeavePolicyError(
                "The one allowed substitute replacement has already been used."
            )
        if int(new_substitute_user_id) == leave_request.substitute_user_id:
            raise LeavePolicyError("Choose a different substitute.")

        _validate_substitute(
            user_id,
            new_substitute_user_id,
            leave_request.requested_start_date,
            leave_request.requested_end_date,
            excluding_request_id=leave_request.pk,
        )
        previous_status = leave_request.status
        leave_request.substitute_user_id = new_substitute_user_id
        leave_request.substitute_status = "PENDING"
        leave_request.substitute_replacement_count += 1
        leave_request.status = "PENDING_SUBSTITUTE"
        leave_request.save(
            update_fields=(
                "substitute_user_id",
                "substitute_status",
                "substitute_replacement_count",
                "status",
                "updated_at",
            )
        )
        LeaveRequestEvent.objects.create(
            request=leave_request,
            event_type="SUBSTITUTE_REPLACED",
            from_status=previous_status,
            to_status=leave_request.status,
            actor_user_id=user_id,
        )
        return leave_request

    @staticmethod
    @transaction.atomic
    def decide_request(request_id, actor_user_id, action, reason=""):
        try:
            task = LeaveApprovalTask.objects.select_for_update().select_related(
                "request", "rule"
            ).get(
                request_id=request_id,
                assignee_user_id=actor_user_id,
                status="PENDING",
            )
        except LeaveApprovalTask.DoesNotExist as exc:
            raise LeavePolicyError("Pending approval task was not found.") from exc

        leave_request = LeaveRequest.objects.select_for_update().get(
            pk=request_id
        )
        if leave_request.status != _status_for_stage(task.stage):
            raise LeavePolicyError(
                "The approval task no longer matches the request stage."
            )

        action = action.upper()
        if task.decision_mode == "RECOMMEND":
            outcomes = {
                "RECOMMEND": "RECOMMENDED",
                "NOT_RECOMMENDED": "NOT_RECOMMENDED",
            }
            if action not in outcomes:
                raise LeavePolicyError(
                    "This Unit Head step requires Recommend or Not Recommended."
                )
            task.status = outcomes[action]
            event_type = f"UNIT_HEAD_{action}"
        elif task.decision_mode == "VERIFY":
            if action != "VERIFY":
                raise LeavePolicyError(
                    "The Establishment step accepts only Verify."
                )
            task.status = "VERIFIED"
            event_type = "ESTABLISHMENT_VERIFIED"
        elif task.decision_mode == "FINAL":
            if action not in ("APPROVE", "REJECT"):
                raise LeavePolicyError(
                    "The final sanction step requires Approve or Reject."
                )
            task.status = "APPROVED" if action == "APPROVE" else "REJECTED"
            event_type = f"FINAL_{action}"
        else:
            raise LeavePolicyError("The configured approval task is invalid.")

        task.decided_at = timezone.now()
        task.decision_note = reason
        task.save(
            update_fields=("status", "decided_at", "decision_note")
        )

        if task.decision_mode != "FINAL":
            next_task = LeaveApprovalTask.objects.select_for_update().filter(
                request=leave_request,
                status="BLOCKED",
                step_order__gt=task.step_order,
            ).order_by("step_order").first()
            if next_task is None:
                raise LeavePolicyError(
                    "The configured route has no final sanction task."
                )
            next_task.status = "PENDING"
            next_task.save(update_fields=("status",))
            previous_status = leave_request.status
            leave_request.status = _status_for_stage(next_task.stage)
            leave_request.save(update_fields=("status", "updated_at"))
            LeaveRequestEvent.objects.create(
                request=leave_request,
                event_type=event_type,
                from_status=previous_status,
                to_status=leave_request.status,
                actor_user_id=actor_user_id,
                note=reason,
            )
            LeaveRequestEvent.objects.create(
                request=leave_request,
                event_type="TASK_ACTIVATED",
                from_status=previous_status,
                to_status=leave_request.status,
                actor_user_id=None,
                note=f"{next_task.stage} task assigned to user {next_task.assignee_user_id}",
            )
            return leave_request

        previous_status = leave_request.status
        if action == "APPROVE":
            leave_request.status = "APPROVED"
            leave_request.approved_by_user_id = actor_user_id
            leave_request.approved_at = timezone.now()
            _settle_reservations(leave_request, "USE", actor_user_id)
        else:
            leave_request.status = "REJECTED"
            leave_request.rejection_reason = reason
            _settle_reservations(leave_request, "RELEASE", actor_user_id)
        leave_request.save(
            update_fields=(
                "status",
                "approved_by_user_id",
                "approved_at",
                "rejection_reason",
                "updated_at",
            )
        )
        LeaveRequestEvent.objects.create(
            request=leave_request,
            event_type=event_type,
            from_status=previous_status,
            to_status=leave_request.status,
            actor_user_id=actor_user_id,
            note=reason,
        )
        return leave_request
