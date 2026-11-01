from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    ApplyInputSerializer, BalanceInputSerializer, CalendarInputSerializer,
    DecisionInputSerializer, LeaveApplicationSerializer, LeaveBalanceSerializer,
    RouteInputSerializer,
)
from modules.elm.domain.leave import Category, LeaveRuleError
from modules.elm.selectors.leave import applications_for, balances_for, review_queue_for
from modules.elm.services import leave

MODULE = HasModuleGrant("leave_elm")


def _rule_error(exc: LeaveRuleError):
    raise BadRequestError(str(exc), code="leave_rule_invalid") from exc


class LeaveTypesView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.application.apply")]

    @extend_schema(responses={200: dict})
    def get(self, request):
        data = [{"code": category.value, "label": category.name}
                for category in Category]
        if request.user.kind.casefold() == "staff":
            data = [item for item in data if item["code"] != "VL"]
        if request.user.kind.casefold() == "faculty":
            data = [item for item in data if item["code"] != "EL"]
        return Response(data)


class MyApplicationsView(APIView):
    permission_classes = [MODULE]

    def get_permissions(self):
        code = ("leave_elm.application.apply" if self.request.method == "POST"
                else "leave_elm.application.view_self")
        return [MODULE(), HasPermission(code)()]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        rows = applications_for(request.user).prefetch_related("transitions")
        return Response(LeaveApplicationSerializer(rows, many=True).data)

    @extend_schema(request=ApplyInputSerializer, responses=LeaveApplicationSerializer)
    def post(self, request):
        serializer = ApplyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = leave.apply_for_leave(actor=request.user, **serializer.validated_data)
        except LeaveRuleError as exc:
            _rule_error(exc)
        return Response(LeaveApplicationSerializer(application).data, status=201)


class MyBalanceView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.balance.view")]

    @extend_schema(responses=LeaveBalanceSerializer(many=True))
    def get(self, request):
        raw_year = request.query_params.get("year")
        if raw_year is None:
            year = timezone.localdate().year
        else:
            try:
                year = int(raw_year)
            except ValueError as exc:
                raise BadRequestError("year must be a number.", code="invalid_filter") from exc
            if not 2000 <= year <= 9999:
                raise BadRequestError("year is outside the supported range.", code="invalid_filter")
        return Response(LeaveBalanceSerializer(balances_for(request.user, year), many=True).data)


class PendingApprovalsView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.application.review")]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        rows = review_queue_for(request.user).prefetch_related("transitions")
        return Response(LeaveApplicationSerializer(rows, many=True).data)


class DecideView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.application.review")]

    @extend_schema(request=DecisionInputSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        serializer = DecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = leave.decide(actor=request.user, application_id=pk,
                                       **serializer.validated_data)
        except LeaveRuleError as exc:
            _rule_error(exc)
        return Response(LeaveApplicationSerializer(application).data)


class WithdrawView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.application.apply")]

    @extend_schema(responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        application = leave.withdraw(actor=request.user, application_id=pk)
        return Response(LeaveApplicationSerializer(application).data)


class AdminBalanceView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.policy.manage")]

    @extend_schema(request=BalanceInputSerializer, responses=LeaveBalanceSerializer)
    def put(self, request):
        serializer = BalanceInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            balance = leave.set_balance(actor=request.user, **serializer.validated_data)
        except LeaveRuleError as exc:
            _rule_error(exc)
        return Response(LeaveBalanceSerializer(balance).data)


class AdminRouteView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.policy.manage")]

    @extend_schema(request=RouteInputSerializer)
    def put(self, request, employee_id, category):
        serializer = RouteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            route = leave.set_route(actor=request.user, employee_id=employee_id,
                                    category=category, **serializer.validated_data)
        except LeaveRuleError as exc:
            _rule_error(exc)
        return Response([{"stage": row.stage, "approver_user_id": row.approver_user_id}
                         for row in route])


class AdminCalendarView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.policy.manage")]

    @extend_schema(request=CalendarInputSerializer)
    def post(self, request):
        serializer = CalendarInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            calendar = leave.publish_calendar(actor=request.user, **serializer.validated_data)
        except (LeaveRuleError, ValueError) as exc:
            _rule_error(LeaveRuleError(str(exc)))
        return Response({"id": calendar.pk, "name": calendar.name,
                         "published_at": calendar.published_at}, status=201)
