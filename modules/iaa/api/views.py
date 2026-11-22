"""Thin HTTP handlers; all writes remain in the transactional service layer."""

import csv

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import ConflictError, NotFoundError
from fusion_auth.permissions import HasModuleGrant
from modules.iaa import selectors, services
from modules.iaa.api import serializers as s
from modules.iaa.authorization import active_role, require
from modules.iaa.domain.workflow import WorkflowError
from modules.iaa.models import (
    ApprovalRoute,
    ApprovalStep,
    AuditObservation,
    BudgetAllocation,
    ExpenseRequest,
    IaaAuditEvent,
    IaaPolicy,
    IaaProcessingIssue,
    IaaSupportingDocument,
    TravelClaim,
)
from modules.iaa.services.workflows import BudgetReferenceUnavailable

IAA = HasModuleGrant("iaa")


class IaaCursorPagination(CursorPagination):
    page_size = 25
    page_size_query_param = "limit"
    max_page_size = 100
    ordering = "-created_at"


@extend_schema(responses=OpenApiTypes.OBJECT)
class _View(APIView):
    permission_classes = [IAA]

    @property
    def actor(self):
        return self.request.principal

    def call_service(self, call):
        try:
            return call()
        except BudgetReferenceUnavailable as exc:
            issue = IaaProcessingIssue.objects.create(
                record_type=exc.record_type,
                record_id=exc.record_id,
                operation="finance_budget_check",
                reason=str(exc),
                reported_by_user_id=self.actor.user_id,
            )
            IaaAuditEvent.objects.create(
                record_type=exc.record_type,
                record_id=exc.record_id,
                actor_user_id=self.actor.user_id,
                active_role=self.actor.active_role,
                action="budget_reference_unavailable",
                details={"issue_id": issue.pk},
            )
            raise ConflictError(str(exc), code="budget_reference_unavailable") from exc
        except ObjectDoesNotExist as exc:
            raise NotFoundError("IAA record was not found.") from exc
        except WorkflowError as exc:
            raise ConflictError(str(exc), code="invalid_transition") from exc


class ExpenseListView(_View):
    pagination_class = IaaCursorPagination

    @extend_schema(operation_id="iaa_expense_list", responses=OpenApiTypes.OBJECT)
    def get(self, request):
        role = active_role(request.principal)
        code = "iaa.request.view_self" if role == "basic_user" else "iaa.request.view"
        require(self.actor, code)
        queryset = selectors.expenses_for(self.actor).order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(s.ExpenseReadSerializer(page, many=True).data)

    @extend_schema(
        operation_id="iaa_expense_create",
        request=s.ExpenseDraftSerializer,
        responses=s.ExpenseReadSerializer,
    )
    def post(self, request):
        data = s.ExpenseDraftSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        record = self.call_service(
            lambda: services.create_expense_draft(self.actor, data.validated_data)
        )
        return Response(
            s.ExpenseReadSerializer(record).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/api/v1/iaa/expenses/{record.pk}"},
        )


class ExpenseDetailView(_View):
    def get_object(self, pk):
        record = selectors.expenses_for(self.actor).filter(pk=pk).first()
        if record is None:
            raise NotFoundError("Expense request was not found.")
        role = active_role(self.actor)
        require(self.actor, "iaa.request.view_self" if role == "basic_user" else "iaa.request.view")
        return record

    @extend_schema(operation_id="iaa_expense_detail", responses=s.ExpenseReadSerializer)
    def get(self, request, pk):
        return Response(s.ExpenseReadSerializer(self.get_object(pk)).data)

    @extend_schema(
        operation_id="iaa_expense_update_draft",
        request=s.ExpenseDraftSerializer,
        responses=s.ExpenseReadSerializer,
    )
    def patch(self, request, pk):
        data = s.ExpenseDraftSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        record = self.call_service(
            lambda: services.update_expense_draft(self.actor, pk, data.validated_data)
        )
        return Response(s.ExpenseReadSerializer(record).data)


class ExpenseSubmitView(_View):
    @extend_schema(
        operation_id="iaa_expense_submit",
        request=None,
        responses=s.ExpenseReadSerializer,
    )
    def post(self, request, pk):
        record = self.call_service(lambda: services.submit_expense(self.actor, pk))
        return Response(s.ExpenseReadSerializer(record).data)


class ExpenseFinanceReviewView(_View):
    @extend_schema(
        operation_id="iaa_expense_finance_review",
        request=s.ActionSerializer,
        responses=s.ExpenseReadSerializer,
    )
    def post(self, request, pk):
        data = s.ActionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        record = self.call_service(
            lambda: services.finance_review_expense(self.actor, pk, **data.validated_data)
        )
        return Response(s.ExpenseReadSerializer(record).data)


class FinancialRecordView(_View):
    @extend_schema(
        operation_id="iaa_financial_record",
        request=None,
        responses=OpenApiTypes.OBJECT,
    )
    def post(self, request, record_type, pk):
        record = self.call_service(
            lambda: services.record_financial_item(self.actor, record_type, pk)
        )
        serializer = (
            s.ExpenseReadSerializer if record_type == "expense" else s.TravelClaimReadSerializer
        )
        return Response(serializer(record).data)


class TravelClaimListView(_View):
    pagination_class = IaaCursorPagination

    @extend_schema(operation_id="iaa_ta_claim_list", responses=OpenApiTypes.OBJECT)
    def get(self, request):
        role = active_role(self.actor)
        require(self.actor, "iaa.ta.view_self" if role == "basic_user" else "iaa.ta.view")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(
            selectors.claims_for(self.actor).order_by("-created_at"), request, view=self
        )
        return paginator.get_paginated_response(s.TravelClaimReadSerializer(page, many=True).data)

    @extend_schema(
        operation_id="iaa_ta_claim_create",
        request=s.TravelClaimWriteSerializer,
        responses=s.TravelClaimReadSerializer,
    )
    def post(self, request):
        data = s.TravelClaimWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        record = self.call_service(
            lambda: services.submit_ta_claim(self.actor, data.validated_data)
        )
        return Response(
            s.TravelClaimReadSerializer(record).data,
            status=201,
            headers={"Location": f"/api/v1/iaa/ta-claims/{record.pk}"},
        )


class TravelClaimFinanceReviewView(_View):
    @extend_schema(
        operation_id="iaa_ta_claim_finance_review",
        request=s.ActionSerializer,
        responses=s.TravelClaimReadSerializer,
    )
    def post(self, request, pk):
        data = s.ActionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        record = self.call_service(
            lambda: services.finance_review_ta(self.actor, pk, **data.validated_data)
        )
        return Response(s.TravelClaimReadSerializer(record).data)


class TravelClaimDetailView(_View):
    @extend_schema(operation_id="iaa_ta_claim_detail", responses=s.TravelClaimReadSerializer)
    def get(self, request, pk):
        role = active_role(self.actor)
        require(self.actor, "iaa.ta.view_self" if role == "basic_user" else "iaa.ta.view")
        record = selectors.claims_for(self.actor).filter(pk=pk).first()
        if record is None:
            raise NotFoundError("Travel claim was not found.")
        return Response(s.TravelClaimReadSerializer(record).data)


class SupportingDocumentView(_View):
    @extend_schema(
        operation_id="iaa_document_list", responses=s.SupportingDocumentSerializer(many=True)
    )
    def get(self, request):
        role = active_role(self.actor)
        require(self.actor, "iaa.request.view_self" if role == "basic_user" else "iaa.request.view")
        rows = IaaSupportingDocument.objects.filter(user_id=self.actor.user_id, is_active=True)
        return Response(
            s.SupportingDocumentSerializer(rows.order_by("-created_at"), many=True).data
        )

    @extend_schema(
        operation_id="iaa_document_create",
        request=s.SupportingDocumentWriteSerializer,
        responses=s.SupportingDocumentSerializer,
    )
    def post(self, request):
        data = s.SupportingDocumentWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        document = self.call_service(
            lambda: services.attach_document(self.actor, **data.validated_data)
        )
        return Response(
            s.SupportingDocumentSerializer(document).data,
            status=201,
            headers={"Location": f"/api/v1/iaa/documents/{document.pk}"},
        )


class ClarificationResponseView(_View):
    @extend_schema(
        request=s.ClarificationSerializer,
        responses=OpenApiTypes.OBJECT,
    )
    def post(self, request, record_type, pk):
        data = s.ClarificationSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        record = self.call_service(
            lambda: services.respond_to_clarification(
                self.actor, record_type, pk, **data.validated_data
            )
        )
        serializer = (
            s.ExpenseReadSerializer if record_type == "expense" else s.TravelClaimReadSerializer
        )
        return Response(serializer(record).data)


class ApprovalQueueView(generics.ListAPIView):
    permission_classes = [IAA]
    serializer_class = s.ApprovalStepSerializer
    pagination_class = IaaCursorPagination
    queryset = ApprovalStep.objects.none()

    def get_queryset(self):
        require(self.request.principal, "iaa.approval.decide", roles={"hod", "dean", "director"})
        return selectors.assigned_approvals(self.request.principal).order_by("due_at", "id")


class ApprovalDecisionView(_View):
    @extend_schema(
        operation_id="iaa_approval_decide",
        request=s.ActionSerializer,
        responses=OpenApiTypes.OBJECT,
    )
    def post(self, request, pk):
        data = s.ActionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        record = self.call_service(
            lambda: services.decide_approval(
                self.actor,
                pk,
                decision=data.validated_data["decision"],
                remarks=data.validated_data.get("remarks", ""),
            )
        )
        serializer = (
            s.ExpenseReadSerializer
            if isinstance(record, ExpenseRequest)
            else s.TravelClaimReadSerializer
        )
        return Response(serializer(record).data)


class AnomalyListCreateView(_View):
    pagination_class = IaaCursorPagination

    @extend_schema(operation_id="iaa_anomaly_list", responses=OpenApiTypes.OBJECT)
    def get(self, request):
        require(self.actor, "iaa.anomaly.resolve")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(
            selectors.anomalies_for(self.actor).order_by("-created_at"), request, view=self
        )
        return paginator.get_paginated_response(s.AnomalySerializer(page, many=True).data)

    @extend_schema(
        operation_id="iaa_anomaly_create",
        request=s.AnomalyCreateSerializer,
        responses=s.AnomalySerializer,
    )
    def post(self, request):
        data = s.AnomalyCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        anomaly = self.call_service(
            lambda: services.flag_anomaly(self.actor, **data.validated_data)
        )
        return Response(s.AnomalySerializer(anomaly).data, status=201)


class AnomalyResolveView(_View):
    @extend_schema(
        operation_id="iaa_anomaly_resolve",
        request=s.AnomalyResolutionSerializer,
        responses=s.AnomalySerializer,
    )
    def post(self, request, pk):
        data = s.AnomalyResolutionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        anomaly = self.call_service(
            lambda: services.resolve_anomaly(self.actor, pk, **data.validated_data)
        )
        return Response(s.AnomalySerializer(anomaly).data)


class ObservationListView(generics.ListAPIView):
    permission_classes = [IAA]
    serializer_class = s.ObservationSerializer
    pagination_class = IaaCursorPagination
    queryset = AuditObservation.objects.none()

    def get_queryset(self):
        role = active_role(self.request.principal)
        require(
            self.request.principal,
            "iaa.audit.review" if role == "auditor" else "iaa.observation.respond",
        )
        return selectors.observations_for(self.request.principal).order_by("-created_at")


class ObservationCreateView(_View):
    @extend_schema(
        operation_id="iaa_observation_create",
        request=s.ObservationCreateSerializer,
        responses=s.ObservationSerializer,
    )
    def post(self, request):
        data = s.ObservationCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        observation = self.call_service(
            lambda: services.raise_observation(self.actor, **data.validated_data)
        )
        return Response(s.ObservationSerializer(observation).data, status=201)


class ObservationResponseView(_View):
    @extend_schema(
        operation_id="iaa_observation_respond",
        request=s.ObservationResponseSerializer,
        responses=OpenApiTypes.OBJECT,
    )
    def post(self, request, pk):
        data = s.ObservationResponseSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        response = self.call_service(
            lambda: services.respond_observation(self.actor, pk, **data.validated_data)
        )
        return Response(
            {
                "id": response.pk,
                "observation_id": response.observation_id,
                "created_at": response.created_at,
            },
            status=201,
        )


class ObservationReviewView(_View):
    @extend_schema(
        operation_id="iaa_observation_review",
        request=s.ObservationReviewSerializer,
        responses=s.ObservationSerializer,
    )
    def post(self, request, pk, response_id):
        data = s.ObservationReviewSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        observation = self.call_service(
            lambda: services.verify_observation(self.actor, pk, response_id, **data.validated_data)
        )
        return Response(s.ObservationSerializer(observation).data)


class NotificationListView(_View):
    @extend_schema(operation_id="iaa_notification_list", responses=OpenApiTypes.OBJECT)
    def get(self, request):
        require(self.actor, "iaa.notification.view")
        role = active_role(self.actor)
        feed = [
            {
                "id": f"event-{row.pk}",
                "event": row.event,
                "record_type": row.record_type,
                "record_id": row.record_id,
                "created_at": row.created_at.isoformat(),
            }
            for row in selectors.notifications_for(self.actor).order_by("-created_at")[:100]
        ]
        # Queue reminders are scoped to the active actor role and show pending work
        # even when an audience has no individually assigned recipient.
        if role == "finance_staff":
            for kind, qs in (
                (
                    "expense",
                    ExpenseRequest.objects.filter(status__in=("submitted", "query_responded")),
                ),
                ("ta", TravelClaim.objects.filter(status__in=("submitted", "query_responded"))),
            ):
                feed.extend(
                    {
                        "id": f"queue-{kind}-{row.pk}",
                        "event": "pending_finance_review",
                        "record_type": kind,
                        "record_id": row.pk,
                        "created_at": row.created_at.isoformat(),
                    }
                    for row in qs[:100]
                )
            issues = IaaProcessingIssue.objects.filter(
                status="open", reported_by_user_id=self.actor.user_id
            )
            feed.extend(
                {
                    "id": f"recovery-{issue.pk}",
                    "event": "finance_validation_needs_recovery",
                    "record_type": issue.record_type,
                    "record_id": issue.record_id,
                    "created_at": issue.created_at.isoformat(),
                }
                for issue in issues[:100]
            )
        elif role in {"hod", "dean", "director"}:
            feed.extend(
                {
                    "id": f"approval-{row.pk}",
                    "event": "approval_pending",
                    "record_type": row.record_type,
                    "record_id": row.record_id,
                    "created_at": row.created_at.isoformat(),
                }
                for row in selectors.assigned_approvals(self.actor)
            )
        if role in {"finance_staff", "auditor", "hod", "dean", "director"}:
            feed.extend(
                {
                    "id": f"anomaly-{row.pk}",
                    "event": "anomaly_follow_up",
                    "record_type": "anomaly",
                    "record_id": row.pk,
                    "created_at": row.created_at.isoformat(),
                }
                for row in selectors.anomalies_for(self.actor).filter(
                    status__in=("open", "escalated")
                )[:100]
            )
        feed.sort(key=lambda item: item["created_at"], reverse=True)
        return Response({"results": feed[:100], "next": None, "previous": None})


class ProcessingIssuesView(_View):
    @extend_schema(
        operation_id="iaa_processing_issues",
        responses=s.ProcessingIssueSerializer(many=True),
    )
    def get(self, request):
        require(self.actor, "iaa.finance.validate", roles={"finance_staff"})
        rows = IaaProcessingIssue.objects.filter(
            status="open", operation="finance_budget_check", reported_by_user_id=self.actor.user_id
        ).order_by("-created_at")
        return Response(
            list(rows.values("id", "record_type", "record_id", "operation", "reason", "created_at"))
        )


class AuditRecordsView(_View):
    @extend_schema(operation_id="iaa_audit_records", responses=OpenApiTypes.OBJECT)
    def get(self, request):
        require(self.actor, "iaa.audit.review", roles={"auditor"})
        expenses = ExpenseRequest.objects.order_by("-created_at")[:100]
        claims = TravelClaim.objects.order_by("-created_at")[:100]
        return Response(
            {
                "expenses": s.ExpenseReadSerializer(expenses, many=True).data,
                "ta_claims": s.TravelClaimReadSerializer(claims, many=True).data,
            }
        )


class RecordHistoryView(_View):
    @extend_schema(responses=s.AuditEventSerializer(many=True))
    def get(self, request, record_type, pk):
        if record_type == "expense":
            record = selectors.expenses_for(self.actor).filter(pk=pk).first()
            require(
                self.actor,
                "iaa.request.view_self"
                if active_role(self.actor) == "basic_user"
                else "iaa.request.view",
            )
        elif record_type == "ta":
            record = selectors.claims_for(self.actor).filter(pk=pk).first()
            require(
                self.actor,
                "iaa.ta.view_self" if active_role(self.actor) == "basic_user" else "iaa.ta.view",
            )
        else:
            raise NotFoundError("IAA record was not found.")
        if record is None:
            raise NotFoundError("IAA record was not found.")
        events = IaaAuditEvent.objects.filter(record_type=record_type, record_id=pk)
        return Response(
            list(
                events.values(
                    "id",
                    "actor_user_id",
                    "active_role",
                    "action",
                    "from_status",
                    "to_status",
                    "details",
                    "occurred_at",
                )
            )
        )


class IaaPolicyView(_View):
    @extend_schema(operation_id="iaa_policy_get", responses=OpenApiTypes.OBJECT)
    def get(self, request):
        require(self.actor, "iaa.admin.configure", roles={"system_admin"})
        policy = IaaPolicy.objects.filter(is_active=True).order_by("-updated_at").first()
        if policy is None:
            return Response(None)
        return Response(s.PolicySerializer(policy).data)

    @extend_schema(
        operation_id="iaa_policy_update",
        request=s.PolicySerializer,
        responses=s.PolicySerializer,
    )
    def put(self, request):
        require(self.actor, "iaa.admin.configure", roles={"system_admin"})
        policy = IaaPolicy.objects.filter(is_active=True).order_by("-updated_at").first()
        serializer = s.PolicySerializer(policy, data=request.data, partial=policy is not None)
        serializer.is_valid(raise_exception=True)
        policy = serializer.save(configured_by_user_id=self.actor.user_id)
        IaaAuditEvent.objects.create(
            record_type="configuration",
            record_id=policy.pk,
            actor_user_id=self.actor.user_id,
            active_role=self.actor.active_role,
            action="policy_configured",
            details={"policy_name": policy.name},
        )
        return Response(s.PolicySerializer(policy).data)


class ApprovalRouteListCreateView(_View):
    @extend_schema(
        operation_id="iaa_approval_route_list", responses=s.ApprovalRouteSerializer(many=True)
    )
    def get(self, request):
        require(self.actor, "iaa.admin.configure", roles={"system_admin"})
        return Response(
            s.ApprovalRouteSerializer(
                ApprovalRoute.objects.order_by("request_type", "department", "level"), many=True
            ).data
        )

    @extend_schema(
        operation_id="iaa_approval_route_create",
        request=s.ApprovalRouteSerializer,
        responses=s.ApprovalRouteSerializer,
    )
    def post(self, request):
        require(self.actor, "iaa.admin.configure", roles={"system_admin"})
        data = s.ApprovalRouteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        route = data.save()
        IaaAuditEvent.objects.create(
            record_type="configuration",
            record_id=route.pk,
            actor_user_id=self.actor.user_id,
            active_role=self.actor.active_role,
            action="approval_route_created",
            details={
                "request_type": route.request_type,
                "level": route.level,
                "authority_role": route.authority_role,
            },
        )
        return Response(s.ApprovalRouteSerializer(route).data, status=201)


class ApprovalRouteDetailView(_View):
    @extend_schema(
        operation_id="iaa_approval_route_update",
        request=s.ApprovalRouteSerializer,
        responses=s.ApprovalRouteSerializer,
    )
    def patch(self, request, pk):
        require(self.actor, "iaa.admin.configure", roles={"system_admin"})
        route = get_object_or_404(ApprovalRoute, pk=pk)
        data = s.ApprovalRouteSerializer(route, data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        route = data.save()
        IaaAuditEvent.objects.create(
            record_type="configuration",
            record_id=route.pk,
            actor_user_id=self.actor.user_id,
            active_role=self.actor.active_role,
            action="approval_route_updated",
            details={"is_active": route.is_active},
        )
        return Response(s.ApprovalRouteSerializer(route).data)


class BudgetAllocationListCreateView(_View):
    @extend_schema(
        operation_id="iaa_budget_list", responses=s.BudgetAllocationSerializer(many=True)
    )
    def get(self, request):
        require(self.actor, "iaa.admin.configure", roles={"system_admin"})
        rows = BudgetAllocation.objects.order_by("financial_year", "department", "budget_code")
        return Response(s.BudgetAllocationSerializer(rows, many=True).data)

    @extend_schema(
        operation_id="iaa_budget_create",
        request=s.BudgetAllocationSerializer,
        responses=s.BudgetAllocationSerializer,
    )
    def post(self, request):
        require(self.actor, "iaa.admin.configure", roles={"system_admin"})
        data = s.BudgetAllocationSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        budget = data.save(configured_by_user_id=self.actor.user_id)
        IaaAuditEvent.objects.create(
            record_type="configuration",
            record_id=budget.pk,
            actor_user_id=self.actor.user_id,
            active_role=self.actor.active_role,
            action="budget_configured",
            details={"department": budget.department, "financial_year": budget.financial_year},
        )
        return Response(s.BudgetAllocationSerializer(budget).data, status=201)


class BudgetAllocationDetailView(_View):
    @extend_schema(
        operation_id="iaa_budget_update",
        request=s.BudgetAllocationSerializer,
        responses=s.BudgetAllocationSerializer,
    )
    def patch(self, request, pk):
        require(self.actor, "iaa.admin.configure", roles={"system_admin"})
        budget = get_object_or_404(BudgetAllocation, pk=pk)
        data = s.BudgetAllocationSerializer(budget, data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        budget = data.save(configured_by_user_id=self.actor.user_id)
        IaaAuditEvent.objects.create(
            record_type="configuration",
            record_id=budget.pk,
            actor_user_id=self.actor.user_id,
            active_role=self.actor.active_role,
            action="budget_updated",
            details={"financial_year": budget.financial_year},
        )
        return Response(s.BudgetAllocationSerializer(budget).data)


class ReportSummaryView(_View):
    @extend_schema(operation_id="iaa_report_summary", responses=OpenApiTypes.OBJECT)
    def get(self, request):
        require(self.actor, "iaa.report.view")
        # Reports expose aggregate status data only; they never return financial records.
        role = active_role(self.actor)
        if role not in {"finance_staff", "hod", "dean", "director", "auditor"}:
            raise ConflictError(
                "The active role cannot view operational IAA reports.", code="permission_denied"
            )
        expenses, claims = ExpenseRequest.objects.all(), TravelClaim.objects.all()
        if role == "finance_staff":
            expenses = expenses.filter(assigned_finance_user_id=self.actor.user_id)
            claims = claims.filter(assigned_finance_user_id=self.actor.user_id)
        elif role in {"hod", "dean", "director"}:
            steps = ApprovalStep.objects.filter(assignee_user_id=self.actor.user_id)
            expense_ids = steps.filter(record_type="expense").values_list("record_id", flat=True)
            ta_ids = steps.filter(record_type="ta").values_list("record_id", flat=True)
            expenses, claims = expenses.filter(pk__in=expense_ids), claims.filter(pk__in=ta_ids)
        anomalies = selectors.anomalies_for(self.actor)
        observations = selectors.observations_for(self.actor)
        steps = ApprovalStep.objects.filter(
            status__in=("approved", "rejected"), decided_at__isnull=False
        )
        if role != "auditor":
            steps = steps.filter(assignee_user_id=self.actor.user_id)
        turnaround = steps.annotate(
            elapsed=ExpressionWrapper(
                F("decided_at") - F("created_at"), output_field=DurationField()
            )
        ).aggregate(average=Avg("elapsed"))["average"]
        return Response(
            {
                "expense_requests": list(expenses.values("status").annotate(total=Count("id"))),
                "ta_claims": list(claims.values("status").annotate(total=Count("id"))),
                "anomalies": list(anomalies.values("status").annotate(total=Count("id"))),
                "observations": list(observations.values("status").annotate(total=Count("id"))),
                "average_approval_turnaround_seconds": turnaround.total_seconds()
                if turnaround
                else None,
            }
        )


class ReportExportView(_View):
    @extend_schema(
        operation_id="iaa_report_export",
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
    )
    def get(self, request):
        require(self.actor, "iaa.report.export")
        role = active_role(self.actor)
        if role not in {"finance_staff", "hod", "dean", "director", "auditor"}:
            raise ConflictError(
                "The active role cannot export IAA reports.", code="permission_denied"
            )
        rows = []
        for name, queryset in (
            ("expense", selectors.expenses_for(self.actor)),
            ("ta", selectors.claims_for(self.actor)),
        ):
            rows.extend(
                (
                    name,
                    row.pk,
                    row.status,
                    row.department,
                    str(row.amount),
                    row.created_at.isoformat(),
                )
                for row in queryset.order_by("-created_at")[:500]
            )
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="iaa-summary.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ("record_type", "record_id", "status", "department", "amount", "created_at")
        )
        writer.writerows(rows)
        return response
