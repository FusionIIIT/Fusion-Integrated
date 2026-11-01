"""Thin HTTP views: parse and scope here, enforce rules in services."""
from __future__ import annotations

import csv

from django.db.models import Count
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import ConflictError, PermissionDeniedError
from core.files.validators import sanitise_filename
from fusion_auth.permissions import HasModuleGrant, IsAuthenticatedPrincipal
from modules.iaa.api import serializers as s
from modules.iaa.api.permissions import IaaAnyPermission, IaaPermission
from modules.iaa.domain import state_machine as sm
from modules.iaa.models import (
    ActionHistory, Anomaly, ApprovalDecision, ApprovalRouteRule,
    AuditObservation, AuditResponse, AutomaticAnomalyRule, DepartmentBudget,
    Evidence, ExpenseVoucherRequest, FinancialYear, IaaNotification,
    IaaRoleAssignment, PolicyParameter, TravelAllowanceClaim,
)
from modules.iaa.selectors import records as selectors
from modules.iaa.services import configuration, records
from modules.iaa.services.authz import (
    IaaAccessError, active_role, available_roles,
)
from modules.iaa.services.records import IaaRuleError


def _role(request):
    role = active_role(request)
    if not role:
        raise PermissionDenied("Select an assigned active IAA role first.")
    return role


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except IaaAccessError as exc:
        raise PermissionDeniedError(str(exc), code="iaa_permission_denied") from exc
    except IaaRuleError as exc:
        raise ConflictError(str(exc), code=exc.code) from exc


def _serialize(serializer, data, *, many=False):
    return serializer(data, many=many).data


class ActiveRolesView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IsAuthenticatedPrincipal]

    def get(self, request):
        return Response({"roles": available_roles(request.principal),
                         "active_role": active_role(request)})

    def post(self, request):
        data = s.ActiveRoleSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        role = _run(records.switch_role, principal=request.principal,
                    role=data.validated_data["active_role"])
        return Response({"active_role": role, "roles": available_roles(request.principal)})


class RequestCollectionView(APIView):
    def get_permissions(self):
        code = IaaAnyPermission("iaa.request.view", "iaa.request.view_self") if self.request.method == "GET" else IaaPermission("iaa.request.create")
        return [HasModuleGrant("iaa")(), code()]

    def get(self, request):
        role = _role(request)
        qs = selectors.requests_for(request.principal, role)
        if role == sm.FINANCE:
            qs = qs.order_by("created_at", "id")
        return Response({"results": _serialize(s.RequestSerializer, qs, many=True)})

    def post(self, request):
        data = s.RequestUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        record = _run(records.save_request, principal=request.principal,
                      role=_role(request), values=data.validated_data)
        return Response(s.RequestSerializer(record).data, status=status.HTTP_201_CREATED)


class RequestDetailView(APIView):
    permission_classes = [HasModuleGrant("iaa"),
                          IaaAnyPermission("iaa.request.view", "iaa.request.view_self")]

    def get(self, request, pk):
        record = get_object_or_404(selectors.requests_for(request.principal, _role(request)), pk=pk)
        return Response(s.RequestSerializer(record).data)

    def put(self, request, pk):
        if not records_permission(request, "iaa.request.update"):
            raise PermissionDeniedError("Only the request creator may update a draft.")
        data = s.RequestUpdateSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        record = _run(records.save_request, principal=request.principal,
                      role=_role(request), values=data.validated_data,
                      request_id=pk)
        return Response(s.RequestSerializer(record).data)


def records_permission(request, code):
    return records_role_has_permission(request, code)


def records_role_has_permission(request, code):
    from modules.iaa.services.authz import role_has_permission
    role = active_role(request)
    return bool(role and role_has_permission(request.principal, role, code))


class RequestSubmitView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.request.create")]

    def post(self, request, pk):
        record = _run(records.submit_request, principal=request.principal,
                      role=_role(request), request_id=pk)
        return Response(s.RequestSerializer(record).data)


class RequestReviewView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.request.review")]

    def post(self, request, pk):
        data = s.RequestReviewSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        record = _run(records.review_request, principal=request.principal,
                      role=_role(request), request_id=pk, **data.validated_data)
        return Response(s.RequestSerializer(record).data)


class RequestResponseView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.request.update")]

    def post(self, request, pk):
        data = s.ClarificationResponseSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        record = _run(records.respond_request, principal=request.principal,
                      role=_role(request), request_id=pk, **data.validated_data)
        return Response(s.RequestSerializer(record).data)


class RequestDecisionView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.request.approve")]

    def post(self, request, pk):
        data = s.DecisionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        record = _run(records.decide_request, principal=request.principal,
                      role=_role(request), request_id=pk, **data.validated_data)
        return Response(s.RequestSerializer(record).data)


class RequestRecordView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.request.review")]

    def post(self, request, pk):
        record = _run(records.record_request, principal=request.principal,
                      role=_role(request), request_id=pk,
                      processing_details=request.data.get("processing_details", ""))
        return Response(s.RequestSerializer(record).data)


class ClaimCollectionView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        code = IaaAnyPermission("iaa.ta_claim.view", "iaa.ta_claim.view_self") if self.request.method == "GET" else IaaPermission("iaa.ta_claim.create")
        return [HasModuleGrant("iaa")(), code()]

    def get(self, request):
        qs = selectors.claims_for(request.principal, _role(request))
        return Response({"results": _serialize(s.ClaimSerializer, qs, many=True)})

    def post(self, request):
        data = s.ClaimCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        evidence = values.pop("evidence")
        claim = _run(records.submit_ta_claim, principal=request.principal,
                     role=_role(request), values=values, evidence_files=evidence)
        return Response(s.ClaimSerializer(claim).data, status=status.HTTP_201_CREATED)


class ClaimDetailView(APIView):
    permission_classes = [HasModuleGrant("iaa"),
                          IaaAnyPermission("iaa.ta_claim.view", "iaa.ta_claim.view_self")]

    def get(self, request, pk):
        claim = get_object_or_404(selectors.claims_for(request.principal, _role(request)), pk=pk)
        return Response(s.ClaimSerializer(claim).data)


class ClaimReviewView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.ta_claim.review")]

    def post(self, request, pk):
        data = s.TaReviewSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        claim = _run(records.review_ta_claim, principal=request.principal,
                     role=_role(request), claim_id=pk, **data.validated_data)
        return Response(s.ClaimSerializer(claim).data)


class ClaimResponseView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.ta_claim.update")]

    def post(self, request, pk):
        data = s.ClarificationResponseSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        claim = _run(records.respond_ta_claim, principal=request.principal,
                     role=_role(request), claim_id=pk, **data.validated_data)
        return Response(s.ClaimSerializer(claim).data)


class ClaimDecisionView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.ta_claim.approve")]

    def post(self, request, pk):
        data = s.DecisionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        claim = _run(records.decide_ta_claim, principal=request.principal,
                     role=_role(request), claim_id=pk, **data.validated_data)
        return Response(s.ClaimSerializer(claim).data)


class ClaimRecordView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.ta_claim.review")]

    def post(self, request, pk):
        claim = _run(records.record_ta_claim, principal=request.principal,
                     role=_role(request), claim_id=pk,
                     processing_details=request.data.get("processing_details", ""))
        return Response(s.ClaimSerializer(claim).data)


class AnomalyCollectionView(APIView):
    def get_permissions(self):
        code = IaaPermission("iaa.anomaly.view") if self.request.method == "GET" else IaaPermission("iaa.anomaly.create")
        return [HasModuleGrant("iaa")(), code()]

    def get(self, request):
        rows = selectors.anomalies_for(request.principal, _role(request))
        return Response({"results": _serialize(s.AnomalySerializer, rows, many=True)})

    def post(self, request):
        data = s.AnomalyCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        anomaly = _run(records.flag_anomaly, principal=request.principal,
                       role=_role(request), **data.validated_data)
        return Response(s.AnomalySerializer(anomaly).data, status=status.HTTP_201_CREATED)


class AnomalyOutcomeView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.anomaly.update")]

    def post(self, request, pk):
        data = s.AnomalyOutcomeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        anomaly = _run(records.resolve_anomaly, principal=request.principal,
                       role=_role(request), anomaly_id=pk, **data.validated_data)
        return Response(s.AnomalySerializer(anomaly).data)


class AuditRecordsView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.audit_record.view")]

    def get(self, request):
        requests = selectors.requests_for(request.principal, _role(request))
        claims = selectors.claims_for(request.principal, _role(request))
        return Response({"requests": _serialize(s.RequestSerializer, requests, many=True),
                         "ta_claims": _serialize(s.ClaimSerializer, claims, many=True)})


class ObservationCollectionView(APIView):
    def get_permissions(self):
        code = IaaAnyPermission("iaa.audit_observation.view",
                                "iaa.audit_observation.create") if self.request.method == "GET" else IaaPermission("iaa.audit_observation.create")
        return [HasModuleGrant("iaa")(), code()]

    def get(self, request):
        rows = selectors.observations_for(request.principal, _role(request))
        return Response({"results": _serialize(s.ObservationSerializer, rows, many=True)})

    def post(self, request):
        data = s.ObservationCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        observation = _run(records.raise_observation, principal=request.principal,
                           role=_role(request), **data.validated_data)
        return Response(s.ObservationSerializer(observation).data,
                        status=status.HTTP_201_CREATED)


class ObservationResponseView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.audit_observation.update")]

    def post(self, request, pk):
        data = s.ObservationResponseSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        answer = _run(records.respond_observation, principal=request.principal,
                      role=_role(request), observation_id=pk, **data.validated_data)
        return Response({"id": answer.pk, "observation_id": answer.observation_id,
                         "response": answer.response, "submitted_at": answer.submitted_at})


class ObservationVerifyView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.audit_observation.update")]

    def post(self, request, pk):
        data = s.ObservationVerifySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        observation = _run(records.verify_observation, principal=request.principal,
                           role=_role(request), observation_id=pk,
                           **data.validated_data)
        return Response(s.ObservationSerializer(observation).data)


class RecordHistoryView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaAnyPermission(
        "iaa.request.view", "iaa.request.view_self", "iaa.ta_claim.view",
        "iaa.ta_claim.view_self", "iaa.audit_record.view", "iaa.anomaly.view")]

    def get(self, request, record_type, pk):
        role = _role(request)
        if record_type == "request":
            get_object_or_404(selectors.requests_for(request.principal, role), pk=pk)
        elif record_type == "ta_claim":
            get_object_or_404(selectors.claims_for(request.principal, role), pk=pk)
        elif record_type == "audit_observation":
            get_object_or_404(selectors.observations_for(request.principal, role), pk=pk)
        elif record_type == "anomaly":
            get_object_or_404(selectors.anomalies_for(request.principal, role), pk=pk)
        elif record_type != "anomaly":
            raise NotFound()
        rows = ActionHistory.objects.filter(record_type=record_type, record_id=pk)
        return Response({"results": _serialize(s.ActionHistorySerializer, rows, many=True)})


class EvidenceView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [HasModuleGrant("iaa"), IaaAnyPermission(
        "iaa.request.view", "iaa.request.view_self", "iaa.request.update",
        "iaa.ta_claim.view", "iaa.ta_claim.view_self", "iaa.ta_claim.update",
        "iaa.audit_observation.view", "iaa.audit_observation.update")]

    def get(self, request):
        record_type = request.query_params.get("record_type", "")
        record_id = request.query_params.get("record_id")
        if not record_id or not record_id.isdigit():
            raise ConflictError("record_type and numeric record_id are required.",
                                code="invalid_evidence_scope")
        self._check_scope(request, record_type, int(record_id), write=False)
        rows = Evidence.objects.filter(record_type=record_type, record_id=record_id)
        return Response({"results": _serialize(s.EvidenceSerializer, rows, many=True)})

    def post(self, request):
        data = s.EvidenceSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        self._check_scope(request, values["record_type"], values["record_id"], write=True)
        file = values["file"]
        evidence = Evidence.objects.create(
            record_type=values["record_type"], record_id=values["record_id"],
            purpose=values.get("purpose", ""), file=file,
            original_filename=sanitise_filename(file.name),
            uploaded_by_id=request.principal.user_id)
        ActionHistory.objects.create(
            record_type=values["record_type"], record_id=values["record_id"],
            action="evidence_attached", actor_user_id=request.principal.user_id,
            actor_role=_role(request), details={"evidence_id": evidence.pk,
                                               "purpose": evidence.purpose})
        return Response(s.EvidenceSerializer(evidence).data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _check_scope(request, record_type, record_id, *, write):
        role = _role(request)
        if record_type == "request":
            row = get_object_or_404(selectors.requests_for(request.principal, role), pk=record_id)
            if write and role == sm.BASIC_USER and row.status not in ("Draft", "Query Raised"):
                raise PermissionDeniedError("Submitted request evidence is locked outside a query response.")
        elif record_type == "ta_claim":
            row = get_object_or_404(selectors.claims_for(request.principal, role), pk=record_id)
            if write and role == sm.BASIC_USER and row.status not in ("Query Raised",):
                raise PermissionDeniedError("TA claim evidence can be added only for a clarification response.")
        elif record_type == "audit_observation":
            get_object_or_404(selectors.observations_for(request.principal, role), pk=record_id)
        else:
            raise NotFound()


class EvidenceDownloadView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaAnyPermission(
        "iaa.request.view", "iaa.request.view_self", "iaa.ta_claim.view",
        "iaa.ta_claim.view_self", "iaa.audit_record.view",
        "iaa.audit_observation.view")]

    def get(self, request, pk):
        evidence = get_object_or_404(Evidence.objects.filter(pk=pk))
        EvidenceView._check_scope(request, evidence.record_type,
                                  evidence.record_id, write=False)
        stream = evidence.file.open("rb")
        return FileResponse(stream, as_attachment=True,
                            filename=evidence.original_filename)


class NotificationsView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.notification.view")]

    def get(self, request):
        rows = selectors.notifications_for(request.principal, _role(request))
        return Response({"results": _serialize(s.NotificationSerializer, rows, many=True)})

    def patch(self, request, pk):
        row = get_object_or_404(IaaNotification.objects.filter(
            user_id=request.principal.user_id, actor_role__in=("", _role(request))), pk=pk)
        row.read_at = timezone.now()
        row.save(update_fields=("read_at",))
        return Response(s.NotificationSerializer(row).data)


class ReportsView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.report.view")]

    def get(self, request):
        role = _role(request)
        requests = selectors.requests_for(request.principal, role)
        claims = selectors.claims_for(request.principal, role)
        anomalies = selectors.anomalies_for(request.principal, role)
        observations = selectors.observations_for(request.principal, role)
        def counts(qs):
            return list(qs.values("status").annotate(count=Count("id")).order_by("status"))
        decisions = ApprovalDecision.objects.filter(step__assigned_user_id=request.principal.user_id)
        elapsed = [max(0, (d.decided_at - d.step.created_at).total_seconds())
                   for d in decisions.select_related("step")]
        average = sum(elapsed) / len(elapsed) if elapsed else None
        return Response({"requests": counts(requests), "ta_claims": counts(claims),
                         "anomalies": counts(anomalies),
                         "audit_observations": counts(observations),
                         "approval_turnaround_seconds_average": average})


class ReportExportView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.report.export")]

    def get(self, request):
        role = _role(request)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = "attachment; filename=iaa-report.csv"
        writer = csv.writer(response)
        writer.writerow(("record_type", "id", "status", "department", "created_at"))
        for row in selectors.requests_for(request.principal, role):
            writer.writerow(("request", row.pk, row.status, row.department, row.created_at.isoformat()))
        for row in selectors.claims_for(request.principal, role):
            writer.writerow(("ta_claim", row.pk, row.status, row.department, row.created_at.isoformat()))
        for row in selectors.anomalies_for(request.principal, role):
            writer.writerow(("anomaly", row.pk, row.status, "", row.created_at.isoformat()))
        for row in selectors.observations_for(request.principal, role):
            writer.writerow(("audit_observation", row.pk, row.status, row.department, row.created_at.isoformat()))
        return response


class RoleAssignmentsView(APIView):
    def get_permissions(self):
        code = IaaPermission("iaa.role.assign") if self.request.method == "POST" else IaaPermission("iaa.role.view")
        return [HasModuleGrant("iaa")(), code()]

    def get(self, request):
        role = _role(request)
        rows = IaaRoleAssignment.objects.filter(is_active=True)
        if role != sm.ADMIN:
            rows = rows.filter(user_id=request.principal.user_id)
        return Response({"results": _serialize(s.RoleAssignmentSerializer, rows, many=True),
                         "available_roles": available_roles(request.principal)})

    def post(self, request):
        data = s.AssignmentCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        assignment = _run(configuration.assign_role, principal=request.principal,
                          role=_role(request), user_id=values["user_id"],
                          assigned_role=values["role"],
                          department=values.get("department", ""))
        return Response(s.RoleAssignmentSerializer(assignment).data,
                        status=status.HTTP_201_CREATED)


class RoleAssignmentDetailView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.role.assign")]

    def delete(self, request, pk):
        assignment = _run(configuration.revoke_role, principal=request.principal,
                          role=_role(request), assignment_id=pk)
        return Response(s.RoleAssignmentSerializer(assignment).data)


class ConfigurationView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.configuration.manage")]

    def get(self, request):
        return Response({
            "financial_years": _serialize(s.FinancialYearSerializer,
                                           FinancialYear.objects.all(), many=True),
            "budgets": _serialize(s.BudgetSerializer, DepartmentBudget.objects.select_related("financial_year"), many=True),
            "approval_routes": _serialize(s.RouteSerializer, ApprovalRouteRule.objects.all(), many=True),
            "policy_parameters": _serialize(s.PolicySerializer, PolicyParameter.objects.all(), many=True),
            "automatic_anomaly_rules": list(AutomaticAnomalyRule.objects.values()),
        })


class FinancialYearView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.configuration.manage")]

    def post(self, request, pk=None):
        data = s.FinancialYearWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        row = _run(configuration.save_financial_year, principal=request.principal,
                   role=_role(request), values=data.validated_data,
                   financial_year_id=pk)
        return Response(s.FinancialYearSerializer(row).data,
                        status=status.HTTP_201_CREATED if pk is None else status.HTTP_200_OK)


class DepartmentBudgetView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.configuration.manage")]

    def post(self, request, pk=None):
        data = s.BudgetWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        row = _run(configuration.save_department_budget, principal=request.principal,
                   role=_role(request), values=data.validated_data, budget_id=pk)
        return Response(s.BudgetSerializer(row).data,
                        status=status.HTTP_201_CREATED if pk is None else status.HTTP_200_OK)


class ApprovalRouteView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.configuration.manage")]

    def post(self, request, pk=None):
        data = s.RouteWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        row = _run(configuration.save_route, principal=request.principal,
                   role=_role(request), values=data.validated_data, route_id=pk)
        return Response(s.RouteSerializer(row).data,
                        status=status.HTTP_201_CREATED if pk is None else status.HTTP_200_OK)


class PolicyParameterView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.configuration.manage")]

    def post(self, request, pk=None):
        data = s.PolicyWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        row = _run(configuration.save_policy_parameter, principal=request.principal,
                   role=_role(request), values=data.validated_data, parameter_id=pk)
        return Response(s.PolicySerializer(row).data,
                        status=status.HTTP_201_CREATED if pk is None else status.HTTP_200_OK)


class AutomaticAnomalyRuleView(APIView):
    permission_classes = [HasModuleGrant("iaa"), IaaPermission("iaa.configuration.manage")]

    def post(self, request):
        data = s.AutoAnomalyRuleSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        row = _run(configuration.save_anomaly_rule, principal=request.principal,
                   role=_role(request), values=data.validated_data)
        return Response({"id": row.pk, "condition": row.condition,
                         "category": row.category, "resolver_role": row.resolver_role,
                         "assigned_user_id": row.assigned_user_id,
                         "is_active": row.is_active}, status=status.HTTP_201_CREATED)
