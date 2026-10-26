"""Transactional application and decision services for ELM.

Balances are configured data: the service must never invent an entitlement for
an employee. All changes to a pending balance and its request are committed
or rolled back together.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction

from modules.elm.domain.state_machine import WorkflowTransitionError
from modules.elm.models import (
    LeaveActionLog,
    LeaveBalance,
    LeaveBalanceAdjustment,
    LeaveRequest,
    LeaveStatus,
    LeaveType,
    SubstituteStatus,
)

PENDING_STATUSES = (
    LeaveStatus.PENDING_SUBSTITUTE,
    LeaveStatus.APPLICANT_ACTION_REQUIRED,
    LeaveStatus.PENDING_UNIT_HEAD,
    LeaveStatus.PENDING_AUTHORITY,
)


def _balance_for_update(user_id: str, leave_type: str, year: int) -> LeaveBalance:
    """Lock an existing entitlement row; create an uncredited row if absent."""
    balance, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id,
        leave_type=leave_type,
        year=year,
        defaults={"credited": Decimal("0.0")},
    )
    return LeaveBalance.objects.select_for_update().get(pk=balance.pk)


def _release_pending(req: LeaveRequest) -> LeaveBalance:
    balance = _balance_for_update(req.applicant_user_id, req.leave_type, req.start_date.year)
    if balance.pending < req.duration_days:
        raise WorkflowTransitionError(
            "The pending leave balance is inconsistent; an administrator must reconcile it."
        )
    balance.pending -= req.duration_days
    return balance


def _request_duration(
    start_date, end_date, leave_type: str, is_half_day: bool, half_day_session: str
) -> Decimal:
    if end_date < start_date:
        raise ValueError("End date must be on or after start date.")
    if start_date.year != end_date.year:
        raise ValueError("A leave request must fall within one leave-account year.")
    if is_half_day:
        if leave_type != LeaveType.CASUAL:
            raise ValueError("Half-day leave is available only for Casual Leave.")
        if start_date != end_date:
            raise ValueError("A half-day request must start and end on the same date.")
        if start_date.weekday() >= 5:
            raise ValueError("Half-day Casual Leave must fall on a working day.")
        if half_day_session not in {"FN", "AN"}:
            raise ValueError("Choose FN or AN for the half-day session.")
        return Decimal("0.5")
    if half_day_session:
        raise ValueError("Half-day session must be blank for a full-day request.")
    if leave_type in (LeaveType.EARNED, LeaveType.COMMUTED, LeaveType.VACATION):
        # These categories count every day in the continuous approved interval,
        # including intervening weekends and closed holidays.
        return Decimal((end_date - start_date).days + 1)
    if leave_type == LeaveType.RESTRICTED:
        # Calendar membership is checked when the effective published RH
        # calendar is integrated; a selected RH date is one charged day.
        return Decimal((end_date - start_date).days + 1)
    # CL and SCL do not use continuous-day counting. The installed baseline
    # has no published holiday calendar yet, so weekends are excluded here and
    # calendar exceptions remain an integration dependency.
    count = sum(
        1
        for offset in range((end_date - start_date).days + 1)
        if (start_date + timedelta(days=offset)).weekday() < 5
    )
    if count == 0:
        raise ValueError("The requested period contains no working days.")
    return Decimal(count)


def _check_overlap(
    applicant_id: str,
    start_date,
    end_date,
    leave_type: str,
    is_half_day: bool,
    half_day_session: str,
) -> None:
    overlaps = LeaveRequest.objects.filter(
        applicant_user_id=applicant_id,
        status__in=(
            LeaveStatus.PENDING_SUBSTITUTE,
            LeaveStatus.APPLICANT_ACTION_REQUIRED,
            LeaveStatus.PENDING_UNIT_HEAD,
            LeaveStatus.PENDING_AUTHORITY,
            LeaveStatus.APPROVED,
        ),
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if not overlaps.exists():
        return

    # The sole permitted same-day overlap is two opposite half-day CL requests.
    if (
        is_half_day
        and leave_type == LeaveType.CASUAL
        and start_date == end_date
        and not overlaps.exclude(
            leave_type=LeaveType.CASUAL,
            start_date=start_date,
            end_date=end_date,
            is_half_day=True,
        ).exists()
    ):
        sessions = set(overlaps.values_list("half_day_session", flat=True))
        if half_day_session not in sessions:
            return
    raise ValueError("The requested dates overlap another pending or approved leave.")


def _validate_substitute(applicant_id: str, substitute_id: str, start_date, end_date) -> str:
    try:
        numeric_id = int(substitute_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Enter the substitute's numeric Fusion user ID.") from exc
    if str(numeric_id) == str(applicant_id):
        raise ValueError("You cannot nominate yourself as a substitute.")

    # Access the shared directory only through its public module contract.
    from modules.directory.contracts import get_users

    person = get_users([numeric_id]).get(numeric_id)
    if person is None or not person.is_active or person.kind not in {"faculty", "staff"}:
        raise ValueError("The substitute must be another active Fusion employee.")
    conflict = LeaveRequest.objects.filter(
        applicant_user_id=str(numeric_id),
        status__in=(
            LeaveStatus.PENDING_SUBSTITUTE,
            LeaveStatus.APPLICANT_ACTION_REQUIRED,
            LeaveStatus.PENDING_UNIT_HEAD,
            LeaveStatus.PENDING_AUTHORITY,
            LeaveStatus.APPROVED,
        ),
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exists()
    if conflict:
        raise ValueError("The nominated substitute has overlapping pending or approved leave.")
    return str(numeric_id)


class LeaveService:
    @staticmethod
    @transaction.atomic
    def adjust_entitlement(
        *, user_id: str, leave_type: str, year: int, credited: Decimal,
        actor_id: str, reason: str,
    ) -> LeaveBalance:
        if leave_type not in LeaveType.values:
            raise ValueError("Select a supported leave category.")
        if year < 1900 or year > 9999:
            raise ValueError("Enter a valid leave-account year.")
        if not reason.strip():
            raise ValueError("An adjustment reason is required.")

        balance = _balance_for_update(str(user_id), leave_type, year)
        if credited < balance.availed + balance.pending:
            raise ValueError("Entitlement cannot be lower than already used or reserved leave.")
        previous = balance.credited
        balance.credited = credited
        balance.save(update_fields=["credited"])
        LeaveBalanceAdjustment.objects.create(
            user_id=str(user_id), leave_type=leave_type, year=year,
            actor_user_id=str(actor_id), previous_credited=previous,
            credited=credited, reason=reason.strip(),
        )
        return balance

    @staticmethod
    @transaction.atomic
    def apply_leave(
        applicant_id: str,
        leave_type: str,
        start_date,
        end_date,
        duration_days: Decimal | None,
        reason: str,
        is_half_day: bool = False,
        half_day_session: str = "",
        station_leave: bool = False,
        station_leave_address: str = "",
        out_of_station_from=None,
        out_of_station_to=None,
        substitute_id: str = "",
        applicant_roles: tuple[str, ...] = (),
    ) -> LeaveRequest:
        if leave_type not in LeaveType.values:
            raise ValueError("Select a supported leave category.")
        if not reason.strip():
            raise ValueError("A reason for leave is required.")
        duration = _request_duration(
            start_date, end_date, leave_type, is_half_day, half_day_session
        )
        if duration_days is not None and Decimal(duration_days) != duration:
            raise ValueError("Duration must match the requested dates and half-day selection.")
        if station_leave:
            if not station_leave_address.strip():
                raise ValueError("Provide a contact address for Station Leave.")
            if (out_of_station_from is None) != (out_of_station_to is None):
                raise ValueError("Provide both Station Leave dates or leave both blank.")
            if out_of_station_from and out_of_station_to:
                if out_of_station_to < out_of_station_from:
                    raise ValueError("Station Leave end date must not precede its start date.")
                if out_of_station_from < start_date or out_of_station_to > end_date:
                    raise ValueError(
                        "Station Leave dates must fall within the requested leave period."
                    )
        elif station_leave_address or out_of_station_from or out_of_station_to:
            raise ValueError("Station Leave details require Station Leave to be selected.")

        substitute_id = (substitute_id or "").strip()
        if substitute_id:
            substitute_id = _validate_substitute(
                str(applicant_id), substitute_id, start_date, end_date
            )
        _check_overlap(
            str(applicant_id),
            start_date,
            end_date,
            leave_type,
            is_half_day,
            half_day_session,
        )

        balance = _balance_for_update(str(applicant_id), leave_type, start_date.year)
        if balance.balance < duration:
            if balance.credited == 0:
                raise ValueError("No leave entitlement is configured for this category and year.")
            raise ValueError(
                f"Insufficient leave balance. Available: {balance.balance}, Requested: {duration}"
            )

        is_director = any(role.lower() == "director" for role in applicant_roles)
        if substitute_id:
            initial_status = LeaveStatus.PENDING_SUBSTITUTE
            approver_role = "director_substitute" if is_director else "substitute"
            substitute_status = SubstituteStatus.PENDING
        elif is_director:
            initial_status = LeaveStatus.PENDING_AUTHORITY
            approver_role = "director"
            substitute_status = SubstituteStatus.NOT_REQUIRED
        else:
            initial_status = LeaveStatus.PENDING_UNIT_HEAD
            approver_role = "unit_head"
            substitute_status = SubstituteStatus.NOT_REQUIRED

        req = LeaveRequest.objects.create(
            applicant_user_id=str(applicant_id),
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            duration_days=duration,
            reason=reason.strip(),
            is_half_day=is_half_day,
            half_day_session=half_day_session if is_half_day else "",
            station_leave=station_leave,
            station_leave_address=station_leave_address.strip() if station_leave else "",
            out_of_station_from=out_of_station_from if station_leave else None,
            out_of_station_to=out_of_station_to if station_leave else None,
            substitute_user_id=substitute_id,
            substitute_status=substitute_status,
            status=initial_status,
            current_approver_role=approver_role,
        )
        balance.pending += duration
        balance.save(update_fields=["pending"])
        LeaveActionLog.objects.create(
            leave_request=req,
            actor_user_id=str(applicant_id),
            actor_role="employee",
            action="SUBMIT",
            remarks=f"Applied for {duration} days {leave_type}",
        )
        return req

    @staticmethod
    @transaction.atomic
    def respond_substitute(
        leave_id: str, substitute_id: str, accept: bool, remarks: str = ""
    ) -> LeaveRequest:
        req = LeaveRequest.objects.select_for_update().get(id=leave_id)
        if req.substitute_user_id != str(substitute_id):
            raise PermissionError("Not the designated substitute.")
        if req.status != LeaveStatus.PENDING_SUBSTITUTE:
            raise WorkflowTransitionError("Request is not awaiting substitute response.")

        req.substitute_remarks = remarks.strip()
        if accept:
            req.substitute_status = SubstituteStatus.ACCEPTED
            if req.current_approver_role == "director_substitute":
                req.current_approver_role = "director"
                req.status = LeaveStatus.PENDING_AUTHORITY
            else:
                req.status = LeaveStatus.PENDING_UNIT_HEAD
                req.current_approver_role = "unit_head"
            action_code = "SUBSTITUTE_ACCEPT"
        else:
            req.substitute_status = SubstituteStatus.REJECTED
            req.status = LeaveStatus.APPLICANT_ACTION_REQUIRED
            req.current_approver_role = (
                "director_employee"
                if req.current_approver_role == "director_substitute"
                else "employee"
            )
            action_code = "SUBSTITUTE_DECLINE"

        req.save()
        LeaveActionLog.objects.create(
            leave_request=req,
            actor_user_id=str(substitute_id),
            actor_role="substitute",
            action=action_code,
            remarks=remarks.strip(),
        )
        return req

    @staticmethod
    @transaction.atomic
    def nominate_replacement(leave_id: str, applicant_id: str, substitute_id: str) -> LeaveRequest:
        req = LeaveRequest.objects.select_for_update().get(id=leave_id)
        if req.applicant_user_id != str(applicant_id):
            raise PermissionError("Cannot change another employee's request.")
        if req.status != LeaveStatus.APPLICANT_ACTION_REQUIRED:
            raise WorkflowTransitionError("A replacement can be nominated only after a decline.")
        substitute_id = str(substitute_id).strip()
        if not substitute_id or substitute_id == req.substitute_user_id:
            raise ValueError("Choose a different eligible substitute.")
        substitute_id = _validate_substitute(
            req.applicant_user_id, substitute_id, req.start_date, req.end_date
        )

        req.substitute_user_id = substitute_id
        req.substitute_status = SubstituteStatus.PENDING
        req.substitute_remarks = ""
        req.status = LeaveStatus.PENDING_SUBSTITUTE
        req.current_approver_role = (
            "director_substitute"
            if req.current_approver_role == "director_employee"
            else "substitute"
        )
        req.save()
        LeaveActionLog.objects.create(
            leave_request=req,
            actor_user_id=str(applicant_id),
            actor_role="employee",
            action="SUBSTITUTE_REPLACEMENT",
            remarks=f"Replacement substitute nominated: {substitute_id}",
        )
        return req

    @staticmethod
    @transaction.atomic
    def review_unit_head(
        leave_id: str,
        approver_id: str,
        approve: bool,
        remarks: str = "",
        forward_higher: bool = False,
    ) -> LeaveRequest:
        req = LeaveRequest.objects.select_for_update().get(id=leave_id)
        if req.status != LeaveStatus.PENDING_UNIT_HEAD:
            raise WorkflowTransitionError("Request is not awaiting Unit Head review.")
        is_cl_rh = req.leave_type in (LeaveType.CASUAL, LeaveType.RESTRICTED)
        if is_cl_rh and forward_higher:
            raise WorkflowTransitionError("CL/RH decisions are final at Unit Head review.")
        if not is_cl_rh and not forward_higher:
            raise WorkflowTransitionError(
                "Higher-sanction leave requires a recommendation to the authority."
            )

        if is_cl_rh and not approve:
            balance = _release_pending(req)
            balance.save(update_fields=["pending"])
            req.status = LeaveStatus.REJECTED
            req.rejection_reason = remarks.strip()
            action_code = "REJECT"
        elif not is_cl_rh:
            # Both Recommended and Not Recommended continue to final authority.
            req.status = LeaveStatus.PENDING_AUTHORITY
            req.current_approver_role = "sanctioning_authority"
            action_code = "RECOMMEND" if approve else "NOT_RECOMMEND"
        else:
            balance = _release_pending(req)
            balance.availed += req.duration_days
            balance.save(update_fields=["pending", "availed"])
            req.status = LeaveStatus.APPROVED
            action_code = "APPROVE"

        req.save()
        LeaveActionLog.objects.create(
            leave_request=req,
            actor_user_id=str(approver_id),
            actor_role="unit_head",
            action=action_code,
            remarks=remarks.strip(),
        )
        return req

    @staticmethod
    @transaction.atomic
    def decide_authority(
        leave_id: str, approver_id: str, approve: bool, remarks: str = ""
    ) -> LeaveRequest:
        req = LeaveRequest.objects.select_for_update().get(id=leave_id)
        if req.status != LeaveStatus.PENDING_AUTHORITY:
            raise WorkflowTransitionError("Request is not awaiting final authority decision.")
        if approve:
            balance = _release_pending(req)
            balance.availed += req.duration_days
            balance.save(update_fields=["pending", "availed"])
            req.status = LeaveStatus.APPROVED
            req.rejection_reason = ""
            action = "AUTHORITY_APPROVE"
        else:
            balance = _release_pending(req)
            balance.save(update_fields=["pending"])
            req.status = LeaveStatus.REJECTED
            req.rejection_reason = remarks.strip()
            action = "AUTHORITY_REJECT"
        req.save()
        LeaveActionLog.objects.create(
            leave_request=req,
            actor_user_id=str(approver_id),
            actor_role="sanctioning_authority",
            action=action,
            remarks=remarks.strip(),
        )
        return req

    @staticmethod
    @transaction.atomic
    def withdraw_leave(leave_id: str, user_id: str, reason: str = "") -> LeaveRequest:
        req = LeaveRequest.objects.select_for_update().get(id=leave_id)
        if req.applicant_user_id != str(user_id):
            raise PermissionError("Cannot withdraw another employee's request.")
        if req.status not in PENDING_STATUSES:
            raise WorkflowTransitionError(f"Cannot withdraw request in {req.status} status.")

        balance = _release_pending(req)
        balance.save(update_fields=["pending"])
        req.status = LeaveStatus.WITHDRAWN
        req.current_approver_role = ""
        req.save(update_fields=["status", "current_approver_role", "updated_at"])
        LeaveActionLog.objects.create(
            leave_request=req,
            actor_user_id=str(user_id),
            actor_role="employee",
            action="WITHDRAW",
            remarks=reason.strip(),
        )
        return req
