from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    LeaveApplicationSerializer,
    LeaveBalanceSerializer,
    ReviewApplicationSerializer,
    SubstituteNominationSerializer,
    SubstituteResponseSerializer,
)
from modules.elm.models import LeaveApplication, LeaveBalance, SubstituteNomination
from modules.elm.services import applications


class LeaveBalanceListView(APIView):
    permission_classes = [
        HasModuleGrant("elm"),
        HasPermission("elm.balance.view"),
    ]

    @extend_schema(responses=LeaveBalanceSerializer(many=True))
    def get(self, request):
        rows = LeaveBalance.objects.filter(employee_id=request.user.user_id)
        return Response(LeaveBalanceSerializer(rows, many=True).data)


class LeaveApplicationListCreateView(APIView):
    permission_classes = [
        HasModuleGrant("elm"),
        HasPermission("elm.application.create"),
    ]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        rows = LeaveApplication.objects.filter(applicant_id=request.user.user_id)
        return Response(LeaveApplicationSerializer(rows, many=True).data)

    @extend_schema(
        request=LeaveApplicationSerializer,
        responses={201: LeaveApplicationSerializer},
    )
    def post(self, request):
        serializer = LeaveApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = applications.submit_leave_application(
                applicant_id=request.user.user_id,
                leave_type=serializer.validated_data["leave_type"],
                start_date=serializer.validated_data["start_date"],
                end_date=serializer.validated_data["end_date"],
                reason=serializer.validated_data.get("reason", ""),
                station_leave_details=serializer.validated_data.get("station_leave_details", ""),
            )
            return Response(
                LeaveApplicationSerializer(application).data,
                status=status.HTTP_201_CREATED,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class SubstituteResponseView(APIView):
    permission_classes = [
        HasModuleGrant("elm"),
    ]

    @extend_schema(request=SubstituteResponseSerializer, responses=SubstituteNominationSerializer)
    def post(self, request, pk: int):
        nomination = get_object_or_404(SubstituteNomination, pk=pk)
        serializer = SubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = applications.respond_substitute_nomination(
                nomination=nomination,
                accept=serializer.validated_data["accept"],
                decline_reason=serializer.validated_data.get("decline_reason", ""),
            )
            return Response(SubstituteNominationSerializer(updated).data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveApplicationReviewView(APIView):
    permission_classes = [
        HasModuleGrant("elm"),
    ]

    @extend_schema(request=ReviewApplicationSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk: int):
        application = get_object_or_404(LeaveApplication, pk=pk)
        serializer = ReviewApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reviewed = applications.review_leave_application(
                application=application,
                approve=serializer.validated_data["approve"],
            )
            return Response(LeaveApplicationSerializer(reviewed).data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveApplicationWithdrawView(APIView):
    permission_classes = [
        HasModuleGrant("elm"),
    ]

    @extend_schema(responses=LeaveApplicationSerializer)
    def post(self, request, pk: int):
        application = get_object_or_404(
            LeaveApplication,
            pk=pk,
            applicant_id=request.user.user_id,
        )
        try:
            withdrawn = applications.withdraw_application(application=application)
            return Response(LeaveApplicationSerializer(withdrawn).data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
