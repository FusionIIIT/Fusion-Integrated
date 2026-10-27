"""ELM API views using Fusion authentication and RBAC permissions."""

from datetime import date
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, IsAuthenticatedPrincipal
from modules.elm.models import LeaveType, LeaveRequest, LeaveBalance, SubstituteResponse, LeaveRequestTransition
from modules.elm.domain.state_machine import (
    Status,
    validate_transition,
    InvalidTransition,
    PermissionDenied,
)
from modules.elm.services.balances import (
    calculate_leave_days,
    debit_leave_balance,
    restore_leave_balance,
)


class LeaveTypeListView(APIView):
    """List available active leave categories (CL, RH, SCL, EL, VL, COL)."""
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]

    def get(self, request):
        types = LeaveType.objects.filter(is_active=True).values("id", "code", "name", "description")
        return Response(list(types))


class LeaveRequestListView(APIView):
    """List or apply for leave requests."""
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]

    def get(self, request):
        p = request.principal
        # Employees see their own requests; Unit Heads/Establishment can view requests within scope
        if p.has_permission("leave_elm.leave_request.view"):
            requests = LeaveRequest.objects.all().values(
                "id", "employee_user_id", "leave_type__code", "start_date", "end_date",
                "half_day_type", "reason", "status", "is_station_leave", "station_leave_address",
                "station_leave_contact", "created_at"
            )
        else:
            requests = LeaveRequest.objects.filter(employee_user_id=p.user_id).values(
                "id", "employee_user_id", "leave_type__code", "start_date", "end_date",
                "half_day_type", "reason", "status", "is_station_leave", "station_leave_address",
                "station_leave_contact", "created_at"
            )
        return Response(list(requests))

    def post(self, request):
        p = request.principal
        if not p.has_permission("leave_elm.leave_request.create"):
            return Response(
                {"detail": "You do not have permission to apply for leave."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data
        leave_type_id = data.get("leave_type_id")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        reason = data.get("reason", "")
        half_day_type = data.get("half_day_type", "FULL")
        is_station = data.get("is_station_leave", False)
        station_address = data.get("station_leave_address", "") if is_station else ""
        station_contact = data.get("station_leave_contact", "") if is_station else ""
        substitute_user_id = data.get("substitute_user_id")

        if not leave_type_id or not start_date or not end_date:
            return Response(
                {"detail": "leave_type_id, start_date, and end_date are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        s_date = date.fromisoformat(str(start_date)) if isinstance(start_date, str) else start_date
        e_date = date.fromisoformat(str(end_date)) if isinstance(end_date, str) else end_date
        if s_date > e_date:
            return Response(
                {"detail": "Start date cannot be after end date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # BR-EL-012: Check non-overlap with active pending/approved leaves
        active_reqs = LeaveRequest.objects.filter(
            employee_user_id=p.user_id,
            start_date__lte=e_date,
            end_date__gte=s_date,
        ).exclude(status__in=[Status.WITHDRAWN.value, Status.REJECTED.value, Status.CANCELLED.value])

        for existing in active_reqs:
            is_half_day_exception = (
                s_date == e_date
                and existing.start_date == existing.end_date == s_date
                and existing.leave_type.code == "CL"
                and {existing.half_day_type, half_day_type} == {"FIRST_HALF", "SECOND_HALF"}
            )
            if not is_half_day_exception:
                return Response(
                    {"detail": "An active leave request already overlaps this interval (BR-EL-012)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # BR-EL-014: Substitute eligibility validation
        if substitute_user_id:
            try:
                sub_id_int = int(substitute_user_id)
            except (ValueError, TypeError):
                return Response(
                    {"detail": "substitute_user_id must be a valid integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if sub_id_int == p.user_id:
                return Response(
                    {"detail": "Substitute cannot be the applicant (BR-EL-014)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            initial_status = Status.AWAITING_SUBSTITUTE_RESPONSE.value
        else:
            initial_status = Status.PENDING_UNIT_HEAD.value

        with transaction.atomic():
            req = LeaveRequest.objects.create(
                employee_user_id=p.user_id,
                leave_type_id=leave_type_id,
                start_date=s_date,
                end_date=e_date,
                half_day_type=half_day_type,
                reason=reason,
                is_station_leave=is_station,
                station_leave_address=station_address,
                station_leave_contact=station_contact,
                status=initial_status,
            )
            if substitute_user_id:
                SubstituteResponse.objects.create(
                    leave_request=req,
                    substitute_user_id=sub_id_int,
                    status="PENDING",
                )
            LeaveRequestTransition.objects.create(
                leave_request=req,
                from_status=Status.DRAFT.value,
                to_status=initial_status,
                actor_user_id=p.user_id,
                reason="Initial leave application submission",
            )

        return Response({"id": req.id, "status": req.status}, status=status.HTTP_201_CREATED)


class LeaveRequestTransitionView(APIView):
    """Validate and execute state transition on a leave request."""
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]

    def post(self, request, pk):
        try:
            leave_req = LeaveRequest.objects.select_related("leave_type").get(pk=pk)
        except LeaveRequest.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        target_status_val = request.data.get("target_status")
        try:
            target_status = Status(target_status_val)
            current_status = Status(leave_req.status)
        except ValueError:
            return Response({"detail": f"Invalid status: {target_status_val}"}, status=status.HTTP_400_BAD_REQUEST)

        p = request.principal
        # Ownership check for employee actions like withdrawal or cancel request
        if target_status in (Status.WITHDRAWN, Status.CANCELLATION_PENDING_UNIT_HEAD):
            if leave_req.employee_user_id != p.user_id:
                return Response(
                    {"detail": "Only the applicant can withdraw or request cancellation."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # BR-EL-023: Cancellation may only be requested before leave start date
        if target_status == Status.CANCELLATION_PENDING_UNIT_HEAD:
            if leave_req.start_date <= timezone.now().date():
                return Response(
                    {"detail": "Approved leave may be cancelled only before its start date (BR-EL-023)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Map user's permissions to state machine check
        user_perms = set(p.permissions) if p else set()
        user_perms.update({perm.replace("leave_elm.", "elm.") for perm in user_perms if perm.startswith("leave_elm.")})

        try:
            validate_transition(current_status, target_status, frozenset(user_perms))
        except InvalidTransition as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

        transition_reason = request.data.get("reason", "")
        with transaction.atomic():
            leave_req.status = target_status.value
            leave_req.save(update_fields=["status"])

            # Create immutable audit transition record
            LeaveRequestTransition.objects.create(
                leave_request=leave_req,
                from_status=current_status.value,
                to_status=target_status.value,
                actor_user_id=p.user_id,
                reason=transition_reason,
            )

            # Deduct balance on approval (BR-EL-010, BR-EL-023)
            if target_status == Status.APPROVED:
                days = calculate_leave_days(
                    leave_req.leave_type.code,
                    leave_req.start_date,
                    leave_req.end_date,
                    leave_req.half_day_type,
                )
                debit_leave_balance(
                    leave_req.employee_user_id,
                    leave_req.leave_type.code,
                    days,
                    leave_req.start_date.year,
                )

            # Restore balance on approved cancellation (BR-EL-023)
            elif target_status == Status.CANCELLED:
                days = calculate_leave_days(
                    leave_req.leave_type.code,
                    leave_req.start_date,
                    leave_req.end_date,
                    leave_req.half_day_type,
                )
                restore_leave_balance(
                    leave_req.employee_user_id,
                    leave_req.leave_type.code,
                    days,
                    leave_req.start_date.year,
                )

        return Response({"id": leave_req.id, "status": leave_req.status})


class LeaveBalanceListView(APIView):
    """View leave balances for the authenticated employee."""
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]

    def get(self, request):
        p = request.principal
        balances = LeaveBalance.objects.filter(employee_user_id=p.user_id).values(
            "leave_type__code", "year", "credited", "used"
        )
        return Response(list(balances))


class SubstituteResponseListView(APIView):
    """List pending responsibility coverage requests for nominated substitute."""
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]

    def get(self, request):
        p = request.principal
        subs = SubstituteResponse.objects.filter(substitute_user_id=p.user_id).values(
            "id", "leave_request_id", "status", "remarks", "responded_at"
        )
        return Response(list(subs))


class SubstituteResponseRespondView(APIView):
    """Respond (Accept or Decline) to substitute coverage request (BR-EL-015, CW-EL-01)."""
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]

    def post(self, request, pk):
        p = request.principal
        if not p.has_permission("leave_elm.substitute.respond"):
            return Response(
                {"detail": "You do not have permission to respond as substitute."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            sub = SubstituteResponse.objects.select_related("leave_request").get(pk=pk)
        except SubstituteResponse.DoesNotExist:
            return Response({"detail": "Substitute request not found."}, status=status.HTTP_404_NOT_FOUND)

        if sub.substitute_user_id != p.user_id:
            return Response(
                {"detail": "Only the nominated substitute can respond to this request."},
                status=status.HTTP_403_FORBIDDEN,
            )

        resp_status = request.data.get("status")
        if resp_status not in ("ACCEPTED", "DECLINED"):
            return Response(
                {"detail": "Status must be either 'ACCEPTED' or 'DECLINED'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        remarks = request.data.get("remarks", "")
        with transaction.atomic():
            sub.status = resp_status
            sub.remarks = remarks
            sub.responded_at = timezone.now()
            sub.save(update_fields=["status", "remarks", "responded_at"])

            leave_req = sub.leave_request
            curr_status = Status(leave_req.status)

            if resp_status == "ACCEPTED":
                # Check if all nominated substitutes accepted
                pending_count = SubstituteResponse.objects.filter(
                    leave_request=leave_req,
                    status="PENDING",
                ).count()
                if pending_count == 0:
                    new_status = Status.PENDING_UNIT_HEAD
                    leave_req.status = new_status.value
                    leave_req.save(update_fields=["status"])
                    LeaveRequestTransition.objects.create(
                        leave_request=leave_req,
                        from_status=curr_status.value,
                        to_status=new_status.value,
                        actor_user_id=p.user_id,
                        reason=f"Substitute accepted responsibility: {remarks}",
                    )
            elif resp_status == "DECLINED":
                # BR-EL-015: Decline transitions request to APPLICANT_ACTION_REQUIRED
                new_status = Status.APPLICANT_ACTION_REQUIRED
                leave_req.status = new_status.value
                leave_req.save(update_fields=["status"])
                LeaveRequestTransition.objects.create(
                    leave_request=leave_req,
                    from_status=curr_status.value,
                    to_status=new_status.value,
                    actor_user_id=p.user_id,
                    reason=f"Substitute declined responsibility: {remarks}",
                )

        return Response({"id": sub.id, "status": sub.status, "request_status": leave_req.status})
