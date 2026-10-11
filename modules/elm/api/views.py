"""Views for Employee Leave Management API endpoints."""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api import serializers as s
from modules.elm.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    LeaveType,
)

MODULE_GATE = HasModuleGrant("leave_elm")


def _principal_user_id(request) -> int:
    principal = getattr(request, "principal", None)
    return int(getattr(principal, "user_id", getattr(principal, "id", 0)) or 0)


class LeaveTypeListView(generics.ListAPIView):
    serializer_class = s.LeaveTypeSerializer
    permission_classes = [MODULE_GATE, HasPermission("leave_elm.application.view")]
    queryset = LeaveType.objects.filter(is_active=True)


class LeaveBalanceListView(generics.ListAPIView):
    serializer_class = s.LeaveBalanceSerializer
    permission_classes = [MODULE_GATE, HasPermission("leave_elm.balance.view")]

    def get_queryset(self):
        return LeaveBalance.objects.filter(
            user_id=_principal_user_id(self.request)
        ).select_related("leave_type")


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    serializer_class = s.LeaveApplicationSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE_GATE(), HasPermission("leave_elm.application.apply")()]
        return [MODULE_GATE(), HasPermission("leave_elm.application.view")()]

    def get_queryset(self):
        return LeaveApplication.objects.filter(
            user_id=_principal_user_id(self.request)
        ).select_related("leave_type")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        inp = s.LeaveApplicationCreateSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        data = inp.validated_data
        leave_type = get_object_or_404(
            LeaveType, code=data.pop("leave_type_code"), is_active=True
        )
        app = LeaveApplication.objects.create(
            user_id=_principal_user_id(request),
            leave_type=leave_type,
            **data,
        )
        return Response(
            s.LeaveApplicationSerializer(app).data,
            status=status.HTTP_201_CREATED,
        )


class LeaveWithdrawView(APIView):
    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.application.withdraw"),
    ]

    @transaction.atomic
    def post(self, request, pk: int):
        app = get_object_or_404(
            LeaveApplication, pk=pk, user_id=_principal_user_id(request)
        )
        if app.status == "pending":
            app.status = "withdrawn"
            app.save(update_fields=["status", "updated_at"])
        return Response(s.LeaveApplicationSerializer(app).data)


class LeaveApprovalQueueView(generics.ListAPIView):
    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.application.approve"),
    ]

    def get_queryset(self):
        return LeaveApplication.objects.filter(
            status__in=["pending", "recommended"]
        ).select_related("leave_type")


class LeaveApprovalDecisionView(APIView):
    serializer_class = s.LeaveDecisionSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.application.approve"),
    ]

    @transaction.atomic
    def post(self, request, pk: int):
        app = get_object_or_404(LeaveApplication, pk=pk)
        inp = s.LeaveDecisionSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        app.status = inp.validated_data["decision"]
        app.review_remarks = inp.validated_data.get("remarks", "")
        app.reviewer_user_id = _principal_user_id(request)
        app.decided_at = timezone.now()
        app.save(
            update_fields=[
                "status",
                "review_remarks",
                "reviewer_user_id",
                "decided_at",
                "updated_at",
            ]
        )
        return Response(s.LeaveApplicationSerializer(app).data)


class SubstituteResponseView(APIView):
    serializer_class = s.SubstituteDecisionSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.substitute.respond"),
    ]

    @transaction.atomic
    def post(self, request, pk: int):
        app = get_object_or_404(
            LeaveApplication,
            pk=pk,
            substitute_user_id=_principal_user_id(request),
        )
        inp = s.SubstituteDecisionSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        app.substitute_status = inp.validated_data["status"]
        app.save(update_fields=["substitute_status", "updated_at"])
        return Response(s.LeaveApplicationSerializer(app).data)


class HolidayCalendarListView(generics.ListAPIView):
    serializer_class = s.HolidayCalendarSerializer
    permission_classes = [MODULE_GATE, HasPermission("leave_elm.calendar.view")]
    queryset = HolidayCalendar.objects.all()
