from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.elm.api.serializers import (
    LeaveBalanceSerializer,
    LeaveApplicationReadSerializer,
    LeaveApplicationCreateSerializer,
    ReviewActionSerializer,
    SanctionActionSerializer,
    HolidaySerializer,
)
from modules.elm.selectors.leave import (
    get_user_balances,
    get_user_applications,
    get_application_by_id,
    get_pending_reviews_for_approver,
    get_holidays,
)
from modules.elm.services.leave import (
    ensure_initial_balances,
    submit_leave_application,
    review_leave_application,
    sanction_leave_application,
    cancel_leave_application,
)


def _get_user_id(request: Request) -> int:
    return getattr(request.user, "user_id", request.user.id if hasattr(request.user, "id") else 1)


class MyBalancesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user_id = _get_user_id(request)
        ensure_initial_balances(user_id)
        balances = get_user_balances(user_id)
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class ApplicationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user_id = _get_user_id(request)
        applications = get_user_applications(user_id)
        return Response(LeaveApplicationReadSerializer(applications, many=True).data)

    def post(self, request: Request) -> Response:
        user_id = _get_user_id(request)
        serializer = LeaveApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            app = submit_leave_application(
                user_id=user_id,
                leave_type=data["leave_type"],
                start_date=data["start_date"],
                start_half=data.get("start_half", "FULL"),
                end_date=data["end_date"],
                end_half=data.get("end_half", "FULL"),
                reason=data["reason"],
                station_leave=data.get("station_leave", False),
                station_address=data.get("station_address", ""),
                station_contact=data.get("station_contact", ""),
                emergency_contact=data.get("emergency_contact", ""),
                substitute_user_id=data.get("substitute_user_id"),
            )
            return Response(LeaveApplicationReadSerializer(app).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            raise ValidationError(detail=str(e))


class ApplicationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        app = get_application_by_id(pk)
        if not app:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        user_id = _get_user_id(request)
        if app.user_id != user_id and not getattr(request.user, "has_permission", lambda p: False)("elm.leave.review"):
            raise PermissionDenied("You do not have permission to view this application.")
        return Response(LeaveApplicationReadSerializer(app).data)


class CancelApplicationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        user_id = _get_user_id(request)
        try:
            app = cancel_leave_application(app_id=pk, actor_user_id=user_id)
            return Response(LeaveApplicationReadSerializer(app).data)
        except Exception as e:
            raise ValidationError(detail=str(e))


class PendingApprovalsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user_id = _get_user_id(request)
        is_authority = getattr(request.user, "has_permission", lambda p: False)("elm.leave.sanction")
        pending = get_pending_reviews_for_approver(user_id=user_id, is_authority=is_authority)
        return Response(LeaveApplicationReadSerializer(pending, many=True).data)


class ReviewApplicationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        user_id = _get_user_id(request)
        serializer = ReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            app = review_leave_application(
                app_id=pk,
                actor_user_id=user_id,
                recommend=data["recommend"],
                comments=data.get("comments", ""),
            )
            return Response(LeaveApplicationReadSerializer(app).data)
        except Exception as e:
            raise ValidationError(detail=str(e))


class SanctionApplicationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        user_id = _get_user_id(request)
        serializer = SanctionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            app = sanction_leave_application(
                app_id=pk,
                actor_user_id=user_id,
                approve=data["approve"],
                comments=data.get("comments", ""),
            )
            return Response(LeaveApplicationReadSerializer(app).data)
        except Exception as e:
            raise ValidationError(detail=str(e))


class HolidayListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        holidays = get_holidays()
        return Response(HolidaySerializer(holidays, many=True).data)
