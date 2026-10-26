"""HTTP endpoints for the ELM module."""

from datetime import date

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import ConflictError
from fusion_auth.permissions import HasModuleGrant
from modules.elm.api.serializers import (
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    RestrictedHolidaySerializer,
)
from modules.elm.models import LeaveBalance, LeaveRequest, RestrictedHoliday
from modules.elm.services.approvals import decide_leave_request
from modules.elm.services.leave_requests import submit_leave_request
from modules.elm.services.withdrawals import withdraw_leave_request

MODULE = HasModuleGrant("elm")


def _employee_id(request):
    principal = getattr(request, "principal", None)
    employee_id = getattr(principal, "user_id", None)
    if employee_id is None:
        employee_id = getattr(principal, "id", None)
    if employee_id is None:
        raise ValidationError({"detail": "Unable to resolve employee identity."})
    return int(employee_id)


class LeaveRequestListCreateView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        requests = LeaveRequest.objects.filter(
            employee_id=_employee_id(request)
        ).order_by("-created_at")
        return Response(LeaveRequestSerializer(requests, many=True).data)

    def post(self, request):
        serializer = LeaveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("employee_id", None)
        try:
            leave_request = submit_leave_request(
                employee_id=_employee_id(request),
                **data,
            )
        except ConflictError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            LeaveRequestSerializer(leave_request).data,
            status=status.HTTP_201_CREATED,
        )


class LeaveBalanceListView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        year_value = request.query_params.get("year", date.today().year)
        try:
            year = int(year_value)
        except (TypeError, ValueError):
            raise ValidationError({"year": "Must be a valid year."}) from None

        balances = LeaveBalance.objects.filter(
            employee_id=_employee_id(request),
            year=year,
        ).order_by("leave_category")
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class RestrictedHolidayListView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        holidays = RestrictedHoliday.objects.filter(is_published=True)
        station_id = request.query_params.get("station_id")
        if station_id:
            try:
                holidays = holidays.filter(station_id=int(station_id))
            except ValueError:
                raise ValidationError({"station_id": "Must be a number."}) from None
        return Response(
            RestrictedHolidaySerializer(holidays, many=True).data
        )



class LeaveApprovalDecisionView(APIView):
    permission_classes = [MODULE]

    def post(self, request, request_id):
        principal = getattr(request, "principal", None)
        if principal is None:
            return Response({"detail": "Authentication required."},
                            status=status.HTTP_401_UNAUTHORIZED)

        decision = request.data.get("decision")
        comments = request.data.get("comments", "")

        if decision not in ("APPROVED", "REJECTED"):
            raise ValidationError({
                "decision": "Must be APPROVED or REJECTED."
            })
        if not isinstance(comments, str):
            raise ValidationError({"comments": "Must be a string."})

        try:
            leave = decide_leave_request(
                request_id=request_id,
                actor_id=int(principal.user_id),
                decision=decision,
                comments=comments,
                permissions=getattr(principal, "permissions", ()),
            )
        except ConflictError as exc:
            code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else (
                status.HTTP_403_FORBIDDEN
                if exc.code in ("approval_forbidden", "self_approval")
                else status.HTTP_409_CONFLICT
            )
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=code,
            )

        return Response(LeaveRequestSerializer(leave).data)


class LeaveRequestWithdrawView(APIView):
    permission_classes = [MODULE]

    def post(self, request, request_id):
        try:
            leave = withdraw_leave_request(
                request_id=request_id,
                actor_id=_employee_id(request),
            )
        except ConflictError as exc:
            code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else (
                status.HTTP_403_FORBIDDEN
                if exc.code == "withdraw_forbidden"
                else status.HTTP_409_CONFLICT
            )
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=code,
            )
        return Response(LeaveRequestSerializer(leave).data)
