from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.hreis.api import serializers as s
from modules.hreis.models import HRPolicyVersion, HRRequest, LeaveBalanceEntry
from modules.hreis.selectors import scoping
from modules.hreis.services import requests as service

MODULE = HasModuleGrant("hreis")


def _page(request, queryset, serializer):
    paginator = CursorPagination()
    page = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response(serializer(page, many=True).data)


class RequestListCreateView(APIView):
    throttle_scope = "hreis_write"

    def get_permissions(self):
        code = "hreis.request.create" if self.request.method == "POST" else "hreis.request.view"
        return [MODULE(), HasPermission(code)()]

    @extend_schema(responses=s.HRRequestSerializer, operation_id="hreis_request_list")
    def get(self, request):
        rows = scoping.requests_for(request.principal).order_by("-id")
        request_type = request.query_params.get("request_type")
        if request_type:
            valid_types = {value for value, _ in HRRequest.REQUEST_TYPES}
            if request_type not in valid_types:
                from core.api.exceptions import BadRequestError

                raise BadRequestError("request_type is not supported.", code="invalid_request_type")
            rows = rows.filter(request_type=request_type)
        return _page(request, rows, s.HRRequestSerializer)

    @extend_schema(request=s.CreateRequestSerializer, responses={201: s.HRRequestSerializer})
    def post(self, request):
        payload = s.CreateRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.create_request(
            actor=request.principal,
            request_type=payload.validated_data["request_type"],
            data=payload.validated_data["data"],
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(s.HRRequestSerializer(row).data, status=status.HTTP_201_CREATED)


class RequestDetailView(APIView):
    permission_classes = [MODULE, HasPermission("hreis.request.view")]

    @extend_schema(responses=s.HRRequestSerializer, operation_id="hreis_request_retrieve")
    def get(self, request, pk):
        row = scoping.requests_for(request.principal).filter(pk=pk).first()
        if row is None:
            from core.api.exceptions import NotFoundError

            raise NotFoundError("HR request was not found.", code="request_not_found")
        return Response(s.HRRequestSerializer(row).data)


class RequestTransitionView(APIView):
    throttle_scope = "hreis_write"
    permission_classes = [
        MODULE,
        HasPermission("hreis.request.review", "hreis.request.assign", "hreis.claim.update"),
    ]

    @extend_schema(
        request=s.HRRequestTransitionSerializer,
        responses=s.HRRequestSerializer,
        operation_id="hreis_request_transition",
    )
    def post(self, request, pk):
        payload = s.HRRequestTransitionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = scoping.requests_for(request.principal).filter(pk=pk).first()
        if row is None:
            from core.api.exceptions import NotFoundError

            raise NotFoundError("HR request was not found.", code="request_not_found")
        row = service.transition_request(
            request_id=row.pk,
            actor=request.principal,
            event=payload.validated_data["event"],
            note=payload.validated_data.get("note", ""),
            details=payload.validated_data.get("details", {}),
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(s.HRRequestSerializer(row).data)


class EmployeeRecordsView(APIView):
    permission_classes = [MODULE, HasPermission("hreis.employee.view", "hreis.employee.manage")]

    @extend_schema(responses=s.EmployeeServiceRecordSerializer(many=True))
    def get(self, request):
        rows = scoping.employee_record_for(request.principal).order_by("id")
        return _page(request, rows, s.EmployeeServiceRecordSerializer)


class EmployeeRecordDetailView(APIView):
    throttle_scope = "hreis_write"

    def get_permissions(self):
        code = "hreis.employee.manage" if self.request.method == "PUT" else "hreis.employee.view"
        return [MODULE(), HasPermission(code)()]

    @extend_schema(responses=s.EmployeeServiceRecordSerializer)
    def get(self, request, user_id):
        row = scoping.employee_record_for(request.principal).filter(user_id=user_id).first()
        if row is None:
            from core.api.exceptions import NotFoundError

            raise NotFoundError(
                "Employee service record was not found.", code="employee_record_not_found"
            )
        return Response(s.EmployeeServiceRecordSerializer(row).data)

    @extend_schema(
        request=s.EmployeeServiceRecordWriteSerializer, responses=s.EmployeeServiceRecordSerializer
    )
    def put(self, request, user_id):
        payload = s.EmployeeServiceRecordWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.maintain_employee_record(
            actor=request.principal, user_id=user_id, values=payload.validated_data
        )
        return Response(s.EmployeeServiceRecordSerializer(row).data)


class PolicyListCreateView(APIView):
    throttle_scope = "hreis_write"

    def get_permissions(self):
        code = "hreis.policy.manage" if self.request.method == "POST" else "hreis.policy.view"
        return [MODULE(), HasPermission(code)()]

    @extend_schema(responses=s.PolicySerializer(many=True))
    def get(self, request):
        rows = HRPolicyVersion.objects.order_by("policy_name", "-version")
        return Response(s.PolicySerializer(rows, many=True).data)

    @extend_schema(request=s.PolicyCreateSerializer, responses={201: s.PolicySerializer})
    def post(self, request):
        payload = s.PolicyCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.create_policy_version(actor=request.principal, **payload.validated_data)
        return Response(s.PolicySerializer(row).data, status=status.HTTP_201_CREATED)


class LeaveBalanceView(APIView):
    throttle_scope = "hreis_write"

    def get_permissions(self):
        code = "hreis.leave_balance.manage" if self.request.method == "POST" else None
        if code:
            return [MODULE(), HasPermission(code)()]
        return [MODULE(), HasPermission("hreis.leave_balance.view", "hreis.leave_balance.manage")()]

    @extend_schema(responses=s.LeaveBalanceEntrySerializer(many=True))
    def get(self, request):
        qs = LeaveBalanceEntry.objects.filter(user_id=request.principal.user_id)
        if request.principal.has_permission("hreis.leave_balance.manage"):
            user_id = request.query_params.get("user_id")
            if user_id:
                try:
                    qs = LeaveBalanceEntry.objects.filter(user_id=int(user_id))
                except ValueError as exc:
                    from core.api.exceptions import BadRequestError

                    raise BadRequestError(
                        "user_id must be a number.", code="invalid_user_id"
                    ) from exc
        return Response(s.LeaveBalanceEntrySerializer(qs.order_by("-created_at"), many=True).data)

    @extend_schema(
        request=s.BalanceAdjustmentSerializer, responses={201: s.LeaveBalanceEntrySerializer}
    )
    def post(self, request):
        payload = s.BalanceAdjustmentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        entry = service.adjust_leave_balance(actor=request.principal, **payload.validated_data)
        return Response(s.LeaveBalanceEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class NotificationListView(APIView):
    permission_classes = [MODULE, HasPermission("hreis.notification.view")]

    @extend_schema(responses=s.NotificationSerializer(many=True))
    def get(self, request):
        rows = scoping.notifications_for(request.principal).order_by("-id")
        return _page(request, rows, s.NotificationSerializer)


class AuditListView(APIView):
    permission_classes = [MODULE, HasPermission("hreis.audit.view")]

    @extend_schema(responses=s.AuditEventSerializer(many=True))
    def get(self, request):
        rows = scoping.audit_events_for(request.principal).order_by("-occurred_at")
        return Response(s.AuditEventSerializer(rows[:100], many=True).data)
