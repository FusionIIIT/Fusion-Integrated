"""ELM HTTP endpoints: authorize at the module boundary and delegate writes."""

from rest_framework import serializers, status, views
from rest_framework.response import Response

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.domain.state_machine import WorkflowTransitionError
from modules.elm.models import LeaveRequest
from modules.elm.selectors.leave_selectors import (
    get_pending_authority_approvals,
    get_pending_substitute_requests,
    get_pending_unit_head_approvals,
    get_user_balances,
    get_user_leaves,
)
from modules.elm.services.leave_service import LeaveService

from .serializers import (
    ApproverDecisionSerializer,
    LeaveBalanceAdjustmentSerializer,
    LeaveBalanceSerializer,
    LeaveCreateSerializer,
    LeaveRequestSerializer,
    ReplacementSubstituteSerializer,
    SubstituteDecisionSerializer,
)

MODULE = HasModuleGrant("elm")
APPLY = HasPermission("elm.leave.apply")
VIEW_SELF = HasPermission("elm.leave.view_self")
SUBSTITUTE = HasPermission("elm.leave.substitute")
APPROVE = HasPermission("elm.leave.approve")
SANCTION = HasPermission("elm.leave.sanction")
ADMIN = HasPermission("elm.leave.admin")


def _actor_id(request) -> str:
    return str(request.principal.user_id)


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, LeaveRequest.DoesNotExist):
        raise NotFoundError("Leave request not found.") from exc
    if isinstance(exc, PermissionError):
        raise PermissionDeniedError(str(exc)) from exc
    if isinstance(exc, WorkflowTransitionError):
        raise ConflictError(str(exc)) from exc
    if isinstance(exc, ValueError):
        raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc
    raise exc


class LeaveListCreateView(views.APIView):
    def get_permissions(self):
        action_permission = VIEW_SELF if self.request.method == "GET" else APPLY
        return [MODULE(), action_permission()]

    def get(self, request):
        leaves = get_user_leaves(_actor_id(request))
        return Response(LeaveRequestSerializer(leaves, many=True).data)

    def post(self, request):
        payload = LeaveCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        data.setdefault("duration_days", None)
        try:
            leave = LeaveService.apply_leave(
                applicant_id=_actor_id(request),
                applicant_roles=tuple(request.principal.roles),
                **data,
            )
        except (
            PermissionError,
            ValueError,
            WorkflowTransitionError,
            LeaveRequest.DoesNotExist,
        ) as exc:
            _raise_service_error(exc)
        return Response(LeaveRequestSerializer(leave).data, status=status.HTTP_201_CREATED)


class LeaveBalanceView(views.APIView):
    permission_classes = [MODULE, VIEW_SELF]

    def get(self, request):
        balances = get_user_balances(_actor_id(request))
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class LeaveBalanceAdjustmentView(views.APIView):
    permission_classes = [MODULE, ADMIN]

    def post(self, request):
        payload = LeaveBalanceAdjustmentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            balance = LeaveService.adjust_entitlement(
                **payload.validated_data, actor_id=_actor_id(request),
            )
        except (ValueError, WorkflowTransitionError, LeaveRequest.DoesNotExist) as exc:
            _raise_service_error(exc)
        return Response(LeaveBalanceSerializer(balance).data, status=status.HTTP_200_OK)


class SubstituteQueueView(views.APIView):
    permission_classes = [MODULE, SUBSTITUTE]

    def get(self, request):
        requests = get_pending_substitute_requests(_actor_id(request))
        return Response(LeaveRequestSerializer(requests, many=True).data)


class SubstituteDecisionView(views.APIView):
    permission_classes = [MODULE, SUBSTITUTE]

    def post(self, request, pk):
        payload = SubstituteDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            leave = LeaveService.respond_substitute(
                leave_id=pk,
                substitute_id=_actor_id(request),
                **payload.validated_data,
            )
        except (
            PermissionError,
            ValueError,
            WorkflowTransitionError,
            LeaveRequest.DoesNotExist,
        ) as exc:
            _raise_service_error(exc)
        return Response(LeaveRequestSerializer(leave).data)


class ReplacementSubstituteView(views.APIView):
    permission_classes = [MODULE, APPLY]

    def post(self, request, pk):
        payload = ReplacementSubstituteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            leave = LeaveService.nominate_replacement(
                leave_id=pk,
                applicant_id=_actor_id(request),
                substitute_id=payload.validated_data["substitute_id"],
            )
        except (
            PermissionError,
            ValueError,
            WorkflowTransitionError,
            LeaveRequest.DoesNotExist,
        ) as exc:
            _raise_service_error(exc)
        return Response(LeaveRequestSerializer(leave).data)


class ApprovalsQueueView(views.APIView):
    permission_classes = [MODULE, APPROVE]

    def get(self, request):
        requests = get_pending_unit_head_approvals()
        return Response(LeaveRequestSerializer(requests, many=True).data)


class ApproverDecisionView(views.APIView):
    permission_classes = [MODULE, APPROVE]

    def post(self, request, pk):
        payload = ApproverDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            leave = LeaveService.review_unit_head(
                leave_id=pk,
                approver_id=_actor_id(request),
                **payload.validated_data,
            )
        except (
            PermissionError,
            ValueError,
            WorkflowTransitionError,
            LeaveRequest.DoesNotExist,
        ) as exc:
            _raise_service_error(exc)
        return Response(LeaveRequestSerializer(leave).data)


class AuthorityApprovalsQueueView(views.APIView):
    permission_classes = [MODULE, SANCTION]

    def get(self, request):
        requests = get_pending_authority_approvals()
        return Response(LeaveRequestSerializer(requests, many=True).data)


class AuthorityDecisionView(views.APIView):
    permission_classes = [MODULE, SANCTION]

    def post(self, request, pk):
        payload = ApproverDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            leave = LeaveService.decide_authority(
                leave_id=pk,
                approver_id=_actor_id(request),
                approve=payload.validated_data["approve"],
                remarks=payload.validated_data.get("remarks", ""),
            )
        except (
            PermissionError,
            ValueError,
            WorkflowTransitionError,
            LeaveRequest.DoesNotExist,
        ) as exc:
            _raise_service_error(exc)
        return Response(LeaveRequestSerializer(leave).data)


class LeaveWithdrawView(views.APIView):
    permission_classes = [MODULE, APPLY]

    def post(self, request, pk):
        reason = request.data.get("reason", "")
        if not isinstance(reason, str):
            raise serializers.ValidationError({"reason": ["Must be a string."]})
        try:
            leave = LeaveService.withdraw_leave(
                leave_id=pk,
                user_id=_actor_id(request),
                reason=reason,
            )
        except (
            PermissionError,
            ValueError,
            WorkflowTransitionError,
            LeaveRequest.DoesNotExist,
        ) as exc:
            _raise_service_error(exc)
        return Response(LeaveRequestSerializer(leave).data)
