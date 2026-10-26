from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.rules import validate_leave_details
from modules.elm.domain.state_machine import (
    WorkflowTransitionError,
    determine_initial_status,
    transition,
)
from modules.elm.models import (
    LeaveActionLog,
    LeaveBalance,
    LeaveRequest,
    LeaveStatus,
    LeaveType,
    SubstituteStatus,
)


class LeaveService:
    ACTIVE_STATUSES = (
        LeaveStatus.PENDING_SUBSTITUTE,
        LeaveStatus.APPLICANT_ACTION_REQUIRED,
        LeaveStatus.PENDING_UNIT_HEAD,
        LeaveStatus.PENDING_AUTHORITY,
        LeaveStatus.APPROVED,
    )

    @staticmethod
    def _has_conflicting_leave(user_id, start_date, end_date, half_day_session=""):
        conflicts = LeaveRequest.objects.filter(
            applicant_user_id=user_id,
            status__in=LeaveService.ACTIVE_STATUSES,
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        if start_date == end_date and half_day_session:
            conflicts = conflicts.exclude(
                is_half_day=True,
                start_date=start_date,
                half_day_session="AN" if half_day_session == "FN" else "FN",
            )
        return conflicts.exists()

    @staticmethod
    def _actor_id(actor) -> str:
        user_id = getattr(actor, "user_id", None)
        if user_id is None:
            raise PermissionDeniedError("An authenticated employee is required.")
        return str(user_id)

    @classmethod
    def _require_permission(cls, actor, permission: str) -> str:
        user_id = cls._actor_id(actor)
        has_permission = getattr(actor, "has_permission", None)
        if has_permission is None or not has_permission(permission):
            raise PermissionDeniedError("You do not have permission for this leave action.")
        return user_id

    @staticmethod
    def _request_for_update(leave_id: str, **scope) -> LeaveRequest:
        try:
            return LeaveRequest.objects.select_for_update().get(id=leave_id, **scope)
        except LeaveRequest.DoesNotExist as exc:
            raise NotFoundError("Leave request was not found.") from exc

    @staticmethod
    def _balance_for_update(request: LeaveRequest) -> LeaveBalance:
        try:
            return LeaveBalance.objects.select_for_update().get(
                user_id=request.applicant_user_id,
                leave_type=request.leave_type,
                year=request.start_date.year,
            )
        except LeaveBalance.DoesNotExist as exc:
            raise ConflictError(
                "No leave balance is configured for this request.",
                code="leave_balance_not_configured",
            ) from exc

    @staticmethod
    def _release_pending(balance: LeaveBalance, duration: Decimal) -> None:
        if balance.pending < duration:
            raise ConflictError(
                "The leave balance does not contain this pending reservation.",
                code="leave_balance_inconsistent",
            )
        balance.pending -= duration

    @staticmethod
    def _log(request, *, actor_id: str, actor_role: str, action: str, remarks: str = ""):
        LeaveActionLog.objects.create(
            leave_request=request,
            actor_user_id=actor_id,
            actor_role=actor_role or "employee",
            action=action,
            remarks=remarks,
        )

    @staticmethod
    @transaction.atomic
    def apply_leave(
        actor,
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
        applicant_id = LeaveService._require_permission(actor, "elm.leave.apply")
        if leave_type not in LeaveType.values:
            raise ValueError("Choose a valid leave category.")

        duration_days = validate_leave_details(
            start_date=start_date,
            end_date=end_date,
            leave_type=leave_type,
            duration_days=duration_days,
            is_half_day=is_half_day,
            half_day_session=half_day_session,
            reason=reason,
            station_leave=station_leave,
            station_leave_address=station_leave_address,
            out_of_station_from=out_of_station_from,
            out_of_station_to=out_of_station_to,
        )
        substitute_id = str(substitute_id or "").strip()
        if substitute_id and substitute_id == applicant_id:
            raise ValueError("You cannot nominate yourself as your substitute.")
        if start_date.year != end_date.year:
            raise ValueError(
                "Requests spanning leave years need year-by-year balance allocation, "
                "which is not configured."
            )
        if LeaveService._has_conflicting_leave(
            applicant_id, start_date, end_date, half_day_session if is_half_day else ""
        ):
            raise ConflictError(
                "You already have pending or approved leave for part of this period.",
                code="leave_overlap",
            )
        if substitute_id and (
            LeaveService._has_conflicting_leave(substitute_id, start_date, end_date)
            or LeaveRequest.objects.filter(
                substitute_user_id=substitute_id,
                status__in=LeaveService.ACTIVE_STATUSES,
                start_date__lte=end_date,
                end_date__gte=start_date,
            ).exists()
        ):
            raise ConflictError(
                "The nominated substitute has a conflicting leave or coverage commitment.",
                code="substitute_unavailable",
            )

        try:
            balance_obj = LeaveBalance.objects.select_for_update().get(
                user_id=applicant_id,
                leave_type=leave_type,
                year=start_date.year,
            )
        except LeaveBalance.DoesNotExist as exc:
            # Never mint entitlement in a request path. Quotas must come from
            # the configured ELM policy and an explicit crediting process.
            raise ConflictError(
                "No leave balance is configured for this leave category and year.",
                code="leave_balance_not_configured",
            ) from exc

        if balance_obj.balance < duration_days:
            raise ConflictError(
                "There is not enough available leave balance for this request.",
                code="insufficient_leave_balance",
            )

        has_sub = bool(substitute_id)
        is_director_applicant = getattr(actor, "active_role", "") == "director"
        initial_status = determine_initial_status(has_sub)
        if is_director_applicant and not has_sub:
            initial_status = LeaveStatus.PENDING_AUTHORITY
        sub_status = SubstituteStatus.PENDING if has_sub else SubstituteStatus.NOT_REQUIRED

        req = LeaveRequest.objects.create(
            applicant_user_id=applicant_id,
            applicant_role=getattr(actor, "active_role", "") or "employee",
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
            current_approver_role=(
                "director" if initial_status == LeaveStatus.PENDING_AUTHORITY else "unit_head"
            ),
        )

        # The locked balance serializes concurrent applications against quota.
        balance_obj.pending += duration_days
        balance_obj.save(update_fields=["pending"])

        LeaveService._log(
            req,
            actor_id=applicant_id,
            actor_role=getattr(actor, "active_role", "") or "employee",
            action="SUBMIT",
            remarks=f"Applied for {duration_days} days {leave_type}",
        )
        return req

    @staticmethod
    @transaction.atomic
    def respond_substitute(leave_id: str, actor, accept: bool, remarks: str = "") -> LeaveRequest:
        substitute_id = LeaveService._require_permission(actor, "elm.leave.substitute")
        req = LeaveService._request_for_update(leave_id, substitute_user_id=substitute_id)
        if req.status != LeaveStatus.PENDING_SUBSTITUTE:
            raise WorkflowTransitionError("Request is not awaiting substitute response.")

        if accept:
            req.substitute_status = SubstituteStatus.ACCEPTED
            req.substitute_remarks = remarks
            next_status = (
                LeaveStatus.PENDING_AUTHORITY
                if req.applicant_role == "director"
                else LeaveStatus.PENDING_UNIT_HEAD
            )
            transition(req, next_status)
            req.current_approver_role = (
                "director" if req.applicant_role == "director" else "unit_head"
            )
            action_code = "SUBSTITUTE_ACCEPT"
        else:
            req.substitute_status = SubstituteStatus.REJECTED
            req.substitute_remarks = remarks
            transition(req, LeaveStatus.APPLICANT_ACTION_REQUIRED)
            req.current_approver_role = ""
            action_code = "SUBSTITUTE_REJECT"

        req.save()
        LeaveService._log(
            req,
            actor_id=substitute_id,
            actor_role=getattr(actor, "active_role", "") or "substitute",
            action=action_code,
            remarks=remarks,
        )
        return req

    @staticmethod
    @transaction.atomic
    def replace_substitute(leave_id: str, actor, substitute_id: str) -> LeaveRequest:
        applicant_id = LeaveService._require_permission(actor, "elm.leave.view_self")
        req = LeaveService._request_for_update(leave_id, applicant_user_id=applicant_id)
        if req.status != LeaveStatus.APPLICANT_ACTION_REQUIRED:
            raise WorkflowTransitionError("Request is not awaiting applicant action.")
        replacement_id = str(substitute_id or "").strip()
        if not replacement_id or replacement_id == applicant_id:
            raise ValueError("Choose another employee as the substitute.")
        if (
            LeaveService._has_conflicting_leave(replacement_id, req.start_date, req.end_date)
            or LeaveRequest.objects.filter(
                substitute_user_id=replacement_id,
                status__in=LeaveService.ACTIVE_STATUSES,
                start_date__lte=req.end_date,
                end_date__gte=req.start_date,
            )
            .exclude(id=req.id)
            .exists()
        ):
            raise ConflictError(
                "The nominated substitute has a conflicting leave or coverage commitment.",
                code="substitute_unavailable",
            )
        req.substitute_user_id = replacement_id
        req.substitute_status = SubstituteStatus.PENDING
        req.substitute_remarks = ""
        transition(req, LeaveStatus.PENDING_SUBSTITUTE)
        req.save(
            update_fields=[
                "substitute_user_id",
                "substitute_status",
                "substitute_remarks",
                "status",
                "updated_at",
            ]
        )
        LeaveService._log(
            req,
            actor_id=applicant_id,
            actor_role=getattr(actor, "active_role", "") or "employee",
            action="SUBSTITUTE_REPLACED",
        )
        return req

    @staticmethod
    @transaction.atomic
    def review_unit_head(
        leave_id: str, actor, approve: bool, remarks: str = "", forward_higher: bool = False
    ) -> LeaveRequest:
        approver_id = LeaveService._require_permission(actor, "elm.leave.approve")
        req = LeaveService._request_for_update(leave_id, current_approver_role="unit_head")
        if req.status != LeaveStatus.PENDING_UNIT_HEAD:
            raise WorkflowTransitionError("Request is not awaiting Unit Head review.")
        if req.applicant_user_id == approver_id:
            raise PermissionDeniedError("You cannot approve your own leave request.")
        if getattr(actor, "active_role", None) not in {
            "unit_head",
            "dean",
            "registrar",
            "leave_admin",
        }:
            raise PermissionDeniedError("Your active role cannot review the Unit Head stage.")
        needs_higher_authority = req.leave_type not in {LeaveType.CASUAL, LeaveType.RESTRICTED}
        if needs_higher_authority:
            req.unit_head_recommendation = "RECOMMENDED" if approve else "NOT_RECOMMENDED"
            transition(req, LeaveStatus.PENDING_AUTHORITY)
            req.current_approver_role = "director"
            action_code = "RECOMMEND" if approve else "NOT_RECOMMEND"
        elif not approve:
            transition(req, LeaveStatus.REJECTED)
            req.rejection_reason = remarks
            req.current_approver_role = ""
            balance_obj = LeaveService._balance_for_update(req)
            LeaveService._release_pending(balance_obj, req.duration_days)
            balance_obj.save(update_fields=["pending"])
            action_code = "REJECT"
        elif forward_higher:
            raise WorkflowTransitionError(
                "Casual and Restricted Holiday requests are decided by the Unit Head."
            )
        else:
            transition(req, LeaveStatus.APPROVED)
            req.current_approver_role = ""
            balance_obj = LeaveService._balance_for_update(req)
            LeaveService._release_pending(balance_obj, req.duration_days)
            balance_obj.availed += req.duration_days
            balance_obj.save(update_fields=["pending", "availed"])
            action_code = "APPROVE"

        req.save()
        LeaveService._log(
            req,
            actor_id=approver_id,
            actor_role=getattr(actor, "active_role", "") or "unit_head",
            action=action_code,
            remarks=remarks,
        )
        return req

    @staticmethod
    @transaction.atomic
    def review_authority(leave_id: str, actor, approve: bool, remarks: str = "") -> LeaveRequest:
        approver_id = LeaveService._require_permission(actor, "elm.leave.approve")
        if getattr(actor, "active_role", None) != "director":
            raise PermissionDeniedError("Only the Sanctioning Authority may review this request.")
        req = LeaveService._request_for_update(leave_id, current_approver_role="director")
        if req.status != LeaveStatus.PENDING_AUTHORITY:
            raise WorkflowTransitionError("Request is not awaiting Authority review.")
        if req.applicant_user_id == approver_id and req.applicant_role != "director":
            raise PermissionDeniedError("You cannot approve your own leave request.")

        balance_obj = LeaveService._balance_for_update(req)
        LeaveService._release_pending(balance_obj, req.duration_days)
        if approve:
            transition(req, LeaveStatus.APPROVED)
            req.current_approver_role = ""
            balance_obj.availed += req.duration_days
            action_code = "AUTHORITY_APPROVE"
        else:
            transition(req, LeaveStatus.REJECTED)
            req.current_approver_role = ""
            req.rejection_reason = remarks
            action_code = "AUTHORITY_REJECT"
        balance_obj.save(update_fields=["pending", "availed"] if approve else ["pending"])
        req.save()
        LeaveService._log(
            req,
            actor_id=approver_id,
            actor_role="director",
            action=action_code,
            remarks=remarks,
        )
        return req

    @staticmethod
    @transaction.atomic
    def withdraw_leave(leave_id: str, actor, reason: str = "") -> LeaveRequest:
        user_id = LeaveService._require_permission(actor, "elm.leave.view_self")
        req = LeaveService._request_for_update(leave_id, applicant_user_id=user_id)
        if req.status in [
            LeaveStatus.APPROVED,
            LeaveStatus.REJECTED,
            LeaveStatus.WITHDRAWN,
            LeaveStatus.CANCELLED,
        ]:
            raise WorkflowTransitionError(f"Cannot withdraw request in {req.status} status.")

        balance_obj = LeaveService._balance_for_update(req)
        LeaveService._release_pending(balance_obj, req.duration_days)
        balance_obj.save(update_fields=["pending"])

        transition(req, LeaveStatus.WITHDRAWN)
        req.current_approver_role = ""
        req.save(update_fields=["status", "current_approver_role"])
        LeaveService._log(
            req,
            actor_id=user_id,
            actor_role=getattr(actor, "active_role", "") or "employee",
            action="WITHDRAW",
            remarks=reason,
        )
        return req
