from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave_elm.api import serializers as s
from modules.leave_elm.models import LeaveApplication, LeaveBalance, LeaveStatus

MODULE = HasModuleGrant("leave_elm")

P_VIEW_SELF = "leave_elm.application.view_self"
P_APPLY = "leave_elm.application.apply"
P_WITHDRAW = "leave_elm.application.withdraw"
P_REVIEW = "leave_elm.application.review"
P_SUB_RESPOND = "leave_elm.substitute.respond"


def _actor(request):
    return getattr(request, "principal", None)


class LeaveBalanceListView(generics.ListAPIView):
    serializer_class = s.LeaveBalanceSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get_queryset(self):
        actor = _actor(self.request)
        year = self.request.query_params.get("year", timezone.now().year)
        return LeaveBalance.objects.filter(user_id=actor.user_id, year=year)


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return s.LeaveApplicationCreateSerializer
        return s.LeaveApplicationSerializer

    def get_queryset(self):
        actor = _actor(self.request)
        return LeaveApplication.objects.filter(user_id=actor.user_id).order_by("-created_at")

    def perform_create(self, serializer):
        actor = _actor(self.request)
        sub_id = serializer.validated_data.get("substitute_user_id")
        initial_status = (
            LeaveStatus.PENDING_SUBSTITUTE if sub_id else LeaveStatus.PENDING_APPROVAL
        )
        serializer.save(user_id=actor.user_id, status=initial_status)


class LeaveApplicationDetailView(generics.RetrieveAPIView):
    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [MODULE]
    lookup_field = "pk"
    queryset = LeaveApplication.objects.all()


class LeaveWithdrawView(APIView):
    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    def post(self, request, pk: int):
        actor = _actor(request)
        app = LeaveApplication.objects.get(pk=pk, user_id=actor.user_id)
        if app.status in [LeaveStatus.APPROVED, LeaveStatus.REJECTED, LeaveStatus.WITHDRAWN]:
            return Response(
                {"error": "Cannot withdraw completed request."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        app.status = LeaveStatus.WITHDRAWN
        app.save(update_fields=["status", "updated_at"])
        return Response(s.LeaveApplicationSerializer(app).data)


class SubstituteRespondView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUB_RESPOND)]

    def post(self, request, pk: int):
        actor = _actor(request)
        app = LeaveApplication.objects.get(pk=pk, substitute_user_id=actor.user_id)
        accepted = request.data.get("accepted", True)
        app.substitute_accepted = accepted
        app.status = LeaveStatus.PENDING_APPROVAL if accepted else LeaveStatus.REJECTED
        app.save(update_fields=["substitute_accepted", "status", "updated_at"])
        return Response(s.LeaveApplicationSerializer(app).data)


class LeaveReviewActionView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    def post(self, request, pk: int):
        app = LeaveApplication.objects.get(pk=pk)
        decision = request.data.get("decision", "APPROVED")
        app.status = LeaveStatus.APPROVED if decision == "APPROVED" else LeaveStatus.REJECTED
        app.save(update_fields=["status", "updated_at"])
        return Response(s.LeaveApplicationSerializer(app).data)
