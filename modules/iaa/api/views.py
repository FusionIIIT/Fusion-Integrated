"""API views for IAA transport layer: parse, scope, delegate, serialize."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.csv import stream as stream_csv
from core.api.exceptions import NotFoundError, PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.iaa.api import serializers as s
from modules.iaa.api.permissions import ScopedCollection
from modules.iaa.selectors import (
    anomalies as anomaly_selectors,
)
from modules.iaa.selectors import (
    audit as audit_selectors,
)
from modules.iaa.selectors import (
    configuration as config_selectors,
)
from modules.iaa.selectors import (
    reports as report_selectors,
)
from modules.iaa.selectors import (
    requests as request_selectors,
)
from modules.iaa.selectors import (
    travel as travel_selectors,
)
from modules.iaa.services import (
    anomalies as anomaly_services,
)
from modules.iaa.services import (
    approvals as approval_services,
)
from modules.iaa.services import (
    audit as audit_services,
)
from modules.iaa.services import (
    requests as request_services,
)
from modules.iaa.services import (
    travel as travel_services,
)

MODULE_GRANT = HasModuleGrant("iaa")


def _actor(request):
    return getattr(request, "principal", None)


class RequestListCreateView(APIView):
    permission_classes = [
        MODULE_GRANT,
        ScopedCollection("iaa.request.view_self", "iaa.request.view_all"),
    ]

    @extend_schema(
        responses=s.ExpenseVoucherRequestSerializer(many=True), operation_id="iaa_requests_list"
    )
    def get(self, request):
        status_filter = request.query_params.get("status")
        reqs = request_selectors.get_requests(_actor(request), status=status_filter)
        serializer = s.ExpenseVoucherRequestSerializer(reqs, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=s.CreateExpenseRequestInputSerializer,
        responses={201: s.ExpenseVoucherRequestSerializer},
        operation_id="iaa_requests_create",
    )
    def post(self, request):
        if not _actor(request).has_permission("iaa.request.create"):
            raise PermissionDeniedError()
        serializer = s.CreateExpenseRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = _actor(request)
        created = request_services.create_expense_request(
            user_id=principal.user_id,
            acting_role=getattr(principal, "active_role", "basic_user"),
            department=data["department"],
            request_type=data["request_type"],
            title=data["title"],
            description=data.get("description", ""),
            items=data.get("items", []),
        )
        return Response(
            s.ExpenseVoucherRequestSerializer(created).data, status=status.HTTP_201_CREATED
        )


class RequestDetailView(APIView):
    permission_classes = [
        MODULE_GRANT,
        ScopedCollection("iaa.request.view_self", "iaa.request.view_all"),
    ]

    @extend_schema(responses=s.ExpenseVoucherRequestSerializer, operation_id="iaa_requests_detail")
    def get(self, request, pk: int):
        req = request_selectors.get_request_by_id(_actor(request), pk)
        if not req:
            raise NotFoundError("Request not found.")
        return Response(s.ExpenseVoucherRequestSerializer(req).data)


class RequestSubmitView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.request.create")]

    @extend_schema(
        request=None,
        responses=s.ExpenseVoucherRequestSerializer,
        operation_id="iaa_requests_submit",
    )
    def post(self, request, pk: int):
        principal = _actor(request)
        submitted = request_services.submit_expense_request(
            request_id=pk,
            user_id=principal.user_id,
            acting_role=getattr(principal, "active_role", "basic_user"),
        )
        return Response(s.ExpenseVoucherRequestSerializer(submitted).data)


class RequestValidateView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.request.validate")]

    @extend_schema(
        request=None,
        responses=s.ExpenseVoucherRequestSerializer,
        operation_id="iaa_requests_validate",
    )
    def post(self, request, pk: int):
        principal = _actor(request)
        validated = request_services.review_and_validate_request(
            request_id=pk,
            finance_user_id=principal.user_id,
            acting_role=getattr(principal, "active_role", "finance_staff"),
        )
        return Response(s.ExpenseVoucherRequestSerializer(validated).data)


class RequestQueryView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.request.validate")]

    @extend_schema(
        request=s.ClarificationQueryInputSerializer,
        responses={201: s.ClarificationQuerySerializer},
        operation_id="iaa_requests_query",
    )
    def post(self, request, pk: int):
        serializer = s.ClarificationQueryInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        principal = _actor(request)
        query = request_services.raise_request_clarification(
            request_id=pk,
            finance_user_id=principal.user_id,
            acting_role=getattr(principal, "active_role", "finance_staff"),
            query_text=serializer.validated_data["query_text"],
        )
        return Response(s.ClarificationQuerySerializer(query).data, status=status.HTTP_201_CREATED)


class RequestRespondQueryView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.request.create")]

    @extend_schema(
        request=s.ClarificationResponseInputSerializer,
        responses=s.ExpenseVoucherRequestSerializer,
        operation_id="iaa_requests_respond_query",
    )
    def post(self, request, query_id: int):
        serializer = s.ClarificationResponseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        principal = _actor(request)
        req = request_services.respond_to_request_clarification(
            query_id=query_id,
            user_id=principal.user_id,
            acting_role=getattr(principal, "active_role", "basic_user"),
            response_text=serializer.validated_data["response_text"],
        )
        return Response(s.ExpenseVoucherRequestSerializer(req).data)


class RequestDecideView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.request.approve")]

    @extend_schema(
        request=s.ApprovalDecisionInputSerializer,
        responses=s.ExpenseVoucherRequestSerializer,
        operation_id="iaa_requests_decide",
    )
    def post(self, request, pk: int):
        serializer = s.ApprovalDecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = _actor(request)
        req = approval_services.record_request_decision(
            request_id=pk,
            approver_id=principal.user_id,
            approver_role=getattr(principal, "active_role", "HOD"),
            decision=data["decision"],
            remarks=data["remarks"],
        )
        return Response(s.ExpenseVoucherRequestSerializer(req).data)


class RequestRecordView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.request.record")]

    @extend_schema(
        request=None,
        responses=s.ExpenseVoucherRequestSerializer,
        operation_id="iaa_requests_record",
    )
    def post(self, request, pk: int):
        principal = _actor(request)
        recorded = request_services.record_request_processing(
            request_id=pk,
            finance_user_id=principal.user_id,
            acting_role=getattr(principal, "active_role", "finance_staff"),
        )
        return Response(s.ExpenseVoucherRequestSerializer(recorded).data)


class TravelClaimListCreateView(APIView):
    permission_classes = [
        MODULE_GRANT,
        ScopedCollection("iaa.travel.view_self", "iaa.travel.view_all"),
    ]

    @extend_schema(responses=s.TAClaimSerializer(many=True), operation_id="iaa_travel_list")
    def get(self, request):
        status_filter = request.query_params.get("status")
        claims = travel_selectors.get_travel_claims(_actor(request), status=status_filter)
        serializer = s.TAClaimSerializer(claims, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=s.SubmitTAClaimInputSerializer,
        responses={201: s.TAClaimSerializer},
        operation_id="iaa_travel_create",
    )
    def post(self, request):
        if not _actor(request).has_permission("iaa.travel.create"):
            raise PermissionDeniedError()
        serializer = s.SubmitTAClaimInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = _actor(request)
        claim = travel_services.submit_travel_claim(
            user_id=principal.user_id,
            acting_role=getattr(principal, "active_role", "basic_user"),
            department=data["department"],
            purpose=data["purpose"],
            departure_date=str(data["departure_date"]),
            arrival_date=str(data["arrival_date"]),
            source_location=data["source_location"],
            destination_location=data["destination_location"],
            claimed_amount=data["claimed_amount"],
            items=data.get("items", []),
        )
        return Response(s.TAClaimSerializer(claim).data, status=status.HTTP_201_CREATED)


class TravelClaimDetailView(APIView):
    permission_classes = [
        MODULE_GRANT,
        ScopedCollection("iaa.travel.view_self", "iaa.travel.view_all"),
    ]

    @extend_schema(responses=s.TAClaimSerializer, operation_id="iaa_travel_detail")
    def get(self, request, pk: int):
        claim = travel_selectors.get_travel_claim_by_id(_actor(request), pk)
        if not claim:
            raise NotFoundError("Travel claim not found.")
        return Response(s.TAClaimSerializer(claim).data)


class TravelClaimVerifyView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.travel.verify")]

    @extend_schema(request=None, responses=s.TAClaimSerializer, operation_id="iaa_travel_verify")
    def post(self, request, pk: int):
        principal = _actor(request)
        verified = travel_services.verify_travel_claim(
            claim_id=pk,
            finance_user_id=principal.user_id,
            acting_role=getattr(principal, "active_role", "finance_staff"),
        )
        return Response(s.TAClaimSerializer(verified).data)


class TravelClaimDecideView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.travel.approve")]

    @extend_schema(
        request=s.ApprovalDecisionInputSerializer,
        responses=s.TAClaimSerializer,
        operation_id="iaa_travel_decide",
    )
    def post(self, request, pk: int):
        serializer = s.ApprovalDecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = _actor(request)
        claim = approval_services.record_travel_decision(
            claim_id=pk,
            approver_id=principal.user_id,
            approver_role=getattr(principal, "active_role", "Dean"),
            decision=data["decision"],
            remarks=data["remarks"],
        )
        return Response(s.TAClaimSerializer(claim).data)


class TravelClaimRecordView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.travel.record")]

    @extend_schema(request=None, responses=s.TAClaimSerializer, operation_id="iaa_travel_record")
    def post(self, request, pk: int):
        principal = _actor(request)
        recorded = travel_services.record_travel_processing(
            claim_id=pk,
            finance_user_id=principal.user_id,
            acting_role=getattr(principal, "active_role", "finance_staff"),
        )
        return Response(s.TAClaimSerializer(recorded).data)


class AnomalyListCreateView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.anomaly.view")]

    @extend_schema(responses=s.AnomalySerializer(many=True), operation_id="iaa_anomalies_list")
    def get(self, request):
        status_filter = request.query_params.get("status")
        anomalies = anomaly_selectors.get_anomalies(_actor(request), status=status_filter)
        return Response(s.AnomalySerializer(anomalies, many=True).data)

    @extend_schema(
        request=s.CreateAnomalyInputSerializer,
        responses={201: s.AnomalySerializer},
        operation_id="iaa_anomalies_create",
    )
    def post(self, request):
        if not _actor(request).has_permission("iaa.anomaly.flag"):
            raise PermissionDeniedError()
        serializer = s.CreateAnomalyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = _actor(request)
        anomaly = anomaly_services.create_anomaly(
            category=data["category"],
            description=data["description"],
            reference_type=data["reference_type"],
            reference_id=data["reference_id"],
            flagged_by_id=principal.user_id,
            flagged_by_role=getattr(principal, "active_role", "auditor"),
        )
        return Response(s.AnomalySerializer(anomaly).data, status=status.HTTP_201_CREATED)


class AnomalyResolveView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.anomaly.resolve")]

    @extend_schema(
        request=s.AnomalyResolutionInputSerializer,
        responses=s.AnomalySerializer,
        operation_id="iaa_anomalies_resolve",
    )
    def post(self, request, pk: int):
        serializer = s.AnomalyResolutionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = _actor(request)
        anomaly = anomaly_services.resolve_or_escalate_anomaly(
            anomaly_id=pk,
            actor_id=principal.user_id,
            actor_role=getattr(principal, "active_role", "finance_staff"),
            action=data["action"],
            remarks=data["remarks"],
        )
        return Response(s.AnomalySerializer(anomaly).data)


class AuditObservationListCreateView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.audit.view")]

    @extend_schema(responses=s.AuditObservationSerializer(many=True), operation_id="iaa_audit_list")
    def get(self, request):
        status_filter = request.query_params.get("status")
        observations = audit_selectors.get_audit_observations(_actor(request), status=status_filter)
        return Response(s.AuditObservationSerializer(observations, many=True).data)

    @extend_schema(
        request=s.RaiseAuditObservationInputSerializer,
        responses={201: s.AuditObservationSerializer},
        operation_id="iaa_audit_create",
    )
    def post(self, request):
        if not _actor(request).has_permission("iaa.audit.raise"):
            raise PermissionDeniedError()
        serializer = s.RaiseAuditObservationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = _actor(request)
        obs = audit_services.raise_audit_observation(
            auditor_id=principal.user_id,
            acting_role=getattr(principal, "active_role", "auditor"),
            department=data["department"],
            title=data["title"],
            description=data["description"],
            reference_type=data.get("reference_type", ""),
            reference_id=data.get("reference_id"),
        )
        return Response(s.AuditObservationSerializer(obs).data, status=status.HTTP_201_CREATED)


class AuditObservationRespondView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.audit.respond")]

    @extend_schema(
        request=s.AuditObservationResponseInputSerializer,
        responses=s.AuditObservationSerializer,
        operation_id="iaa_audit_respond",
    )
    def post(self, request, pk: int):
        serializer = s.AuditObservationResponseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        principal = _actor(request)
        obs = audit_services.respond_to_audit_observation(
            observation_id=pk,
            user_id=principal.user_id,
            acting_role=getattr(principal, "active_role", "basic_user"),
            response_text=serializer.validated_data["response_text"],
        )
        return Response(s.AuditObservationSerializer(obs).data)


class AuditObservationCloseView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.audit.close")]

    @extend_schema(
        request=s.AuditObservationClosureInputSerializer,
        responses=s.AuditObservationSerializer,
        operation_id="iaa_audit_close",
    )
    def post(self, request, pk: int):
        serializer = s.AuditObservationClosureInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = _actor(request)
        obs = audit_services.review_and_close_observation(
            observation_id=pk,
            auditor_id=principal.user_id,
            acting_role=getattr(principal, "active_role", "auditor"),
            is_satisfactory=data["is_satisfactory"],
            remarks=data["remarks"],
        )
        return Response(s.AuditObservationSerializer(obs).data)


class ReportSummaryView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.report.view")]

    @extend_schema(responses={200: dict}, operation_id="iaa_reports_summary")
    def get(self, request):
        summary = report_selectors.get_dashboard_summary(_actor(request))
        return Response(summary)


class ReportExportView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.report.view")]

    @extend_schema(responses={200: str}, operation_id="iaa_reports_export")
    def get(self, request):
        reqs = request_selectors.get_requests(_actor(request))
        header = ["ID", "Title", "Department", "Type", "Amount", "Status", "Created At"]
        rows = [
            [
                str(r.id),
                r.title,
                r.department,
                r.request_type,
                str(r.total_amount),
                r.status,
                str(r.created_at),
            ]
            for r in reqs
        ]
        return stream_csv(filename="iaa_financial_report.csv", header=header, rows=rows)


class ConfigurationView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.config.manage")]

    @extend_schema(responses=s.IAAConfigurationSerializer, operation_id="iaa_config_get")
    def get(self, request):
        config = config_selectors.get_active_configuration()
        return Response(s.IAAConfigurationSerializer(config).data)

    @extend_schema(
        request=s.IAAConfigurationSerializer,
        responses=s.IAAConfigurationSerializer,
        operation_id="iaa_config_update",
    )
    def put(self, request):
        config = config_selectors.get_active_configuration()
        serializer = s.IAAConfigurationSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DepartmentBudgetView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("iaa.config.manage")]

    @extend_schema(
        responses=s.DepartmentBudgetSerializer(many=True), operation_id="iaa_budgets_list"
    )
    def get(self, request):
        budgets = config_selectors.DepartmentBudget.objects.all()
        return Response(s.DepartmentBudgetSerializer(budgets, many=True).data)

    @extend_schema(
        request=s.DepartmentBudgetSerializer,
        responses={201: s.DepartmentBudgetSerializer},
        operation_id="iaa_budgets_create",
    )
    def post(self, request):
        serializer = s.DepartmentBudgetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        budget = serializer.save()
        return Response(s.DepartmentBudgetSerializer(budget).data, status=status.HTTP_201_CREATED)
