from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import LeaveBalanceSerializer, LeaveRequestCreateSerializer, LeaveRequestSerializer
from modules.elm.models import LeaveAction, LeaveApplication, LeaveBalance

MODULE = HasModuleGrant("leave_elm")


def current_user_id(request):
    principal = getattr(request, "principal", None)
    if principal is None or getattr(principal, "user_id", None) is None:
        raise PermissionDenied("Cannot identify current Fusion user.")
    return int(principal.user_id)


class LeaveRequestListView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.view_self", "leave_elm.request.apply")]

    def get(self, request):
        items = LeaveApplication.objects.filter(user_id=current_user_id(request))
        return Response(LeaveRequestSerializer(items, many=True).data)

    def post(self, request):
        serializer = LeaveRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        obj = LeaveApplication.objects.create(user_id=current_user_id(request), **data)
        LeaveAction.objects.create(application=obj, actor_user_id=obj.user_id, action="submitted")
        return Response(LeaveRequestSerializer(obj).data, status=status.HTTP_201_CREATED)


class LeaveQueueView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.review")]

    def get(self, request):
        items = LeaveApplication.objects.filter(status="pending")
        return Response(LeaveRequestSerializer(items, many=True).data)


class LeaveDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.review")]

    def post(self, request, pk):
        obj = LeaveApplication.objects.filter(pk=pk).first()
        if obj is None:
            raise NotFound("Leave request not found.")
        if obj.status != "pending":
            return Response({"detail": "This request is no longer pending."}, status=400)
        decision = request.data.get("decision")
        if decision not in ("approve", "reject"):
            return Response({"detail": "decision must be approve or reject."}, status=400)
        obj.status = "approved" if decision == "approve" else "rejected"
        obj.decision_note = request.data.get("note", "")
        obj.save(update_fields=["status", "decision_note"])
        LeaveAction.objects.create(application=obj, actor_user_id=current_user_id(request), action=decision, note=obj.decision_note)
        return Response(LeaveRequestSerializer(obj).data)


class LeaveBalanceListView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.balance.view_self")]

    def get(self, request):
        balances = LeaveBalance.objects.filter(user_id=current_user_id(request), year=timezone.localdate().year)
        return Response(LeaveBalanceSerializer(balances, many=True).data)
