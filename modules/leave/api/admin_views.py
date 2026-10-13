from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.models import Holiday, LeaveBalance, LeavePolicy, OrgUnit
from modules.leave.selectors import scoping
from modules.leave.services import admin

MODULE = HasModuleGrant("leave")
REQUEST_PERMISSIONS = HasPermission(
    "leave.request.view_self",
    "leave.request.review",
    "leave.request.route",
    "leave.request.sanction",
    "leave.offline.record",
)


def _actor(request):
    return getattr(request, "principal", None)


class ResumptionListView(generics.ListAPIView):
    serializer_class = s.ResumptionSerializer
    permission_classes = [
        MODULE,
        HasPermission("leave.resumption.verify", "leave.request.view_self"),
    ]

    def get_queryset(self):
        return scoping.resumptions_for(_actor(self.request))


class ResumptionReviewView(APIView):
    permission_classes = [MODULE, HasPermission("leave.resumption.verify")]

    @extend_schema(request=s.ResumptionReviewSerializer, responses=s.ResumptionSerializer)
    def post(self, request, pk):
        payload = s.ResumptionReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        resumption_obj = admin.review_resumption(
            request_id=pk, actor=_actor(request), accept=payload.validated_data["accept"]
        )
        return Response(s.ResumptionSerializer(resumption_obj).data)


class BalanceListView(generics.ListAPIView):
    serializer_class = s.LeaveBalanceSerializer
    permission_classes = [MODULE, HasPermission("leave.balance.view")]
    pagination_class = None

    def get_queryset(self):
        actor = _actor(self.request)
        if getattr(self, "swagger_fake_view", False) or actor is None:
            return LeaveBalance.objects.none()
        admin.ensure_balances(user_id=actor.user_id, year=timezone.localdate().year)
        return scoping.balances_for(actor)


class PolicyListView(generics.ListCreateAPIView):
    serializer_class = s.PolicyWriteSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        return LeavePolicy.objects.all()

    def perform_create(self, serializer):
        serializer.save(actor=_actor(self.request))


class UnitListView(generics.ListCreateAPIView):
    serializer_class = s.UnitWriteSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        return OrgUnit.objects.all()

    def perform_create(self, serializer):
        serializer.save(actor=_actor(self.request))


class HolidayListView(generics.ListCreateAPIView):
    serializer_class = s.HolidayWriteSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        return Holiday.objects.all()

    def perform_create(self, serializer):
        serializer.save(actor=_actor(self.request))


class OfflineRecordView(APIView):
    permission_classes = [MODULE, HasPermission("leave.offline.record")]

    @extend_schema(request=s.OfflineRecordSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request):
        payload = s.OfflineRecordSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        request_obj = admin.record_offline_leave(actor=_actor(request), **payload.validated_data)
        return Response(s.LeaveRequestSerializer(request_obj).data, status=status.HTTP_201_CREATED)
