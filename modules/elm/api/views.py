from django.http import Http404
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    LeaveApprovalDecisionSerializer,
    LeaveApprovalTaskSerializer,
    LeaveBalanceEventSerializer,
    LeaveBalanceSummarySerializer,
    LeaveRequestEventSerializer,
    LeaveRequestSerializer,
    LeaveRequestSubmissionSerializer,
    LeaveSubstituteReplacementSerializer,
    LeaveSubstituteResponseSerializer,
)
from modules.elm.models import LeaveRequestEvent
from modules.elm.selectors.balance_selector import LeaveBalanceSelector
from modules.elm.selectors.request_selector import (
    LeaveApprovalTaskSelector,
    LeaveRequestSelector,
)
from modules.elm.services.leave_request_service import LeaveRequestService

MODULE = HasModuleGrant("leave")
P_SUBMIT = "leave.request.create"
P_VIEW_SELF = "leave.request.view_self"
P_WITHDRAW = "leave.request.delete"
P_SUBSTITUTE = "leave.substitute.respond"
P_APPROVE = "leave.request.approve"


def _actor(request):
    return request.principal


class LeaveBalanceSummaryView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        year_value = request.query_params.get("year")
        try:
            year = int(year_value) if year_value else None
        except ValueError as exc:
            raise serializers.ValidationError(
                {"year": "Enter a valid calendar year."}
            ) from exc
        if year is not None and not 1900 <= year <= 9999:
            raise serializers.ValidationError(
                {"year": "Enter a year between 1900 and 9999."}
            )
        balances = LeaveBalanceSelector.for_user(
            user_id=_actor(request).user_id,
            employee_kind=_actor(request).kind.lower(),
            year=year,
        )
        return Response({
            "results": LeaveBalanceSummarySerializer(
                balances, many=True
            ).data,
        })


class LeaveBalanceHistoryView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        leave_type_code = request.query_params.get("leave_type_code")
        valid_codes = dict(LeaveRequestSerializer.Meta.model.LEAVE_CHOICES)
        if leave_type_code and leave_type_code not in valid_codes:
            raise serializers.ValidationError(
                {"leave_type_code": "Choose a supported leave type."}
            )
        events = LeaveBalanceSelector.history_for_user(
            user_id=_actor(request).user_id,
            leave_type_code=leave_type_code,
        )
        return Response({
            "results": LeaveBalanceEventSerializer(events, many=True).data,
        })


class LeaveRequestSubmitView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUBMIT)]

    def post(self, request):
        payload = LeaveRequestSubmissionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            leave_request = LeaveRequestService.submit_request(
                user_id=_actor(request).user_id,
                employee_kind=_actor(request).kind.lower(),
                active_role=_actor(request).active_role,
                actor_roles=_actor(request).roles,
                **payload.validated_data,
            )
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc
        return Response(
            LeaveRequestSerializer(leave_request).data,
            status=status.HTTP_201_CREATED,
        )


class MyLeaveRequestsView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        rows = LeaveRequestSelector.for_user(_actor(request).user_id)
        return Response({
            "results": LeaveRequestSerializer(rows, many=True).data,
        })


class LeaveRequestWithdrawView(APIView):
    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    def post(self, request, request_id):
        try:
            leave_request = LeaveRequestService.withdraw_request(
                request_id=request_id,
                user_id=_actor(request).user_id,
            )
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc
        return Response(LeaveRequestSerializer(leave_request).data)


class LeaveRequestHistoryView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request, request_id):
        leave_request = LeaveRequestSelector.get_for_user(
            request_id=request_id,
            user_id=_actor(request).user_id,
        )
        if leave_request is None:
            raise Http404
        events = LeaveRequestEvent.objects.filter(
            request=leave_request
        ).order_by("created_at", "id")
        return Response(LeaveRequestEventSerializer(events, many=True).data)


class LeaveSubstituteResponseView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    def post(self, request, request_id):
        payload = LeaveSubstituteResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            leave_request = LeaveRequestService.respond_to_substitute(
                request_id=request_id,
                actor_user_id=_actor(request).user_id,
                **payload.validated_data,
            )
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc
        return Response(LeaveRequestSerializer(leave_request).data)


class LeaveSubstituteReplacementView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUBMIT)]

    def post(self, request, request_id):
        payload = LeaveSubstituteReplacementSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            leave_request = LeaveRequestService.replace_substitute(
                request_id=request_id,
                user_id=_actor(request).user_id,
                new_substitute_user_id=payload.validated_data["substitute_user_id"],
            )
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc
        return Response(LeaveRequestSerializer(leave_request).data)


class LeaveSubstituteTasksView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    def get(self, request):
        tasks = LeaveRequestSelector.pending_substitute_for_user(
            _actor(request).user_id
        )
        return Response({
            "results": LeaveRequestSerializer(tasks, many=True).data,
        })


class LeaveApprovalsView(APIView):
    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    def get(self, request):
        tasks = LeaveApprovalTaskSelector.pending_for_user(_actor(request).user_id)
        return Response({"results": LeaveApprovalTaskSerializer(tasks, many=True).data})


class LeaveRequestDecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    def post(self, request, request_id):
        payload = LeaveApprovalDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            leave_request = LeaveRequestService.decide_request(
                request_id=request_id,
                actor_user_id=_actor(request).user_id,
                **payload.validated_data,
            )
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc
        return Response(LeaveRequestSerializer(leave_request).data)
