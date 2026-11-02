"""IAA REST API. All authorization is repeated in the service layer."""
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant
from modules.iaa.api import serializers as s
from modules.iaa.models import (
    ApprovalRule, ApprovalStep, DashboardNotification, FinancialRecord,
    FinancialYearPolicy, RoleAssignment,
)
from modules.iaa.services import iaa as service

MODULE = HasModuleGrant("iaa")


def actor(request):
    return getattr(request, "principal", None)


def page(qs, serializer):
    rows = list(qs[:200])
    return {"results": serializer(rows, many=True).data, "count": len(rows)}


class IAAView(APIView):
    permission_classes = [MODULE]


class FinancialRecordListCreateView(IAAView):
    @extend_schema(operation_id="iaa_requests_list", responses=s.PageSerializer)
    def get(self, request):
        role = service.actor_role(actor(request))
        permission = "iaa.request.view_self" if role in service.BASIC_ROLES else "iaa.request.view"
        service.require(actor(request), permission)
        qs = service.visible_records(actor(request))
        kind = request.query_params.get("kind")
        if kind:
            qs = qs.filter(record_kind=kind)
        state = request.query_params.get("status")
        if state:
            qs = qs.filter(status=state)
        return Response(page(qs.order_by("-created_at"), s.FinancialRecordSerializer))

    @extend_schema(request=s.FinancialRecordWriteSerializer, responses=s.FinancialRecordSerializer)
    def post(self, request):
        serializer = s.FinancialRecordWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = service.create_record(actor(request), serializer.validated_data, kind="expense_voucher")
        return Response(s.FinancialRecordSerializer(row).data, status=status.HTTP_201_CREATED)


class FinancialRecordDetailView(IAAView):
    @extend_schema(operation_id="iaa_request_retrieve", responses=s.FinancialRecordSerializer)
    def get(self, request, pk):
        role = service.actor_role(actor(request))
        service.require(actor(request), "iaa.request.view_self" if role in service.BASIC_ROLES else "iaa.request.view")
        row = service.get_record(actor(request), pk)
        return Response(s.FinancialRecordSerializer(row).data)

    @extend_schema(request=s.FinancialRecordWriteSerializer, responses=s.FinancialRecordSerializer)
    def patch(self, request, pk):
        serializer = s.FinancialRecordWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        row = service.update_draft(actor(request), pk, serializer.validated_data)
        return Response(s.FinancialRecordSerializer(row).data)


class FinancialRecordSubmitView(IAAView):
    @extend_schema(request=None, responses=s.FinancialRecordSerializer)
    def post(self, request, pk):
        row = service.submit_record(actor(request), pk)
        return Response(s.FinancialRecordSerializer(row).data)


class RecordAttachmentView(IAAView):
    @extend_schema(request=s.SupportingDocumentInputSerializer, responses=s.SupportingDocumentSerializer)
    def post(self, request, pk):
        serializer = s.SupportingDocumentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = service.attach_document(actor(request), pk, serializer.validated_data)
        return Response(s.SupportingDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class FinanceQueryView(IAAView):
    @extend_schema(responses=s.PageSerializer)
    def get(self, request, pk):
        row = service.get_record(actor(request), pk)
        service.require(actor(request), "iaa.request.view_self" if service.actor_role(actor(request)) in service.BASIC_ROLES else "iaa.request.view")
        return Response(page(row.queries.order_by("created_at"), s.FinanceQuerySerializer))

    @extend_schema(request=s.QueryInputSerializer, responses=s.FinanceQuerySerializer)
    def post(self, request, pk):
        serializer = s.QueryInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = service.request_clarification(actor(request), pk, serializer.validated_data["question"])
        return Response(s.FinanceQuerySerializer(query).data, status=status.HTTP_201_CREATED)


class FinanceQueryRespondView(IAAView):
    @extend_schema(request=s.QueryResponseInputSerializer, responses=s.FinanceQuerySerializer)
    def post(self, request, pk):
        serializer = s.QueryResponseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = service.respond_to_query(actor(request), pk, serializer.validated_data["response"])
        return Response(s.FinanceQuerySerializer(query).data)


class FinanceQueueView(IAAView):
    @extend_schema(responses=s.PageSerializer)
    def get(self, request):
        service.require(actor(request), "iaa.finance.validate", roles=service.FINANCE_ROLES)
        qs = FinancialRecord.objects.filter(
            status__in=("submitted", "query_responded")).order_by("submitted_at")
        return Response(page(qs, s.FinancialRecordSerializer))


class FinanceValidateView(IAAView):
    @extend_schema(request=s.FinanceValidationInputSerializer, responses=s.FinancialRecordSerializer)
    def post(self, request, pk):
        serializer = s.FinanceValidationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = service.finance_validate(actor(request), pk, **serializer.validated_data)
        return Response(s.FinancialRecordSerializer(row).data)


class TAListCreateView(IAAView):
    @extend_schema(responses=s.PageSerializer)
    def get(self, request):
        role = service.actor_role(actor(request))
        service.require(actor(request), "iaa.ta.view_self" if role in service.BASIC_ROLES else "iaa.request.view")
        qs = service.visible_records(actor(request)).filter(record_kind="ta")
        state = request.query_params.get("status")
        if state:
            qs = qs.filter(status=state)
        return Response(page(qs.order_by("-created_at"), s.FinancialRecordSerializer))

    @extend_schema(request=s.FinancialRecordWriteSerializer, responses=s.FinancialRecordSerializer)
    def post(self, request):
        serializer = s.FinancialRecordWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = service.create_record(actor(request), serializer.validated_data, kind="ta")
        return Response(s.FinancialRecordSerializer(row).data, status=status.HTTP_201_CREATED)


class TASubmitView(IAAView):
    @extend_schema(request=None, responses=s.FinancialRecordSerializer)
    def post(self, request, pk):
        row = service.get_record(actor(request), pk)
        if row.record_kind != "ta":
            raise NotFoundError("TA claim not found.")
        row = service.submit_record(actor(request), pk)
        return Response(s.FinancialRecordSerializer(row).data)


class TAVerifyView(IAAView):
    @extend_schema(request=None, responses=s.FinancialRecordSerializer)
    def post(self, request, pk):
        row = FinancialRecord.objects.filter(pk=pk, record_kind="ta").first()
        if row is None:
            raise NotFoundError("TA claim not found.")
        row = service.finance_validate(actor(request), pk)
        return Response(s.FinancialRecordSerializer(row).data)


class ApprovalQueueView(IAAView):
    @extend_schema(responses=s.PageSerializer)
    def get(self, request):
        role = service.require(actor(request), "iaa.approval.view", roles=service.AUTHORITY_ROLES)
        qs = ApprovalStep.objects.filter(status="pending", authority_role=role)
        qs = qs.filter(Q(assigned_user_id__isnull=True) | Q(assigned_user_id=actor(request).user_id))
        return Response(page(qs.select_related("record").order_by("due_at"), s.ApprovalStepSerializer))


class ApprovalDecisionView(IAAView):
    @extend_schema(request=s.ApprovalDecisionInputSerializer, responses=s.ApprovalStepSerializer)
    def post(self, request, pk):
        serializer = s.ApprovalDecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        step = service.decide_approval(actor(request), pk, **serializer.validated_data)
        return Response(s.ApprovalStepSerializer(step).data)


class RecordCompletionView(IAAView):
    @extend_schema(request=None, responses=s.FinancialRecordSerializer)
    def post(self, request, pk):
        row = service.record_completion(actor(request), pk)
        return Response(s.FinancialRecordSerializer(row).data)


class AnomalyListCreateView(IAAView):
    @extend_schema(responses=s.PageSerializer)
    def get(self, request):
        service.require(actor(request), "iaa.anomaly.view",
                        roles=service.FINANCE_ROLES | service.AUDIT_ROLES | service.AUTHORITY_ROLES | service.BASIC_ROLES)
        qs = service.visible_anomalies(actor(request))
        state = request.query_params.get("status")
        if state:
            qs = qs.filter(status=state)
        return Response(page(qs, s.AnomalySerializer))

    @extend_schema(request=s.AnomalyInputSerializer, responses=s.AnomalySerializer)
    def post(self, request):
        serializer = s.AnomalyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        anomaly = service.flag_anomaly(actor(request), serializer.validated_data)
        return Response(s.AnomalySerializer(anomaly).data, status=status.HTTP_201_CREATED)


class AnomalyResolveView(IAAView):
    @extend_schema(request=s.AnomalyResolutionInputSerializer, responses=s.AnomalySerializer)
    def post(self, request, pk):
        serializer = s.AnomalyResolutionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        anomaly = service.resolve_anomaly(actor(request), pk, **serializer.validated_data)
        return Response(s.AnomalySerializer(anomaly).data)


class AuditFinancialRecordsView(IAAView):
    @extend_schema(responses=s.PageSerializer)
    def get(self, request):
        service.require(actor(request), "iaa.audit.review", roles=service.AUDIT_ROLES)
        qs = FinancialRecord.objects.all().order_by("-updated_at")
        return Response(page(qs, s.FinancialRecordSerializer))


class ObservationListCreateView(IAAView):
    @extend_schema(responses=s.PageSerializer)
    def get(self, request):
        role = service.actor_role(actor(request))
        permission = "iaa.audit.review" if role in service.AUDIT_ROLES else "iaa.audit.observation.respond"
        service.require(actor(request), permission, roles=service.AUDIT_ROLES | service.BASIC_ROLES)
        qs = service.visible_observations(actor(request))
        state = request.query_params.get("status")
        if state:
            qs = qs.filter(status=state)
        return Response(page(qs, s.AuditObservationSerializer))

    @extend_schema(request=s.ObservationInputSerializer, responses=s.AuditObservationSerializer)
    def post(self, request):
        serializer = s.ObservationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obs = service.raise_observation(actor(request), serializer.validated_data)
        return Response(s.AuditObservationSerializer(obs).data, status=status.HTTP_201_CREATED)


class ObservationRespondView(IAAView):
    @extend_schema(request=s.ObservationResponseInputSerializer, responses=s.ObservationResponseSerializer)
    def post(self, request, pk):
        serializer = s.ObservationResponseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = service.respond_observation(actor(request), pk, **serializer.validated_data)
        return Response(s.ObservationResponseSerializer(response).data, status=status.HTTP_201_CREATED)


class ObservationVerifyView(IAAView):
    @extend_schema(request=s.ObservationVerifyInputSerializer, responses=s.AuditObservationSerializer)
    def post(self, request, pk):
        serializer = s.ObservationVerifyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obs = service.verify_observation(actor(request), pk, **serializer.validated_data)
        return Response(s.AuditObservationSerializer(obs).data)


class ReportSummaryView(IAAView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(service.report_summary(actor(request)))


class ReportExportView(IAAView):
    @extend_schema(responses={(200, "text/csv"): OpenApiTypes.STR})
    def get(self, request):
        service.require(actor(request), "iaa.report.export",
                        roles=service.FINANCE_ROLES | service.AUTHORITY_ROLES | service.AUDIT_ROLES)
        csv_data = service.build_csv_report(actor(request))
        response = HttpResponse(csv_data, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="iaa-report.csv"'
        return response


class NotificationListView(IAAView):
    @extend_schema(responses=s.PageSerializer)
    def get(self, request):
        service.require(actor(request), "iaa.notification.view")
        qs = DashboardNotification.objects.filter(recipient_user_id=actor(request).user_id)
        return Response(page(qs, s.NotificationSerializer))


class NotificationReadView(IAAView):
    @extend_schema(request=None, responses=s.NotificationSerializer)
    def post(self, request, pk):
        service.require(actor(request), "iaa.notification.view")
        row = DashboardNotification.objects.filter(pk=pk, recipient_user_id=actor(request).user_id).first()
        if row is None:
            raise NotFoundError("Notification not found.")
        row.read_at = timezone.now()
        row.save(update_fields=["read_at"])
        return Response(s.NotificationSerializer(row).data)


class ActiveRoleView(IAAView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        current = service.actor_role(actor(request))
        return Response({"active_role": current,
                         "available_roles": [service.normalize_role(x) for x in actor(request).roles]})

    @extend_schema(request=s.RoleSwitchSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = s.RoleSwitchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selection = service.switch_active_role(
            actor(request), serializer.validated_data["role"], request.auth)
        return Response({"active_role": selection.role})


class RoleAssignmentView(IAAView):
    @extend_schema(responses=s.PageSerializer)
    def get(self, request):
        service.require(actor(request), "iaa.configuration.manage",
                        roles=service.ADMIN_ROLES, operational=False)
        return Response(page(RoleAssignment.objects.order_by("user_id"), s.RoleAssignmentSerializer))

    @extend_schema(request=s.RoleAssignmentInputSerializer, responses=s.RoleAssignmentSerializer)
    def post(self, request):
        serializer = s.RoleAssignmentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = service.assign_role(actor(request), user_id=serializer.validated_data["user_id"],
                                  role_name=serializer.validated_data["role"],
                                  active=serializer.validated_data["is_active"])
        return Response(s.RoleAssignmentSerializer(row).data, status=status.HTTP_201_CREATED)


class ApprovalRuleView(IAAView):
    @extend_schema(responses=s.PageSerializer)
    def get(self, request):
        service.require(actor(request), "iaa.configuration.manage",
                        roles=service.ADMIN_ROLES, operational=False)
        return Response(page(ApprovalRule.objects.order_by("priority"), s.ApprovalRuleSerializer))

    @extend_schema(request=s.ApprovalRuleInputSerializer, responses=s.ApprovalRuleSerializer)
    def post(self, request):
        serializer = s.ApprovalRuleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = service.configure_approval_rule(actor(request), serializer.validated_data)
        return Response(s.ApprovalRuleSerializer(row).data, status=status.HTTP_201_CREATED)


class FinancialYearPolicyView(IAAView):
    @extend_schema(responses=s.PageSerializer)
    def get(self, request):
        service.require(actor(request), "iaa.configuration.manage",
                        roles=service.ADMIN_ROLES, operational=False)
        return Response(page(FinancialYearPolicy.objects.order_by("-starts_on"), s.FinancialYearPolicySerializer))

    @extend_schema(request=s.FinancialYearPolicyInputSerializer, responses=s.FinancialYearPolicySerializer)
    def post(self, request):
        serializer = s.FinancialYearPolicyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = service.configure_financial_year(actor(request), serializer.validated_data)
        return Response(s.FinancialYearPolicySerializer(row).data, status=status.HTTP_201_CREATED)

class DepartmentBudgetView(IAAView):
    @extend_schema(responses=s.PageSerializer)
    def get(self, request):
        service.require(actor(request), "iaa.configuration.manage",
                        roles=service.ADMIN_ROLES, operational=False)
        from modules.iaa.models import DepartmentBudget
        return Response(page(DepartmentBudget.objects.order_by("department", "financial_year"),
                             s.DepartmentBudgetSerializer))

    @extend_schema(request=s.DepartmentBudgetInputSerializer, responses=s.DepartmentBudgetSerializer)
    def post(self, request):
        serializer = s.DepartmentBudgetInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = service.configure_department_budget(actor(request), serializer.validated_data)
        return Response(s.DepartmentBudgetSerializer(row).data, status=status.HTTP_201_CREATED)


class AuditLogListView(IAAView):
    @extend_schema(responses=s.PageSerializer)
    def get(self, request):
        qs = service.audit_logs_for(actor(request))
        action = request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)
        return Response(page(qs, s.AuditLogSerializer))
