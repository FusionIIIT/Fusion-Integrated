"""REST API endpoints for ELM module."""
from datetime import date

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission, IsAuthenticatedPrincipal
from modules.elm.api.serializers import (
    HolidayCalendarSerializer,
    LeaveApplicationCreateSerializer,
    LeaveBalanceSerializer,
    LeaveExtensionCreateSerializer,
    LeaveRequestSerializer,
    ResumptionSubmitSerializer,
    SanctionDecisionSerializer,
    SubstituteResponseSerializer,
    UnitHeadReviewSerializer,
)
from modules.elm.models.holidays import HolidayCalendar
from modules.elm.selectors import leaves as selectors
from modules.elm.services import applications as app_service
from modules.elm.services import workflows as wf_service


def _get_current_user_id(request) -> int:
    principal = getattr(request, "principal", None)
    if principal and getattr(principal, "user_id", None):
        return int(principal.user_id)
    if getattr(request.user, "id", None):
        return int(request.user.id)
    return 1  # Fallback for dev/unauthenticated local testing


class MyLeavesView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get(self, request):
        uid = _get_current_user_id(request)
        leaves = selectors.get_user_leaves(uid)
        return Response(LeaveRequestSerializer(leaves, many=True).data)

    def post(self, request):
        uid = _get_current_user_id(request)
        serializer = LeaveApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            req = app_service.apply_for_leave(
                user_id=uid,
                **serializer.validated_data,
            )
            return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveDetailWithdrawView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get(self, request, pk: int):
        uid = _get_current_user_id(request)
        leave = selectors.get_user_leave_detail(uid, pk)
        if not leave:
            return Response({"error": "Leave not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(LeaveRequestSerializer(leave).data)

    def delete(self, request, pk: int):
        """Immediate withdrawal (EL-UC-007, BR-EL-022)."""
        uid = _get_current_user_id(request)
        try:
            req = app_service.withdraw_leave_application(uid, pk)
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveCancellationView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm"), HasPermission("elm.leave.cancel")]

    def post(self, request, pk: int):
        uid = _get_current_user_id(request)
        try:
            req = wf_service.request_cancellation(uid, pk)
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveResumptionView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm"), HasPermission("elm.leave.resume")]

    def post(self, request, pk: int):
        uid = _get_current_user_id(request)
        serializer = ResumptionSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            req = wf_service.submit_resumption(
                user_id=uid,
                leave_id=pk,
                actual_date=serializer.validated_data["actual_date"],
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveExtensionView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("elm"),
        HasPermission("elm.leave.extend"),
    ]

    def post(self, request, pk: int):
        uid = _get_current_user_id(request)
        serializer = LeaveExtensionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            extension = app_service.request_leave_extension(
                user_id=uid,
                leave_id=pk,
                **serializer.validated_data,
            )
            return Response(LeaveRequestSerializer(extension).data, status=status.HTTP_201_CREATED)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class ExtensionSubstituteView(APIView):
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("elm"),
        HasPermission("elm.leave.extend"),
    ]

    def post(self, request, pk: int):
        uid = _get_current_user_id(request)
        substitute_user_id = request.data.get("substitute_user_id")
        try:
            substitute_user_id = int(substitute_user_id)
        except (TypeError, ValueError):
            return Response(
                {"error": "substitute_user_id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            extension = wf_service.nominate_replacement_substitute(uid, pk, substitute_user_id)
            return Response(LeaveRequestSerializer(extension).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class MyBalancesView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get(self, request):
        uid = _get_current_user_id(request)
        year = int(request.query_params.get("year", date.today().year))
        balances = selectors.get_user_balances(uid, year)
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class SubstituteQueueView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm"), HasPermission("elm.leave.substitute")]

    def get(self, request):
        uid = _get_current_user_id(request)
        pending = selectors.get_substitute_pending_requests(uid)
        return Response(LeaveRequestSerializer(pending, many=True).data)

    def post(self, request, pk: int):
        uid = _get_current_user_id(request)
        serializer = SubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            req = wf_service.respond_substitute(
                substitute_user_id=uid,
                leave_id=pk,
                accepted=serializer.validated_data["accepted"],
            )
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class UnitHeadReviewView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm"), HasPermission("elm.leave.review")]

    def get(self, request):
        uid = _get_current_user_id(request)
        pending = selectors.get_unit_head_pending_requests(uid)
        return Response(LeaveRequestSerializer(pending, many=True).data)

    def post(self, request, pk: int):
        uid = _get_current_user_id(request)
        serializer = UnitHeadReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            req = wf_service.review_unit_head(
                unit_head_user_id=uid,
                leave_id=pk,
                decision=serializer.validated_data["decision"],
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class SanctionDecisionView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm"), HasPermission("elm.leave.sanction")]

    def get(self, request):
        uid = _get_current_user_id(request)
        pending = selectors.get_sanctioning_authority_pending_requests(uid)
        return Response(LeaveRequestSerializer(pending, many=True).data)

    def post(self, request, pk: int):
        uid = _get_current_user_id(request)
        serializer = SanctionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            req = wf_service.make_sanction_decision(
                authority_user_id=uid,
                leave_id=pk,
                approve=serializer.validated_data["approve"],
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class HolidayCalendarView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm")]

    def get(self, request):
        year = int(request.query_params.get("year", date.today().year))
        holidays = HolidayCalendar.objects.filter(year=year, is_published=True).order_by("date")
        return Response(HolidayCalendarSerializer(holidays, many=True).data)
