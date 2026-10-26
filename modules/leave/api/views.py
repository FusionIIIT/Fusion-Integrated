# API Views for ELM endpoints
from datetime import date

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, IsAuthenticatedPrincipal
from modules.leave.api.serializers import (
    LeaveApplicationCreateSerializer,
    LeaveApplicationSerializer,
    LeaveBalanceSerializer,
    LeaveReviewSerializer,
)
from modules.leave.models import LeaveApplication, LeaveBalance
from modules.leave.services.applications import (
    cancel_application,
    initialize_user_balances,
    review_application,
    submit_application,
    withdraw_application,
)


class LeaveBalanceListView(APIView):
    """View to fetch current year leave balances for the authenticated user."""

    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]
    serializer_class = LeaveBalanceSerializer

    def get(self, request):
        if "leave_elm.application.view" not in request.principal.permissions:
            raise PermissionDeniedError("Permission denied to view leave balances.")

        user_id = request.principal.user_id
        current_year = date.today().year
        balances = LeaveBalance.objects.filter(user_id=user_id, year=current_year)
        if not balances.exists():
            balances = initialize_user_balances(user_id, current_year)

        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeaveApplicationListCreateView(APIView):
    """List applications or submit a new leave application."""

    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]
    serializer_class = LeaveApplicationSerializer

    def get(self, request):
        if "leave_elm.application.view" not in request.principal.permissions:
            raise PermissionDeniedError("Permission denied to view leave applications.")

        user_id = request.principal.user_id
        if "leave_elm.application.approve" in request.principal.permissions:
            applications = LeaveApplication.objects.all().order_by("-created_at")
        else:
            applications = LeaveApplication.objects.filter(user_id=user_id).order_by("-created_at")

        serializer = LeaveApplicationSerializer(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if "leave_elm.application.apply" not in request.principal.permissions:
            raise PermissionDeniedError("Permission denied to apply for leave.")

        # Prevent students from availing employee leave (BR-EL-036)
        roles = [r.lower() for r in getattr(request.principal, "roles", [])]
        if "student" in roles or getattr(request.principal, "user_type", "").lower() == "student":
            raise PermissionDeniedError("Students are not eligible to apply for employee leave.")

        serializer = LeaveApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        application = submit_application(
            user_id=request.principal.user_id,
            leave_type=data["leave_type"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            reason=data["reason"],
            half_day=data.get("half_day", "NONE"),
            is_station_leave=data.get("is_station_leave", False),
            station_leave_address=data.get("station_leave_address", ""),
            replacement_user_id=data.get("replacement_user_id"),
        )
        return Response(
            LeaveApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class LeaveApplicationReviewView(APIView):
    """Review (approve/reject) a submitted leave application."""

    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]
    serializer_class = LeaveReviewSerializer

    def post(self, request, pk: int):
        if "leave_elm.application.approve" not in request.principal.permissions:
            raise PermissionDeniedError("Permission denied to review leave applications.")

        serializer = LeaveReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application = review_application(
            application_id=pk,
            reviewer_user_id=request.principal.user_id,
            action=serializer.validated_data["action"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(application).data, status=status.HTTP_200_OK)


class LeaveApplicationWithdrawView(APIView):
    """Withdraw a pending leave application before approval (BR-EL-022)."""

    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]
    serializer_class = LeaveApplicationSerializer

    def post(self, request, pk: int):
        if "leave_elm.application.withdraw" not in request.principal.permissions:
            raise PermissionDeniedError("Permission denied to withdraw leave applications.")

        application = withdraw_application(
            application_id=pk,
            user_id=request.principal.user_id,
        )
        return Response(LeaveApplicationSerializer(application).data, status=status.HTTP_200_OK)


class LeaveApplicationCancelView(APIView):
    """Cancel an approved leave application before its start date (BR-EL-023)."""

    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]
    serializer_class = LeaveApplicationSerializer

    def post(self, request, pk: int):
        if "leave_elm.application.cancel" not in request.principal.permissions:
            raise PermissionDeniedError("Permission denied to cancel leave applications.")

        is_approver = "leave_elm.application.approve" in request.principal.permissions
        application = cancel_application(
            application_id=pk,
            user_id=request.principal.user_id,
            is_approver=is_approver,
        )
        return Response(LeaveApplicationSerializer(application).data, status=status.HTTP_200_OK)
