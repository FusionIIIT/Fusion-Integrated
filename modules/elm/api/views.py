from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status, views
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.selectors.leave_selectors import (
    get_pending_approvals,
    get_pending_substitute_requests,
    get_user_balances,
    get_user_leaves,
)
from modules.elm.services.leave_service import LeaveService

from .serializers import (
    ApproverDecisionSerializer,
    LeaveBalanceSerializer,
    LeaveCreateSerializer,
    LeaveRequestSerializer,
    LeaveWithdrawSerializer,
    SubstituteDecisionSerializer,
    SubstituteReplacementSerializer,
)

MODULE = HasModuleGrant("elm")


def _actor(request):
    return request.principal


class LeaveListCreateView(views.APIView):
    def get_permissions(self):
        permission = "elm.leave.apply" if self.request.method == "POST" else "elm.leave.view_self"
        return [MODULE(), HasPermission(permission)()]

    @extend_schema(
        summary="List the authenticated employee's leave requests",
        tags=["ELM"],
        responses=LeaveRequestSerializer(many=True),
    )
    def get(self, request):
        leaves = get_user_leaves(str(_actor(request).user_id))
        return Response(LeaveRequestSerializer(leaves, many=True).data)

    @extend_schema(
        summary="Submit a leave request",
        tags=["ELM"],
        request=LeaveCreateSerializer,
        responses={201: LeaveRequestSerializer},
    )
    def post(self, request):
        payload = LeaveCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            leave = LeaveService.apply_leave(actor=_actor(request), **payload.validated_data)
        except ValueError as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(LeaveRequestSerializer(leave).data, status=status.HTTP_201_CREATED)


class LeaveBalanceView(views.APIView):
    permission_classes = [MODULE, HasPermission("elm.leave.view_self")]

    @extend_schema(
        summary="List the authenticated employee's leave balances",
        tags=["ELM"],
        responses=LeaveBalanceSerializer(many=True),
    )
    def get(self, request):
        balances = get_user_balances(str(_actor(request).user_id))
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class SubstituteQueueView(views.APIView):
    permission_classes = [MODULE, HasPermission("elm.leave.substitute")]

    @extend_schema(
        summary="List requests assigned to the authenticated substitute",
        tags=["ELM"],
        responses=LeaveRequestSerializer(many=True),
    )
    def get(self, request):
        requests = get_pending_substitute_requests(str(_actor(request).user_id))
        return Response(LeaveRequestSerializer(requests, many=True).data)


class SubstituteDecisionView(views.APIView):
    permission_classes = [MODULE, HasPermission("elm.leave.substitute")]

    @extend_schema(
        summary="Accept or decline a substitute assignment",
        tags=["ELM"],
        request=SubstituteDecisionSerializer,
        responses=LeaveRequestSerializer,
    )
    def post(self, request, pk):
        payload = SubstituteDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave = LeaveService.respond_substitute(
            leave_id=pk,
            actor=_actor(request),
            **payload.validated_data,
        )
        return Response(LeaveRequestSerializer(leave).data)


class ApprovalsQueueView(views.APIView):
    permission_classes = [MODULE, HasPermission("elm.leave.approve")]

    @extend_schema(
        summary="List requests assigned to the active approver role",
        tags=["ELM"],
        responses=LeaveRequestSerializer(many=True),
    )
    def get(self, request):
        leaves = get_pending_approvals(_actor(request).active_role or "")
        return Response(LeaveRequestSerializer(leaves, many=True).data)


class ApproverDecisionView(views.APIView):
    permission_classes = [MODULE, HasPermission("elm.leave.approve")]

    @extend_schema(
        summary="Approve, reject, or forward a leave request",
        tags=["ELM"],
        request=ApproverDecisionSerializer,
        responses=LeaveRequestSerializer,
    )
    def post(self, request, pk):
        payload = ApproverDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        if actor.active_role == "director":
            if payload.validated_data.get("forward_higher", False):
                raise serializers.ValidationError(
                    {"forward_higher": "The Authority stage cannot forward to itself."}
                )
            leave = LeaveService.review_authority(
                leave_id=pk,
                actor=actor,
                approve=payload.validated_data["approve"],
                remarks=payload.validated_data.get("remarks", ""),
            )
        else:
            leave = LeaveService.review_unit_head(
                leave_id=pk,
                actor=actor,
                **payload.validated_data,
            )
        return Response(LeaveRequestSerializer(leave).data)


class LeaveWithdrawView(views.APIView):
    permission_classes = [MODULE, HasPermission("elm.leave.view_self")]

    @extend_schema(
        summary="Withdraw an eligible leave request",
        tags=["ELM"],
        request=LeaveWithdrawSerializer,
        responses=LeaveRequestSerializer,
    )
    def post(self, request, pk):
        payload = LeaveWithdrawSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave = LeaveService.withdraw_leave(
            leave_id=pk, actor=_actor(request), **payload.validated_data
        )
        return Response(LeaveRequestSerializer(leave).data)


class SubstituteReplacementView(views.APIView):
    permission_classes = [MODULE, HasPermission("elm.leave.view_self")]

    @extend_schema(
        summary="Nominate a replacement after substitute decline",
        tags=["ELM"],
        request=SubstituteReplacementSerializer,
        responses=LeaveRequestSerializer,
    )
    def post(self, request, pk):
        payload = SubstituteReplacementSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave = LeaveService.replace_substitute(
            leave_id=pk, actor=_actor(request), **payload.validated_data
        )
        return Response(LeaveRequestSerializer(leave).data)
