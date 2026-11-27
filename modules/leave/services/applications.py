"""Application lifecycle and workflow services for Employee Leave Management."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.directory import contracts as directory_contracts
from modules.leave.domain.counting import calculate_leave_days
from modules.leave.domain.state_machine import LeaveState
from modules.leave.models import (
    Holiday,
    LeaveBalance,
    LeaveLedgerEntry,
    LeaveRequest,
    LeaveType,
    SubstituteNomination,
    WorkflowTransition,
)


def apply_for_leave(
    *,
    actor_user_id: int,
    leave_type_code: str,
    start_date: date,
    end_date: date,
    reason: str,
    is_half_day: bool = False,
    half_day_period: str = "",
    is_station_leave: bool = False,
    station_departure_date: date | None = None,
    station_arrival_date: date | None = None,
    station_destination: str = "",
    substitute_user_id: int | None = None,
    address_during_leave: str = "",
    contact_number: str = "",
    actor_roles: Sequence[str] = (),
) -> LeaveRequest:
    """Validate and submit a new leave application (CFR-EL-002, EL-UC-001)."""
    if start_date > end_date:
        raise BadRequestError("Start date cannot be after end date.")

    if is_half_day:
        if start_date != end_date:
            raise BadRequestError("Half-day leave must start and end on the same date.")
        if half_day_period not in ("first_half", "second_half"):
            raise BadRequestError(
                "Half-day leave requires specifying 'first_half' or 'second_half'."
            )

    try:
        leave_type = LeaveType.objects.get(code=leave_type_code, is_active=True)
    except LeaveType.DoesNotExist as err:
        raise NotFoundError(
            f"Leave type '{leave_type_code}' does not exist or is inactive."
        ) from err

    if is_half_day and not leave_type.allows_half_day:
        raise ConflictError(f"Leave type '{leave_type_code}' does not permit half-day leave.")

    # Holiday lookup for working-day vs continuous counting (BR-EL-011)
    closed_holidays = set(
        Holiday.objects.filter(
            calendar__year=start_date.year,
            calendar__is_published=True,
            is_restricted=False,
        ).values_list("date", flat=True)
    )

    requested_days = calculate_leave_days(
        start_date=start_date,
        end_date=end_date,
        is_continuous=leave_type.is_continuous_count,
        closed_holidays=closed_holidays,
        is_half_day=is_half_day,
    )

    # Overlap check (BR-EL-012)
    active_requests = LeaveRequest.objects.filter(
        user_id=actor_user_id,
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exclude(status__in=(LeaveState.REJECTED, LeaveState.WITHDRAWN, LeaveState.CANCELLED))

    for existing in active_requests:
        # Half-day non-overlap exception (BR-EL-012)
        if (
            is_half_day
            and existing.is_half_day
            and existing.start_date == start_date
            and existing.half_day_period != half_day_period
        ):
            continue
        raise ConflictError(
            "Requested leave period overlaps with an existing pending or approved leave."
        )

    # Server-side directory snapshot (cadre and department)
    users = directory_contracts.get_users([actor_user_id])
    user_dto = users.get(actor_user_id)
    cadre = user_dto.kind if user_dto else "faculty"
    department = user_dto.department if user_dto else ""

    # Balance check: verify entitlement is sufficient before submission
    try:
        balance = LeaveBalance.objects.get(
            user_id=actor_user_id, leave_type=leave_type, year=start_date.year
        )
    except LeaveBalance.DoesNotExist as err:
        raise ConflictError(
            f"No leave balance allocated for user {actor_user_id} and leave type "
            f"{leave_type_code} in year {start_date.year}."
        ) from err

    if balance.available_days < requested_days:
        raise ConflictError(
            f"Insufficient leave balance: requested {requested_days} days, "
            f"but only {balance.available_days} available."
        )

    # Substitute validation (BR-EL-014, BR-EL-015)
    if substitute_user_id is not None:
        if substitute_user_id == actor_user_id:
            raise ConflictError("Applicant cannot nominate themselves as a substitute.")

        sub_overlaps = LeaveRequest.objects.filter(
            user_id=substitute_user_id,
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exclude(status__in=(LeaveState.REJECTED, LeaveState.WITHDRAWN, LeaveState.CANCELLED))
        if sub_overlaps.exists():
            raise ConflictError(
                "Nominated substitute has active or pending leave during the requested period."
            )

    # Initial workflow state determination
    is_director_applicant = "Director" in actor_roles
    if is_director_applicant:
        initial_state = (
            LeaveState.AWAITING_SUBSTITUTE if substitute_user_id else LeaveState.AWAITING_DIRECTOR
        )
        handler_role = "Director" if not substitute_user_id else ""
    else:
        initial_state = (
            LeaveState.AWAITING_SUBSTITUTE if substitute_user_id else LeaveState.AWAITING_UNIT_HEAD
        )
        handler_role = "HOD" if not substitute_user_id else ""

    with transaction.atomic():
        app_num = f"LEAVE-{start_date.year}-{uuid.uuid4().hex[:6].upper()}"
        req = LeaveRequest.objects.create(
            application_number=app_num,
            user_id=actor_user_id,
            cadre=cadre,
            department=department,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            is_half_day=is_half_day,
            half_day_period=half_day_period if is_half_day else "",
            requested_days=requested_days,
            reason=reason,
            address_during_leave=address_during_leave,
            contact_number=contact_number,
            is_station_leave=is_station_leave,
            station_departure_date=station_departure_date if is_station_leave else None,
            station_arrival_date=station_arrival_date if is_station_leave else None,
            station_destination=station_destination if is_station_leave else "",
            status=initial_state,
            current_handler_role=handler_role,
        )

        if substitute_user_id is not None:
            SubstituteNomination.objects.create(
                request=req,
                substitute_user_id=substitute_user_id,
                status="pending",
                sequence=1,
            )

        WorkflowTransition.objects.create(
            request=req,
            from_state="none",
            to_state=initial_state,
            action="apply",
            actor_user_id=actor_user_id,
            actor_role=cadre,
            remarks=reason,
        )

    return req


def respond_to_substitute(
    *,
    actor_user_id: int,
    nomination_id: int,
    decision: str,  # "accepted" or "declined"
    remarks: str = "",
) -> SubstituteNomination:
    """Record substitute response and enforce consent gate (BR-EL-015, EL-UC-002)."""
    if decision not in ("accepted", "declined"):
        raise BadRequestError("Decision must be 'accepted' or 'declined'.")

    with transaction.atomic():
        try:
            nomination = (
                SubstituteNomination.objects.select_for_update()
                .select_related("request", "request__leave_type")
                .get(pk=nomination_id)
            )
        except SubstituteNomination.DoesNotExist as err:
            raise NotFoundError("Substitute nomination not found.") from err

        if nomination.substitute_user_id != actor_user_id:
            raise PermissionDeniedError("You are not the nominated substitute for this request.")

        if nomination.status != "pending":
            raise ConflictError(
                f"Substitute request has already been answered with '{nomination.status}'."
            )

        req = nomination.request
        if req.status not in (
            LeaveState.AWAITING_SUBSTITUTE,
            LeaveState.AWAITING_EXTENSION_SUBSTITUTE,
        ):
            raise ConflictError(
                f"Request is in state '{req.status}' and not awaiting substitute response."
            )

        nomination.status = decision
        nomination.remarks = remarks
        nomination.responded_at = timezone.now()
        nomination.save()

        old_state = req.status
        if decision == "accepted":
            if req.current_handler_role == "Director":
                next_state = LeaveState.AWAITING_DIRECTOR
            elif req.status == LeaveState.AWAITING_EXTENSION_SUBSTITUTE:
                next_state = LeaveState.AWAITING_EXTENSION_UNIT_HEAD
                req.current_handler_role = "HOD"
            else:
                next_state = LeaveState.AWAITING_UNIT_HEAD
                req.current_handler_role = "HOD"
            action = "substitute_accept"
        else:
            if req.status == LeaveState.AWAITING_EXTENSION_SUBSTITUTE:
                next_state = LeaveState.EXTENSION_APPLICANT_ACTION_REQUIRED
            else:
                next_state = LeaveState.APPLICANT_ACTION_REQUIRED
            action = "substitute_decline"

        req.status = next_state
        req.save()

        WorkflowTransition.objects.create(
            request=req,
            from_state=old_state,
            to_state=next_state,
            action=action,
            actor_user_id=actor_user_id,
            actor_role="substitute",
            remarks=remarks,
        )

    return nomination


def review_unit_head(
    *,
    actor_user_id: int,
    actor_roles: Sequence[str],
    request_id: int,
    decision: str,  # "approve", "reject", "recommend", "not_recommend"
    remarks: str = "",
) -> LeaveRequest:
    """Unit Head decision for CL/RH or recommendation for higher sanction.

    Implements BR-EL-016..017, EL-UC-003.
    """
    with transaction.atomic():
        try:
            req = (
                LeaveRequest.objects.select_for_update()
                .select_related("leave_type")
                .get(pk=request_id)
            )
        except LeaveRequest.DoesNotExist as err:
            raise NotFoundError("Leave request not found.") from err

        if req.status != LeaveState.AWAITING_UNIT_HEAD:
            raise ConflictError(
                f"Request is in state '{req.status}' and not awaiting Unit Head review."
            )

        if actor_user_id == req.user_id:
            raise PermissionDeniedError("Unit Head cannot review their own leave request.")

        if not any(r in actor_roles for r in ("HOD", "Unit Head")):
            raise PermissionDeniedError("Actor does not hold the Unit Head role.")

        # Department scoping: verify HOD department matches applicant department
        hod_dtos = directory_contracts.get_users([actor_user_id])
        hod_dto = hod_dtos.get(actor_user_id)
        if hod_dto and req.department and hod_dto.department != req.department:
            raise PermissionDeniedError(
                f"HOD department '{hod_dto.department}' does not match "
                f"request department '{req.department}'."
            )

        old_state = req.status
        is_cl_or_rh = req.leave_type.code in ("CL", "RH")

        if is_cl_or_rh:
            # BR-EL-016: Unit Head is final authority for CL/RH
            if decision not in ("approve", "reject"):
                raise BadRequestError(
                    "For CL/RH requests, Unit Head decision must be 'approve' or 'reject'."
                )

            if decision == "approve":
                req.status = LeaveState.APPROVED
                req.current_handler_role = ""

                # Deduct balance atomically
                balance = LeaveBalance.objects.select_for_update().get(
                    user_id=req.user_id, leave_type=req.leave_type, year=req.start_date.year
                )
                if balance.available_days < req.requested_days:
                    raise ConflictError("Insufficient leave balance at approval time.")

                balance.used_days += req.requested_days
                balance.available_days -= req.requested_days
                balance.save()

                LeaveLedgerEntry.objects.create(
                    balance=balance,
                    entry_type="debit",
                    amount=req.requested_days,
                    balance_after=balance.available_days,
                    reference_type="leave_request",
                    reference_id=req.id,
                    description="Unit Head approved leave",
                    performed_by_user_id=actor_user_id,
                )
                action = "unit_head_approve"
            else:
                req.status = LeaveState.REJECTED
                req.current_handler_role = ""
                action = "unit_head_reject"
        else:
            # BR-EL-017: Unit Head records recommendation for SCL/EL/COL/VL
            if decision not in ("recommend", "not_recommend"):
                raise BadRequestError(
                    "For higher-sanction leave (SCL/EL/COL/VL), "
                    "decision must be 'recommend' or 'not_recommend'."
                )

            req.unit_head_recommendation = (
                "recommended" if decision == "recommend" else "not_recommended"
            )
            req.unit_head_remarks = remarks
            req.status = LeaveState.AWAITING_SANCTION
            req.current_handler_role = "Dean Academic"
            action = f"unit_head_{decision}"

        req.save()

        WorkflowTransition.objects.create(
            request=req,
            from_state=old_state,
            to_state=req.status,
            action=action,
            actor_user_id=actor_user_id,
            actor_role="HOD",
            remarks=remarks,
        )

    return req


def sanction_leave(
    *,
    actor_user_id: int,
    actor_roles: Sequence[str],
    request_id: int,
    decision: str,  # "approve" or "reject"
    remarks: str = "",
) -> LeaveRequest:
    """Execute final decision by Sanctioning Authority or Director self-sanction.

    Implements BR-EL-018, BR-EL-020, EL-UC-005.
    """
    if decision not in ("approve", "reject"):
        raise BadRequestError("Decision must be 'approve' or 'reject'.")

    with transaction.atomic():
        try:
            req = (
                LeaveRequest.objects.select_for_update()
                .select_related("leave_type")
                .get(pk=request_id)
            )
        except LeaveRequest.DoesNotExist as err:
            raise NotFoundError("Leave request not found.") from err

        old_state = req.status

        # Director self-sanction (BR-EL-020)
        if req.status == LeaveState.AWAITING_DIRECTOR:
            if actor_user_id != req.user_id or "Director" not in actor_roles:
                raise PermissionDeniedError(
                    "Only the Director applicant may execute self-sanction."
                )
            actor_role = "Director"
        elif req.status == LeaveState.AWAITING_SANCTION:
            if actor_user_id == req.user_id:
                raise PermissionDeniedError(
                    "Sanctioning authority cannot approve their own leave request."
                )
            sanction_roles = {
                "Dean",
                "Dean Academic",
                "Director",
                "Registrar",
                "Deputy Registrar (Estt.)",
            }
            matched_roles = sanction_roles.intersection(set(actor_roles))
            if not matched_roles:
                raise PermissionDeniedError(
                    "Actor does not hold an authorized Sanctioning Authority role."
                )
            actor_role = sorted(matched_roles)[0]
        else:
            raise ConflictError(f"Request is in state '{req.status}' and not awaiting sanction.")

        if decision == "approve":
            req.status = LeaveState.APPROVED
            req.current_handler_role = ""

            # Deduct balance atomically
            balance = LeaveBalance.objects.select_for_update().get(
                user_id=req.user_id, leave_type=req.leave_type, year=req.start_date.year
            )
            if balance.available_days < req.requested_days:
                raise ConflictError("Insufficient leave balance at sanction time.")

            balance.used_days += req.requested_days
            balance.available_days -= req.requested_days
            balance.save()

            LeaveLedgerEntry.objects.create(
                balance=balance,
                entry_type="debit",
                amount=req.requested_days,
                balance_after=balance.available_days,
                reference_type="leave_request",
                reference_id=req.id,
                description="Sanctioning authority approved leave",
                performed_by_user_id=actor_user_id,
            )
            action = "sanction_approve"
        else:
            req.status = LeaveState.REJECTED
            req.current_handler_role = ""
            action = "sanction_reject"

        req.save()

        WorkflowTransition.objects.create(
            request=req,
            from_state=old_state,
            to_state=req.status,
            action=action,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            remarks=remarks,
        )

    return req


def withdraw_leave_request(
    *,
    actor_user_id: int,
    request_id: int,
    remarks: str = "",
) -> LeaveRequest:
    """Immediate applicant withdrawal of pending request before final approval.

    Implements BR-EL-022, EL-UC-007.
    """
    with transaction.atomic():
        try:
            req = LeaveRequest.objects.select_for_update().get(pk=request_id)
        except LeaveRequest.DoesNotExist as err:
            raise NotFoundError("Leave request not found.") from err

        if req.user_id != actor_user_id:
            raise PermissionDeniedError("You can only withdraw your own leave requests.")

        if req.status in (
            LeaveState.APPROVED,
            LeaveState.REJECTED,
            LeaveState.WITHDRAWN,
            LeaveState.CANCELLED,
        ):
            raise ConflictError(
                f"Cannot withdraw request in state '{req.status}'. "
                "Only pending requests may be withdrawn."
            )

        old_state = req.status
        req.status = LeaveState.WITHDRAWN
        req.current_handler_role = ""
        req.current_handler_user_id = None
        req.save()

        WorkflowTransition.objects.create(
            request=req,
            from_state=old_state,
            to_state=LeaveState.WITHDRAWN,
            action="withdraw",
            actor_user_id=actor_user_id,
            actor_role="applicant",
            remarks=remarks,
        )

    return req
