from datetime import date

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasPermission
from modules.directory.models import UserRef
from modules.elm import services
from modules.elm.api.serializers import (
    ApplyInputSerializer, LeaveApplicationSerializer, LeaveBalanceSerializer)
from modules.elm.models import LeaveApplication, LeaveApplicationStatus


def _caller(request) -> UserRef:
    """The directory record of the logged-in person."""
    try:
        return UserRef.objects.get(pk=request.principal.user_id)
    except UserRef.DoesNotExist as exc:
        raise NotFound("No directory record for this user.") from exc


class ApplicationsView(APIView):
    """GET: the caller's own applications. POST: submit a new one."""

    def get_permissions(self):
        code = "elm.leave.apply" if self.request.method == "POST" \
            else "elm.leave.view"
        return [HasPermission(code)()]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        rows = LeaveApplication.objects.filter(
            user=_caller(request)).order_by("-created_at")
        return Response({"results": LeaveApplicationSerializer(rows, many=True).data})

    @extend_schema(request=ApplyInputSerializer,
                   responses=LeaveApplicationSerializer)
    def post(self, request):
        data = ApplyInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            application = services.submit_application(
                user=_caller(request), **data.validated_data)
        except ValueError as exc:
            raise BadRequestError(str(exc), code="invalid_leave_request") from exc
        return Response(LeaveApplicationSerializer(application).data,
                        status=status.HTTP_201_CREATED)


class BalancesView(APIView):
    """The caller's balances for the current year."""

    permission_classes = [HasPermission("elm.leave.view")]

    @extend_schema(responses=LeaveBalanceSerializer(many=True))
    def get(self, request):
        balances = services.ensure_balances(_caller(request), date.today().year)
        return Response({"results": LeaveBalanceSerializer(balances, many=True).data})


class ApproveView(APIView):
    """Approve a pending application."""

    permission_classes = [HasPermission("elm.leave.approve")]

    @extend_schema(request=None, responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        try:
            application = LeaveApplication.objects.get(pk=pk)
        except LeaveApplication.DoesNotExist as exc:
            raise NotFound("Application not found.") from exc
        if application.status != LeaveApplicationStatus.PENDING:
            raise BadRequestError("Only a pending application can be approved.",
                                  code="not_pending")
        try:
            services.approve_application(application)
        except ValueError as exc:
            raise BadRequestError(str(exc), code="invalid_leave_request") from exc
        application.refresh_from_db()
        return Response(LeaveApplicationSerializer(application).data)
