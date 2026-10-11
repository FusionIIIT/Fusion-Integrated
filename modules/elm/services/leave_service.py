from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from modules.elm.models import LeaveRequest, LeaveBalance, LeaveActionLog, LeaveStatus, SubstituteStatus, LeaveType
from modules.elm.domain.state_machine import can_transition, determine_initial_status, WorkflowTransitionError


class LeaveService:
    @staticmethod
    @transaction.atomic
    def apply_leave(
        applicant_id: str,
        leave_type: str,
        start_date,
        end_date,
        duration_days: Decimal,
        reason: str,
        is_half_day: bool = False,
        half_day_session: str = "",
        station_leave: bool = False,
        station_leave_address: str = "",
        out_of_station_from=None,
        out_of_station_to=None,
        substitute_id: str = "",
    ) -> LeaveRequest:
        # 1. Balance validation (SRS-EL-007)
        balance_obj, _ = LeaveBalance.objects.get_or_create(
            user_id=applicant_id,
            leave_type=leave_type,
            year=timezone.now().year,
            defaults={"credited": Decimal("12.0"), "availed": Decimal("0.0"), "pending": Decimal("0.0")},
        )
        if balance_obj.balance < duration_days:
            raise ValueError(f"Insufficient leave balance. Available: {balance_obj.balance}, Requested: {duration_days}")

        has_sub = bool(substitute_id and substitute_id.strip())
        initial_status = determine_initial_status(has_sub)
        sub_status = SubstituteStatus.PENDING if has_sub else SubstituteStatus.NOT_REQUIRED

        req = LeaveRequest.objects.create(
            applicant_user_id=applicant_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            duration_days=duration_days,
            reason=reason,
            is_half_day=is_half_day,
            half_day_session=half_day_session,
            station_leave=station_leave,
            station_leave_address=station_leave_address,
            out_of_station_from=out_of_station_from,
            out_of_station_to=out_of_station_to,
            substitute_user_id=substitute_id.strip() if has_sub else "",
            substitute_status=sub_status,
            status=initial_status,
            current_approver_role="substitute" if has_sub else "unit_head",
        )

        # Lock quota as pending
        balance_obj.pending += duration_days
        balance_obj.save(update_fields=["pending"])

        LeaveActionLog.objects.create(
            leave_request=req,
            actor_user_id=applicant_id,
            actor_role="employee",
            action="SUBMIT",
            remarks=f"Applied for {duration_days} days {leave_type}",
        )
        return req

    @staticmethod
    @transaction.atomic
    def respond_substitute(leave_id: str, substitute_id: str, accept: bool, remarks: str = "") -> LeaveRequest:
        req = LeaveRequest.objects.select_for_update().get(id=leave_id)
        if req.substitute_user_id != substitute_id:
            raise PermissionError("Not the designated substitute.")
        if req.status != LeaveStatus.PENDING_SUBSTITUTE:
            raise WorkflowTransitionError("Request is not awaiting substitute response.")

        if accept:
            req.substitute_status = SubstituteStatus.ACCEPTED
            req.substitute_remarks = remarks
            req.status = LeaveStatus.PENDING_UNIT_HEAD
            req.current_approver_role = "unit_head"
            action_code = "SUBSTITUTE_ACCEPT"
        else:
            req.substitute_status = SubstituteStatus.REJECTED
            req.substitute_remarks = remarks
            req.status = LeaveStatus.REJECTED
            req.rejection_reason = f"Substitute declined: {remarks}"
            action_code = "SUBSTITUTE_REJECT"
            # Release pending balance
            balance_obj = LeaveBalance.objects.get(user_id=req.applicant_user_id, leave_type=req.leave_type, year=req.start_date.year)
            balance_obj.pending -= req.duration_days
            balance_obj.save(update_fields=["pending"])

        req.save()
        LeaveActionLog.objects.create(
            leave_request=req,
            actor_user_id=substitute_id,
            actor_role="substitute",
            action=action_code,
            remarks=remarks,
        )
        return req

    @staticmethod
    @transaction.atomic
    def review_unit_head(leave_id: str, approver_id: str, approve: bool, remarks: str = "", forward_higher: bool = False) -> LeaveRequest:
        req = LeaveRequest.objects.select_for_update().get(id=leave_id)
        if req.status != LeaveStatus.PENDING_UNIT_HEAD:
            raise WorkflowTransitionError("Request is not awaiting Unit Head review.")

        balance_obj = LeaveBalance.objects.get(user_id=req.applicant_user_id, leave_type=req.leave_type, year=req.start_date.year)

        if not approve:
            req.status = LeaveStatus.REJECTED
            req.rejection_reason = remarks
            balance_obj.pending -= req.duration_days
            balance_obj.save(update_fields=["pending"])
            action_code = "REJECT"
        elif forward_higher:
            req.status = LeaveStatus.PENDING_AUTHORITY
            req.current_approver_role = "director"
            action_code = "FORWARD"
        else:
            req.status = LeaveStatus.APPROVED
            balance_obj.pending -= req.duration_days
            balance_obj.availed += req.duration_days
            balance_obj.save(update_fields=["pending", "availed"])
            action_code = "APPROVE"

        req.save()
        LeaveActionLog.objects.create(
            leave_request=req,
            actor_user_id=approver_id,
            actor_role="unit_head",
            action=action_code,
            remarks=remarks,
        )
        return req

    @staticmethod
    @transaction.atomic
    def withdraw_leave(leave_id: str, user_id: str, reason: str = "") -> LeaveRequest:
        req = LeaveRequest.objects.select_for_update().get(id=leave_id)
        if req.applicant_user_id != user_id:
            raise PermissionError("Cannot withdraw another employee's request.")
        if req.status in [LeaveStatus.APPROVED, LeaveStatus.REJECTED, LeaveStatus.WITHDRAWN, LeaveStatus.CANCELLED]:
            raise WorkflowTransitionError(f"Cannot withdraw request in {req.status} status.")

        balance_obj = LeaveBalance.objects.get(user_id=req.applicant_user_id, leave_type=req.leave_type, year=req.start_date.year)
        balance_obj.pending -= req.duration_days
        balance_obj.save(update_fields=["pending"])

        req.status = LeaveStatus.WITHDRAWN
        req.save(update_fields=["status"])
        LeaveActionLog.objects.create(
            leave_request=req,
            actor_user_id=user_id,
            actor_role="employee",
            action="WITHDRAW",
            remarks=reason,
        )
        return req
