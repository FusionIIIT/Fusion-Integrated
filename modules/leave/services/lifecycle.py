"""Lifecycle services for Employee Leave Management.

Covers cancellation, extension, resumption, and offline records.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal

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
    ResumptionRecord,
    SubstituteNomination,
    WorkflowTransition,
)

# ==============================================================================
# 1. Approved-Leave Cancellation Before Start ? CW-EL-02 (BR-EL-023, EL-UC-008)
# ==============================================================================


def request_cancellation(
    *,
    actor_user_id: int,
    request_id: int,
    reason: str,
    current_date: date | None = None,
) -> LeaveRequest:
    """Applicant requests cancellation of approved leave before its start date (BR-EL-023)."""
    today = current_date or timezone.localdate()

    with transaction.atomic():
        try:
            req = (
                LeaveRequest.objects.select_for_update()
                .select_related("leave_type")
                .get(pk=request_id)
            )
        except LeaveRequest.DoesNotExist as err:
            raise NotFoundError("Leave request not found.") from err

        if req.user_id != actor_user_id:
            raise PermissionDeniedError(
                "You can only request cancellation for your own leave requests."
            )

        if req.status != LeaveState.APPROVED:
            raise ConflictError(
                f"Cannot cancel leave in state '{req.status}'. "
                "Cancellation is only available for approved leave."
            )

        if today >= req.start_date:
            raise ConflictError(
                "Cancellation is only permitted strictly before the leave start date."
            )

        old_state = req.status
        req.cancellation_reason = reason
        req.cancellation_requested_at = timezone.now()
        req.status = LeaveState.CANCELLATION_PENDING_UNIT_HEAD
        req.current_handler_role = "HOD"
        req.save()

        WorkflowTransition.objects.create(
            request=req,
            from_state=old_state,
            to_state=req.status,
            action="request_cancellation",
            actor_user_id=actor_user_id,
            actor_role="applicant",
            remarks=reason,
        )

    return req


def review_cancellation_unit_head(
    *,
    actor_user_id: int,
    actor_roles: Sequence[str],
    request_id: int,
    decision: str,  # "approve", "reject", "recommend", "not_recommend"
    remarks: str = "",
) -> LeaveRequest:
    """Unit Head review of approved leave cancellation (BW-EL-10, BW-EL-11)."""
    with transaction.atomic():
        try:
            req = (
                LeaveRequest.objects.select_for_update()
                .select_related("leave_type")
                .get(pk=request_id)
            )
        except LeaveRequest.DoesNotExist as err:
            raise NotFoundError("Leave request not found.") from err

        if req.status != LeaveState.CANCELLATION_PENDING_UNIT_HEAD:
            raise ConflictError(
                f"Request is in state '{req.status}' and not awaiting "
                "Unit Head cancellation review."
            )

        if actor_user_id == req.user_id:
            raise PermissionDeniedError("Unit Head cannot review their own cancellation request.")

        if not any(r in actor_roles for r in ("HOD", "Unit Head")):
            raise PermissionDeniedError("Actor does not hold the Unit Head role.")

        # Department scoping
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
            # BW-EL-10: Unit Head is final authority for CL/RH cancellation
            if decision not in ("approve", "reject"):
                raise BadRequestError("Decision must be 'approve' or 'reject'.")

            if decision == "approve":
                req.status = LeaveState.CANCELLED
                req.current_handler_role = ""

                # Restore deducted balance atomically
                balance = LeaveBalance.objects.select_for_update().get(
                    user_id=req.user_id, leave_type=req.leave_type, year=req.start_date.year
                )
                balance.used_days -= req.requested_days
                balance.available_days += req.requested_days
                balance.save()

                LeaveLedgerEntry.objects.create(
                    balance=balance,
                    entry_type="credit",
                    amount=req.requested_days,
                    balance_after=balance.available_days,
                    reference_type="cancellation",
                    reference_id=req.id,
                    description="Cancellation approved: balance restored",
                    performed_by_user_id=actor_user_id,
                )
                action = "cancellation_unit_head_approve"
            else:
                req.status = (
                    LeaveState.APPROVED
                )  # Rejection leaves original approval unchanged (BR-EL-023)
                req.current_handler_role = ""
                action = "cancellation_unit_head_reject"
        else:
            # BW-EL-11: Higher sanction required
            req.unit_head_recommendation = (
                "recommended" if decision in ("approve", "recommend") else "not_recommended"
            )
            req.unit_head_remarks = remarks
            req.status = LeaveState.CANCELLATION_PENDING_SANCTION
            req.current_handler_role = "Dean Academic"
            action = f"cancellation_unit_head_{decision}"

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


def sanction_cancellation(
    *,
    actor_user_id: int,
    actor_roles: Sequence[str],
    request_id: int,
    decision: str,  # "approve" or "reject"
    remarks: str = "",
) -> LeaveRequest:
    """Final sanctioning decision for higher-sanction leave cancellation (BW-EL-11)."""
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

        if req.status != LeaveState.CANCELLATION_PENDING_SANCTION:
            raise ConflictError(
                f"Request is in state '{req.status}' and not awaiting cancellation sanction."
            )

        if actor_user_id == req.user_id:
            raise PermissionDeniedError(
                "Sanctioning authority cannot approve their own cancellation."
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

        old_state = req.status
        actor_role = sorted(matched_roles)[0]

        if decision == "approve":
            req.status = LeaveState.CANCELLED
            req.current_handler_role = ""

            # Restore deducted balance atomically
            balance = LeaveBalance.objects.select_for_update().get(
                user_id=req.user_id, leave_type=req.leave_type, year=req.start_date.year
            )
            balance.used_days -= req.requested_days
            balance.available_days += req.requested_days
            balance.save()

            LeaveLedgerEntry.objects.create(
                balance=balance,
                entry_type="credit",
                amount=req.requested_days,
                balance_after=balance.available_days,
                reference_type="cancellation",
                reference_id=req.id,
                description="Higher-sanction cancellation approved: balance restored",
                performed_by_user_id=actor_user_id,
            )
            action = "cancellation_sanction_approve"
        else:
            req.status = LeaveState.APPROVED  # Original approval preserved
            req.current_handler_role = ""
            action = "cancellation_sanction_reject"

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


# ==============================================================================
# 2. Extension of Ongoing Leave ? CW-EL-03 (BR-EL-025, EL-UC-009)
# ==============================================================================


def request_extension(
    *,
    actor_user_id: int,
    request_id: int,
    extension_end_date: date,
    reason: str,
    substitute_user_id: int | None = None,
    current_date: date | None = None,
) -> LeaveRequest:
    """Applicant requests extension on ongoing EL, COL, or VL (BR-EL-025)."""
    today = current_date or timezone.localdate()

    with transaction.atomic():
        try:
            req = (
                LeaveRequest.objects.select_for_update()
                .select_related("leave_type")
                .get(pk=request_id)
            )
        except LeaveRequest.DoesNotExist as err:
            raise NotFoundError("Leave request not found.") from err

        if req.user_id != actor_user_id:
            raise PermissionDeniedError("You can only extend your own leave requests.")

        if not req.leave_type.allows_extension:
            raise ConflictError(
                f"Extension is not permitted for leave type '{req.leave_type.code}'."
            )

        if req.status not in (LeaveState.APPROVED, LeaveState.EXTENDED):
            raise ConflictError(
                f"Cannot extend leave in state '{req.status}'. Leave must be approved and ongoing."
            )

        if not (req.start_date <= today <= req.end_date):
            raise ConflictError("Extension is only permitted while leave is ongoing.")

        if extension_end_date <= req.end_date:
            raise BadRequestError("Extension end date must be after the current leave end date.")

        # Incremental days calculation (BR-EL-025)
        extension_start = req.end_date + timedelta(days=1)
        closed_holidays = set(
            Holiday.objects.filter(
                calendar__year=extension_start.year,
                calendar__is_published=True,
                is_restricted=False,
            ).values_list("date", flat=True)
        )
        incremental_days = calculate_leave_days(
            start_date=extension_start,
            end_date=extension_end_date,
            is_continuous=req.leave_type.is_continuous_count,
            closed_holidays=closed_holidays,
        )

        # Verify entitlement is sufficient for the additional period
        balance = LeaveBalance.objects.get(
            user_id=req.user_id, leave_type=req.leave_type, year=req.start_date.year
        )
        if balance.available_days < incremental_days:
            raise ConflictError(
                f"Insufficient balance for extension: {incremental_days} required, "
                f"{balance.available_days} available."
            )

        old_state = req.status
        req.extension_end_date = extension_end_date
        req.extension_days = incremental_days
        req.extension_reason = reason

        if substitute_user_id is not None:
            if substitute_user_id == actor_user_id:
                raise ConflictError("Applicant cannot nominate themselves as a substitute.")
            req.status = LeaveState.AWAITING_EXTENSION_SUBSTITUTE
            SubstituteNomination.objects.create(
                request=req,
                substitute_user_id=substitute_user_id,
                status="pending",
                sequence=2,
            )
        else:
            req.status = LeaveState.AWAITING_EXTENSION_UNIT_HEAD
            req.current_handler_role = "HOD"

        req.save()

        WorkflowTransition.objects.create(
            request=req,
            from_state=old_state,
            to_state=req.status,
            action="request_extension",
            actor_user_id=actor_user_id,
            actor_role="applicant",
            remarks=reason,
        )

    return req


def review_extension_unit_head(
    *,
    actor_user_id: int,
    actor_roles: Sequence[str],
    request_id: int,
    decision: str,  # "recommend", "not_recommend"
    remarks: str = "",
) -> LeaveRequest:
    """Unit Head records recommendation for ongoing leave extension (BW-EL-12..14)."""
    if decision not in ("recommend", "not_recommend"):
        raise BadRequestError("Decision must be 'recommend' or 'not_recommend'.")

    with transaction.atomic():
        try:
            req = (
                LeaveRequest.objects.select_for_update()
                .select_related("leave_type")
                .get(pk=request_id)
            )
        except LeaveRequest.DoesNotExist as err:
            raise NotFoundError("Leave request not found.") from err

        if req.status != LeaveState.AWAITING_EXTENSION_UNIT_HEAD:
            raise ConflictError(
                f"Request is in state '{req.status}' and not awaiting Unit Head extension review."
            )

        if actor_user_id == req.user_id:
            raise PermissionDeniedError("Unit Head cannot review their own extension.")

        if not any(r in actor_roles for r in ("HOD", "Unit Head")):
            raise PermissionDeniedError("Actor does not hold the Unit Head role.")

        # Department scoping
        hod_dtos = directory_contracts.get_users([actor_user_id])
        hod_dto = hod_dtos.get(actor_user_id)
        if hod_dto and req.department and hod_dto.department != req.department:
            raise PermissionDeniedError(
                f"HOD department '{hod_dto.department}' does not match "
                f"request department '{req.department}'."
            )

        old_state = req.status
        req.unit_head_recommendation = (
            "recommended" if decision == "recommend" else "not_recommended"
        )
        req.unit_head_remarks = remarks
        req.status = LeaveState.EXTENSION_PENDING_SANCTION
        req.current_handler_role = "Dean Academic"
        req.save()

        WorkflowTransition.objects.create(
            request=req,
            from_state=old_state,
            to_state=req.status,
            action=f"extension_unit_head_{decision}",
            actor_user_id=actor_user_id,
            actor_role="HOD",
            remarks=remarks,
        )

    return req


def sanction_extension(
    *,
    actor_user_id: int,
    actor_roles: Sequence[str],
    request_id: int,
    decision: str,  # "approve" or "reject"
    remarks: str = "",
) -> LeaveRequest:
    """Final sanctioning decision for ongoing leave extension (BW-EL-12..14)."""
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

        if req.status != LeaveState.EXTENSION_PENDING_SANCTION:
            raise ConflictError(
                f"Request is in state '{req.status}' and not awaiting extension sanction."
            )

        if actor_user_id == req.user_id:
            raise PermissionDeniedError("Sanctioning authority cannot approve their own extension.")

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

        old_state = req.status
        actor_role = sorted(matched_roles)[0]

        if decision == "approve":
            # BR-EL-025: Approval posts only the incremental additional period
            req.end_date = req.extension_end_date
            req.requested_days += req.extension_days
            req.status = LeaveState.EXTENDED
            req.current_handler_role = ""

            balance = LeaveBalance.objects.select_for_update().get(
                user_id=req.user_id, leave_type=req.leave_type, year=req.start_date.year
            )
            if balance.available_days < req.extension_days:
                raise ConflictError("Insufficient balance at extension sanction time.")

            balance.used_days += req.extension_days
            balance.available_days -= req.extension_days
            balance.save()

            LeaveLedgerEntry.objects.create(
                balance=balance,
                entry_type="debit",
                amount=req.extension_days,
                balance_after=balance.available_days,
                reference_type="extension",
                reference_id=req.id,
                description="Extension approved: incremental period posted",
                performed_by_user_id=actor_user_id,
            )
            action = "extension_sanction_approve"
        else:
            # Rejection preserves original approved leave (BR-EL-025)
            req.status = LeaveState.APPROVED
            req.current_handler_role = ""
            action = "extension_sanction_reject"

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


# ==============================================================================
# 3. Duty Resumption Review ? CW-EL-04 (BR-EL-027..028, DEC-ELM-001)
# ==============================================================================


def submit_resumption(
    *,
    actor_user_id: int,
    request_id: int,
    actual_resumption_date: date,
    remarks: str = "",
) -> ResumptionRecord:
    """Employee submits actual return to duty information (BR-EL-027, EL-UC-010)."""
    with transaction.atomic():
        try:
            req = (
                LeaveRequest.objects.select_for_update()
                .select_related("leave_type")
                .get(pk=request_id)
            )
        except LeaveRequest.DoesNotExist as err:
            raise NotFoundError("Leave request not found.") from err

        if req.user_id != actor_user_id:
            raise PermissionDeniedError("You can only submit resumption for your own leave.")

        if not req.leave_type.allows_extension and req.leave_type.code not in ("EL", "COL", "VL"):
            raise ConflictError("Formal resumption review applies only to EL, COL, and VL.")

        if req.status not in (LeaveState.APPROVED, LeaveState.EXTENDED):
            raise ConflictError(f"Cannot submit resumption for request in state '{req.status}'.")

        expected_date = req.end_date + timedelta(days=1)
        closed_holidays = set(
            Holiday.objects.filter(
                calendar__year=req.start_date.year,
                calendar__is_published=True,
                is_restricted=False,
            ).values_list("date", flat=True)
        )

        if actual_resumption_date == expected_date:
            nature = "normal"
            diff_days = Decimal("0.0")
        elif actual_resumption_date < expected_date:
            nature = "early"
            # Early return: leave ended before approved end date
            # Unavailed days = actual_resumption_date to approved end_date
            diff_days = -calculate_leave_days(
                start_date=actual_resumption_date,
                end_date=req.end_date,
                is_continuous=req.leave_type.is_continuous_count,
                closed_holidays=closed_holidays,
            )
        else:
            nature = "late"
            # Late return: extra days from approved end_date + 1 to actual_resumption_date - 1
            extra_start = expected_date
            extra_end = actual_resumption_date - timedelta(days=1)
            diff_days = calculate_leave_days(
                start_date=extra_start,
                end_date=extra_end,
                is_continuous=req.leave_type.is_continuous_count,
                closed_holidays=closed_holidays,
            )

        res, _ = ResumptionRecord.objects.update_or_create(
            request=req,
            defaults={
                "expected_date": expected_date,
                "actual_resumption_date": actual_resumption_date,
                "nature": nature,
                "difference_days": diff_days,
                "remarks": remarks,
                "decision": "pending",
            },
        )

        old_state = req.status
        req.status = LeaveState.RESUMPTION_REVIEW_PENDING
        req.current_handler_role = "Dean Academic"
        req.save()

        WorkflowTransition.objects.create(
            request=req,
            from_state=old_state,
            to_state=req.status,
            action="submit_resumption",
            actor_user_id=actor_user_id,
            actor_role="applicant",
            remarks=remarks,
        )

    return res


def review_resumption(
    *,
    actor_user_id: int,
    actor_roles: Sequence[str],
    request_id: int,
    decision: str = "approved",
    remarks: str = "",
) -> ResumptionRecord:
    """Sanctioning Authority reviews resumption and synchronizes balance.

    Implements BR-EL-028, DEC-ELM-001.
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

        if req.status != LeaveState.RESUMPTION_REVIEW_PENDING:
            raise ConflictError(
                f"Request is in state '{req.status}' and not awaiting resumption review."
            )

        if actor_user_id == req.user_id:
            raise PermissionDeniedError("Sanctioning authority cannot review their own resumption.")

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

        res = req.resumption
        old_state = req.status
        actor_role = sorted(matched_roles)[0]

        res.reviewed_by_user_id = actor_user_id
        res.reviewed_at = timezone.now()
        res.decision = decision
        res.save()

        if res.nature == "normal":
            # BR-EL-028: Normal resumption causes no adjustment
            req.actual_days = req.requested_days
            req.reconciliation_status = "synchronized"
            req.status = LeaveState.RESUMPTION_NO_ADJUSTMENT
            action = "resumption_normal_sync"
        elif res.nature == "early":
            # Early return: credit back unavailed days
            credit_days = abs(res.difference_days)
            balance = LeaveBalance.objects.select_for_update().get(
                user_id=req.user_id, leave_type=req.leave_type, year=req.start_date.year
            )
            balance.used_days -= credit_days
            balance.available_days += credit_days
            balance.save()

            LeaveLedgerEntry.objects.create(
                balance=balance,
                entry_type="credit",
                amount=credit_days,
                balance_after=balance.available_days,
                reference_type="resumption",
                reference_id=req.id,
                description="Early resumption credit adjustment",
                performed_by_user_id=actor_user_id,
            )

            req.actual_days = req.requested_days - credit_days
            req.reconciliation_status = "synchronized"
            req.status = LeaveState.RESUMPTION_EARLY_SYNCHRONIZED
            action = "resumption_early_sync"
        else:
            # Late return: extra days to debit
            excess_days = res.difference_days
            balance = LeaveBalance.objects.select_for_update().get(
                user_id=req.user_id, leave_type=req.leave_type, year=req.start_date.year
            )

            if balance.available_days >= excess_days:
                balance.used_days += excess_days
                balance.available_days -= excess_days
                balance.save()

                LeaveLedgerEntry.objects.create(
                    balance=balance,
                    entry_type="debit",
                    amount=excess_days,
                    balance_after=balance.available_days,
                    reference_type="resumption",
                    reference_id=req.id,
                    description="Late resumption debit reconciliation",
                    performed_by_user_id=actor_user_id,
                )

                req.actual_days = req.requested_days + excess_days
                req.reconciliation_status = "synchronized"
                req.status = LeaveState.RESUMPTION_LATE_SYNCHRONIZED
                action = "resumption_late_sync"
            else:
                # DEC-ELM-001 Deficit Boundary: available balance exhausted
                # Do NOT create negative balance, do NOT clamp to zero
                req.excess_days = excess_days
                req.actual_days = req.requested_days + excess_days
                req.requires_admin_review = True
                req.reconciliation_status = "pending_admin_policy"
                req.status = LeaveState.RESUMPTION_LATE_SYNCHRONIZED
                action = "resumption_late_flagged_deficit"

        req.current_handler_role = ""
        req.save()

        WorkflowTransition.objects.create(
            request=req,
            from_state=old_state,
            to_state=req.status,
            action=action,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            remarks=remarks or f"Resumption review outcome: {res.nature}",
        )

    return res


# ==============================================================================
# 4. Authorized Offline Leave Records ? BR-EL-029 (CFR-EL-027, EL-UC-016)
# ==============================================================================


def record_offline_leave(
    *,
    actor_user_id: int,
    actor_roles: Sequence[str],
    employee_user_id: int,
    leave_type_code: str,
    start_date: date,
    end_date: date,
    reason: str,
    offline_sanction_reference: str,
    offline_sanctioned_by: str,
    offline_sanctioned_date: date,
    is_half_day: bool = False,
    half_day_period: str = "",
) -> LeaveRequest:
    """Record already-sanctioned offline leave into the system (BR-EL-029)."""
    admin_roles = {"Leave Administrator", "hr_officer"}
    if not admin_roles.intersection(set(actor_roles)):
        raise PermissionDeniedError(
            "Only authorized leave administrators may record offline leave."
        )

    if not offline_sanction_reference or not offline_sanctioned_by:
        raise BadRequestError(
            "Offline sanction reference and sanctioning authority details are required."
        )

    if start_date > end_date:
        raise BadRequestError("Start date cannot be after end date.")

    try:
        leave_type = LeaveType.objects.get(code=leave_type_code, is_active=True)
    except LeaveType.DoesNotExist as err:
        raise NotFoundError(
            f"Leave type '{leave_type_code}' does not exist or is inactive."
        ) from err

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

    users = directory_contracts.get_users([employee_user_id])
    user_dto = users.get(employee_user_id)
    cadre = user_dto.kind if user_dto else "faculty"
    department = user_dto.department if user_dto else ""

    with transaction.atomic():
        balance = LeaveBalance.objects.select_for_update().get(
            user_id=employee_user_id, leave_type=leave_type, year=start_date.year
        )
        if balance.available_days < requested_days:
            raise ConflictError(
                f"Insufficient balance to record offline leave: {requested_days} requested, "
                f"{balance.available_days} available."
            )

        balance.used_days += requested_days
        balance.available_days -= requested_days
        balance.save()

        app_num = f"OFFLINE-{start_date.year}-{uuid.uuid4().hex[:6].upper()}"
        req = LeaveRequest.objects.create(
            application_number=app_num,
            user_id=employee_user_id,
            cadre=cadre,
            department=department,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            is_half_day=is_half_day,
            half_day_period=half_day_period if is_half_day else "",
            requested_days=requested_days,
            actual_days=requested_days,
            reason=reason,
            status=LeaveState.APPROVED,
            is_offline_record=True,
            offline_sanction_reference=offline_sanction_reference,
            offline_sanctioned_by=offline_sanctioned_by,
            offline_sanctioned_date=offline_sanctioned_date,
            reconciliation_status="synchronized",
        )

        LeaveLedgerEntry.objects.create(
            balance=balance,
            entry_type="debit",
            amount=requested_days,
            balance_after=balance.available_days,
            reference_type="offline_record",
            reference_id=req.id,
            description=f"Offline sanction {offline_sanction_reference}",
            performed_by_user_id=actor_user_id,
        )

        WorkflowTransition.objects.create(
            request=req,
            from_state="none",
            to_state=LeaveState.APPROVED,
            action="record_offline",
            actor_user_id=actor_user_id,
            actor_role="Leave Administrator",
            remarks=(
                f"Offline sanctioned by {offline_sanctioned_by} ref {offline_sanction_reference}"
            ),
        )

    return req
