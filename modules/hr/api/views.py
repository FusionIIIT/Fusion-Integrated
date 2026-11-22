from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.hr.api import serializers as s
from modules.hr.selectors import (
    appraisals as appraisal_selectors,
)
from modules.hr.selectors import (
    audit as audit_selectors,
)
from modules.hr.selectors import (
    claims as claim_selectors,
)
from modules.hr.selectors import (
    configuration as configuration_selectors,
)
from modules.hr.selectors import (
    employees as employee_selectors,
)
from modules.hr.selectors import leaves as leave_selectors
from modules.hr.selectors import (
    notifications as notification_selectors,
)
from modules.hr.services import (
    appraisals as appraisal_service,
)
from modules.hr.services import (
    claims as claim_service,
)
from modules.hr.services import (
    configuration as configuration_service,
)
from modules.hr.services import (
    employees as employee_service,
)
from modules.hr.services import leaves as leave_service
from modules.hr.services import (
    notifications as notification_service,
)

MODULE = HasModuleGrant("hr")


def _actor(request):
    return getattr(request, "principal", None)


class HRListAPIView(APIView):
    pagination_class = CursorPagination

    def page(self, request, queryset, serializer_class):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = serializer_class(page, many=True, context={"request": request, "view": self})
        return paginator.get_paginated_response(serializer.data)


@extend_schema(responses=s.EmployeeRecordSerializer(many=True))
class EmployeeListView(HRListAPIView):
    serializer_class = s.EmployeeRecordSerializer
    permission_classes = [
        MODULE,
        HasPermission("hr.employee.view", "hr.employee.view_self"),
    ]

    def get(self, request):
        records = employee_selectors.visible_employee_records(_actor(request))
        return self.page(request, records.order_by("-created_at"), s.EmployeeRecordSerializer)


@extend_schema(request=s.EmployeeRecordWriteSerializer, responses={201: s.EmployeeRecordSerializer})
class EmployeeCreateView(APIView):
    permission_classes = [MODULE, HasPermission("hr.employee.create")]
    throttle_scope = "hr_write"

    def post(self, request):
        payload = s.EmployeeRecordWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        user_id = data.pop("user_id")
        record = employee_service.create_employee_record(
            actor=_actor(request), user_id=user_id, **data
        )
        return Response(
            s.EmployeeRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/api/v1/hr/employees/{user_id}/"},
        )


@extend_schema(responses=s.EmployeeRecordSerializer)
class EmployeeDetailView(APIView):
    permission_classes = [
        MODULE,
        HasPermission("hr.employee.view", "hr.employee.view_self"),
    ]

    def get(self, request, user_id):
        record = employee_selectors.employee_record_for_user(
            user_id=user_id, principal=_actor(request)
        )
        if record is None:
            raise NotFoundError("No employee service record is available.")
        return Response(s.EmployeeRecordSerializer(record).data)


@extend_schema(request=s.EmployeeRecordPatchSerializer, responses=s.EmployeeRecordSerializer)
class EmployeeUpdateView(APIView):
    permission_classes = [MODULE, HasPermission("hr.employee.update")]
    throttle_scope = "hr_write"

    def patch(self, request, user_id):
        payload = s.EmployeeRecordPatchSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        record = employee_service.update_employee_record(
            actor=_actor(request), user_id=user_id, changes=dict(payload.validated_data)
        )
        return Response(s.EmployeeRecordSerializer(record).data)


@extend_schema(responses=s.ClaimSerializer(many=True))
class ClaimListView(HRListAPIView):
    serializer_class = s.ClaimSerializer
    permission_classes = [
        MODULE,
        HasPermission(
            "hr.claim.view",
            "hr.claim.view_self",
            "hr.claim.approve",
            "hr.claim.verify",
            "hr.claim.manage",
        ),
    ]

    def get(self, request):
        claims = claim_selectors.visible_claims(_actor(request))
        return self.page(request, claims.order_by("-created_at"), s.ClaimSerializer)


@extend_schema(request=s.ClaimCreateSerializer, responses={201: s.ClaimSerializer})
class ClaimCreateView(APIView):
    permission_classes = [MODULE, HasPermission("hr.claim.create")]
    throttle_scope = "hr_write"

    def post(self, request):
        payload = s.ClaimCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        claim = claim_service.submit_claim(actor=_actor(request), **payload.validated_data)
        return Response(
            s.ClaimSerializer(claim).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/api/v1/hr/claims/{claim.pk}/"},
        )


@extend_schema(responses=s.ClaimSerializer)
class ClaimDetailView(APIView):
    permission_classes = [
        MODULE,
        HasPermission(
            "hr.claim.view",
            "hr.claim.view_self",
            "hr.claim.approve",
            "hr.claim.verify",
            "hr.claim.manage",
        ),
    ]

    def get(self, request, pk):
        claim = claim_selectors.claim_for_user(claim_id=pk, principal=_actor(request))
        if claim is None:
            raise NotFoundError("No such HR claim.")
        claim = claim_selectors.visible_claims(_actor(request)).get(pk=claim.pk)
        return Response(s.ClaimSerializer(claim).data)


@extend_schema(request=s.ClaimVerificationSerializer, responses=s.ClaimSerializer)
class ClaimVerificationView(APIView):
    permission_classes = [MODULE, HasPermission("hr.claim.verify")]
    throttle_scope = "hr_write"

    def post(self, request, pk):
        payload = s.ClaimVerificationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        claim = claim_service.verify_claim(
            actor=_actor(request), claim_id=pk, **payload.validated_data
        )
        return Response(s.ClaimSerializer(claim).data)


@extend_schema(request=s.ClaimDecisionSerializer, responses=s.ClaimSerializer)
class ClaimDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("hr.claim.approve")]
    throttle_scope = "hr_write"

    def post(self, request, pk):
        payload = s.ClaimDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        claim = claim_service.decide_claim(
            actor=_actor(request), claim_id=pk, **payload.validated_data
        )
        return Response(s.ClaimSerializer(claim).data)


@extend_schema(request=s.ClaimProcessingSerializer, responses=s.ClaimSerializer)
class ClaimProcessingView(APIView):
    permission_classes = [MODULE, HasPermission("hr.claim.manage")]
    throttle_scope = "hr_write"

    def post(self, request, pk):
        payload = s.ClaimProcessingSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        claim = claim_service.process_claim(
            actor=_actor(request), claim_id=pk, **payload.validated_data
        )
        return Response(s.ClaimSerializer(claim).data)


@extend_schema(
    request=s.ClaimIntegrationWriteSerializer, responses={201: s.ClaimIntegrationStatusSerializer}
)
class ClaimIntegrationStatusView(APIView):
    permission_classes = [MODULE, HasPermission("hr.claim.manage")]
    throttle_scope = "hr_write"

    def post(self, request, pk):
        payload = s.ClaimIntegrationWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = claim_service.record_integration_status(
            actor=_actor(request), claim_id=pk, **payload.validated_data
        )
        return Response(
            s.ClaimIntegrationStatusSerializer(row).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(responses=s.AuditEventSerializer(many=True))
class ClaimHistoryView(HRListAPIView):
    serializer_class = s.AuditEventSerializer
    permission_classes = [
        MODULE,
        HasPermission(
            "hr.claim.view",
            "hr.claim.view_self",
            "hr.claim.approve",
            "hr.claim.verify",
            "hr.claim.manage",
        ),
    ]

    def get(self, request, pk):
        claim = claim_selectors.claim_for_user(claim_id=pk, principal=_actor(request))
        if claim is None:
            raise NotFoundError("No such HR claim.")
        events = (
            audit_selectors.audit_events()
            .filter(entity_type="claim", entity_id=claim.pk)
            .order_by("-created_at")
        )
        return self.page(request, events, s.AuditEventSerializer)


@extend_schema(responses=s.AppraisalSerializer(many=True))
class AppraisalListView(HRListAPIView):
    serializer_class = s.AppraisalSerializer
    permission_classes = [
        MODULE,
        HasPermission("hr.appraisal.view_self", "hr.appraisal.assign", "hr.appraisal.review"),
    ]

    def get(self, request):
        appraisals = appraisal_selectors.visible_appraisals(_actor(request))
        return self.page(request, appraisals.order_by("-created_at"), s.AppraisalSerializer)


@extend_schema(request=s.AppraisalCreateSerializer, responses={201: s.AppraisalSerializer})
class AppraisalCreateView(APIView):
    permission_classes = [MODULE, HasPermission("hr.appraisal.create")]
    throttle_scope = "hr_write"

    def post(self, request):
        payload = s.AppraisalCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        appraisal = appraisal_service.submit_appraisal(
            actor=_actor(request), **payload.validated_data
        )
        return Response(
            s.AppraisalSerializer(appraisal).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/api/v1/hr/appraisals/{appraisal.pk}/"},
        )


@extend_schema(responses=s.AppraisalSerializer)
class AppraisalDetailView(APIView):
    permission_classes = [
        MODULE,
        HasPermission("hr.appraisal.view_self", "hr.appraisal.assign", "hr.appraisal.review"),
    ]

    def get(self, request, pk):
        appraisal = appraisal_selectors.visible_appraisals(_actor(request)).filter(pk=pk).first()
        if appraisal is None:
            raise NotFoundError("No such appraisal.")
        return Response(s.AppraisalSerializer(appraisal).data)


@extend_schema(request=s.ReviewerAssignmentSerializer, responses=s.AppraisalSerializer)
class AppraisalReviewerAssignmentView(APIView):
    permission_classes = [MODULE, HasPermission("hr.appraisal.assign")]
    throttle_scope = "hr_write"

    def post(self, request, pk):
        payload = s.ReviewerAssignmentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        appraisal = appraisal_service.assign_reviewers(
            actor=_actor(request), appraisal_id=pk, **payload.validated_data
        )
        return Response(s.AppraisalSerializer(appraisal).data)


@extend_schema(request=s.AppraisalReviewSerializer, responses=s.AppraisalSerializer)
class AppraisalReviewView(APIView):
    permission_classes = [MODULE, HasPermission("hr.appraisal.review")]
    throttle_scope = "hr_write"

    def post(self, request, pk):
        payload = s.AppraisalReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        appraisal = appraisal_service.review_appraisal(
            actor=_actor(request), appraisal_id=pk, **payload.validated_data
        )
        return Response(s.AppraisalSerializer(appraisal).data)


@extend_schema(responses=s.WorkflowRouteSerializer(many=True))
class WorkflowRouteListView(HRListAPIView):
    serializer_class = s.WorkflowRouteSerializer
    permission_classes = [MODULE, HasPermission("hr.workflow.manage")]

    def get(self, request):
        return self.page(
            request,
            configuration_selectors.workflow_routes().order_by("employee_category", "request_type"),
            s.WorkflowRouteSerializer,
        )


@extend_schema(request=s.WorkflowRouteWriteSerializer, responses=s.WorkflowRouteSerializer)
class WorkflowRouteSaveView(APIView):
    permission_classes = [MODULE, HasPermission("hr.workflow.manage")]
    throttle_scope = "hr_write"

    def post(self, request):
        payload = s.WorkflowRouteWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        route = configuration_service.save_workflow_route(
            actor=_actor(request), **payload.validated_data
        )
        return Response(s.WorkflowRouteSerializer(route).data)


@extend_schema(responses=s.AppraisalWindowSerializer(many=True))
class AppraisalWindowListView(HRListAPIView):
    serializer_class = s.AppraisalWindowSerializer
    permission_classes = [MODULE, HasPermission("hr.workflow.manage")]

    def get(self, request):
        return self.page(
            request,
            configuration_selectors.appraisal_windows().order_by("-opens_at"),
            s.AppraisalWindowSerializer,
        )


@extend_schema(request=s.AppraisalWindowWriteSerializer, responses=s.AppraisalWindowSerializer)
class AppraisalWindowSaveView(APIView):
    permission_classes = [MODULE, HasPermission("hr.workflow.manage")]
    throttle_scope = "hr_write"

    def post(self, request):
        payload = s.AppraisalWindowWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        window = configuration_service.save_appraisal_window(
            actor=_actor(request), **payload.validated_data
        )
        return Response(s.AppraisalWindowSerializer(window).data)


@extend_schema(responses=s.AuditEventSerializer(many=True))
class AuditEventListView(HRListAPIView):
    serializer_class = s.AuditEventSerializer
    permission_classes = [MODULE, HasPermission("hr.audit.view")]

    def get(self, request):
        events = audit_selectors.audit_events().order_by("-created_at")
        return self.page(request, events, s.AuditEventSerializer)


@extend_schema(responses=s.HRNotificationSerializer(many=True))
class NotificationListView(HRListAPIView):
    serializer_class = s.HRNotificationSerializer
    permission_classes = [MODULE, HasPermission("hr.notification.view")]

    def get(self, request):
        notifications = notification_selectors.notifications_for(_actor(request))
        return self.page(request, notifications, s.HRNotificationSerializer)


@extend_schema(request=s.NoticeWriteSerializer, responses={201: s.NoticePublishResponseSerializer})
class NoticePublishView(APIView):
    permission_classes = [MODULE, HasPermission("hr.notification.manage")]
    throttle_scope = "hr_write"

    def post(self, request):
        payload = s.NoticeWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        rows = notification_service.publish_notice(actor=_actor(request), **payload.validated_data)
        return Response({"published": len(rows)}, status=status.HTTP_201_CREATED)


@extend_schema(responses=s.LeaveRequestSerializer(many=True))
class LeaveRequestListView(HRListAPIView):
    permission_classes = [
        MODULE,
        HasPermission("hr.leave.view_self", "hr.leave.view", "hr.leave.approve"),
    ]

    def get(self, request):
        requests = leave_selectors.visible_leave_requests(_actor(request))
        return self.page(request, requests.order_by("-created_at"), s.LeaveRequestSerializer)


@extend_schema(request=s.LeaveRequestCreateSerializer, responses={201: s.LeaveRequestSerializer})
class LeaveRequestCreateView(APIView):
    permission_classes = [MODULE, HasPermission("hr.leave.create")]
    throttle_scope = "hr_write"

    def post(self, request):
        payload = s.LeaveRequestCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = leave_service.submit_leave_request(
            actor=_actor(request), **payload.validated_data
        )
        return Response(
            s.LeaveRequestSerializer(leave_request).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/api/v1/hr/leaves/{leave_request.pk}/"},
        )


@extend_schema(request=s.LeaveDecisionSerializer, responses=s.LeaveRequestSerializer)
class LeaveRequestDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("hr.leave.approve")]
    throttle_scope = "hr_write"

    def post(self, request, pk):
        payload = s.LeaveDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = leave_service.decide_leave_request(
            actor=_actor(request), request_id=pk, **payload.validated_data
        )
        return Response(s.LeaveRequestSerializer(leave_request).data)


@extend_schema(responses=s.LeaveBalanceManageReadSerializer(many=True))
class LeaveBalanceListView(HRListAPIView):
    permission_classes = [MODULE, HasPermission("hr.leave_balance.manage")]

    def get(self, request):
        return self.page(
            request,
            leave_selectors.managed_leave_balances(),
            s.LeaveBalanceManageReadSerializer,
        )


@extend_schema(
    request=s.LeaveBalanceManageSerializer,
    responses=s.LeaveBalanceManageReadSerializer,
)
class LeaveBalanceSaveView(APIView):
    permission_classes = [MODULE, HasPermission("hr.leave_balance.manage")]
    throttle_scope = "hr_write"

    def post(self, request):
        payload = s.LeaveBalanceManageSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        employee_user_id = data.pop("employee_user_id")
        balance = leave_service.set_leave_balance(
            actor=_actor(request), employee_user_id=employee_user_id, **data
        )
        return Response(s.LeaveBalanceManageReadSerializer(balance).data)
