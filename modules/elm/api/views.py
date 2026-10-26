from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    LeaveBalanceSerializer,
    LeaveRequestCreateSerializer,
    LeaveRequestSerializer,
)
from modules.elm.domain.errors import (
    ApplicationNotFound,
    LeaveRuleError,
    SelfReviewNotAllowed,
)
from modules.elm.models import LeaveApplication, LeaveBalance
from modules.elm.services.leave import apply_for_leave, decide_leave

MODULE = HasModuleGrant("leave_elm")


def current_user_id(request):
    principal = getattr(request, "principal", None)
    if principal is None or getattr(principal, "user_id", None) is None:
        raise PermissionDenied("Cannot identify current Fusion user.")
    return int(principal.user_id)


class LeaveRequestListView(APIView):
    permission_classes = [
        MODULE,
        HasPermission(
            "leave_elm.request.view_self",
            "leave_elm.request.apply",
        ),
    ]

    def get(self, request):
        items = LeaveApplication.objects.filter(user_id=current_user_id(request))
        return Response(LeaveRequestSerializer(items, many=True).data)

    def post(self, request):
        serializer = LeaveRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            obj = apply_for_leave(current_user_id(request), serializer.validated_data)
        except LeaveRuleError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(LeaveRequestSerializer(obj).data, status=status.HTTP_201_CREATED)


class LeaveQueueView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.review")]

    def get(self, request):
        items = LeaveApplication.objects.filter(status="pending")
        return Response(LeaveRequestSerializer(items, many=True).data)


class LeaveDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.review")]

    def post(self, request, pk):
        decision = request.data.get("decision")
        if decision not in ("approve", "reject"):
            return Response({"detail": "decision must be approve or reject."}, status=400)
        try:
            obj = decide_leave(
                pk,
                current_user_id(request),
                decision,
                request.data.get("note", ""),
            )
        except SelfReviewNotAllowed as exc:
            raise PermissionDenied(str(exc)) from exc
        except ApplicationNotFound as exc:
            raise NotFound(str(exc)) from exc
        except LeaveRuleError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(LeaveRequestSerializer(obj).data)


class LeaveBalanceListView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.balance.view_self")]

    def get(self, request):
        balances = LeaveBalance.objects.filter(
            user_id=current_user_id(request),
            year=timezone.localdate().year,
        )
        return Response(LeaveBalanceSerializer(balances, many=True).data)
