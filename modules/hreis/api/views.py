"""Thin DRF API. Two IAM gates precede every scoped HR-EIS query."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.hreis.api import serializers as s
from modules.hreis.api.throttles import HREISWriteThrottleMixin
from modules.hreis.domain.routing import AUTHORITY_DESIGNATIONS
from modules.hreis.selectors import scoping
from modules.hreis.services import (
    appraisals,
    finance,
    leave_balances,
    policies,
    records,
    transitions,
)
from modules.hreis.services import requests as request_services

MODULE = HasModuleGrant("hreis")
VIEW_RECORD = HasPermission("hreis.service_record.view")
CREATE_RECORD = HasPermission("hreis.service_record.create")
UPDATE_RECORD = HasPermission("hreis.service_record.update")


def _actor(request):
    return getattr(request, "principal", None)


class MyRecordView(APIView):
    permission_classes = [MODULE, VIEW_RECORD]

    @extend_schema(
        responses={200: s.RecordReadSerializer},
        summary="Read the current employee's own service record",
    )
    def get(self, request):
        record = (
            scoping.service_records_for(_actor(request))
            .filter(user_id=_actor(request).user_id)
            .first()
        )
        if record is None:
            raise NotFoundError("No accessible service record was found.", code="record_not_found")
        return Response(s.RecordReadSerializer(record).data)


class RecordListCreateView(HREISWriteThrottleMixin, generics.ListAPIView):
    serializer_class = s.RecordReadSerializer
    permission_classes = [MODULE, VIEW_RECORD]

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), CREATE_RECORD()]
        return [MODULE(), VIEW_RECORD()]

    def get_queryset(self):
        return scoping.service_records_for(_actor(self.request)).order_by("user_id")

    @extend_schema(
        responses={200: s.RecordReadSerializer(many=True)},
        summary="List employee records visible to this role",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=s.RecordCreateSerializer,
        responses={201: s.RecordReadSerializer},
        examples=[
            OpenApiExample(
                "Service record",
                request_only=True,
                value={
                    "user_id": 42,
                    "appointment_details": {"date": "2026-01-01"},
                    "department": "CSE",
                    "designation_snapshot": "Professor",
                    "service_history": [],
                },
            )
        ],
    )
    def post(self, request):
        payload = s.RecordCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        user_id = data.pop("user_id")
        row = records.create_record(
            _actor(request),
            user_id=user_id,
            fields=data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(s.RecordReadSerializer(row).data, status=status.HTTP_201_CREATED)


class RecordDetailView(HREISWriteThrottleMixin, APIView):
    permission_classes = [MODULE, VIEW_RECORD]

    def get_permissions(self):
        return (
            [MODULE(), UPDATE_RECORD()]
            if self.request.method == "PATCH"
            else [
                MODULE(),
                VIEW_RECORD(),
            ]
        )

    @extend_schema(
        responses={200: s.RecordReadSerializer},
        summary="Read a service record within this role's row scope",
    )
    def get(self, request, pk):
        row = scoping.service_records_for(_actor(request)).filter(pk=pk).first()
        if row is None:
            raise NotFoundError("No accessible service record was found.", code="record_not_found")
        return Response(s.RecordReadSerializer(row).data)

    @extend_schema(
        request=s.RecordUpdateSerializer,
        responses={200: s.RecordReadSerializer},
        examples=[
            OpenApiExample(
                "Revision",
                request_only=True,
                value={"expected_revision": 1, "department": "Design"},
            )
        ],
    )
    def patch(self, request, pk):
        payload = s.RecordUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        expected_revision = data.pop("expected_revision")
        if not data:
            raise BadRequestError(
                "No official field was supplied for update.", code="empty_service_fields"
            )
        row = records.update_record(
            _actor(request),
            record_id=pk,
            expected_revision=expected_revision,
            fields=data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(s.RecordReadSerializer(row).data)


class ReviewerAssignmentView(HREISWriteThrottleMixin, APIView):
    permission_classes = [MODULE, HasPermission("hreis.appraisal.assign")]

    @extend_schema(request=s.ReviewerAssignmentSerializer, responses={200: s.RequestReadSerializer})
    def post(self, request, pk):
        payload = s.ReviewerAssignmentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = appraisals.assign_reviewers(
            _actor(request),
            request_id=pk,
            **payload.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(s.RequestReadSerializer(row).data)


class AppraisalDecisionView(HREISWriteThrottleMixin, APIView):
    permission_classes = [MODULE, HasPermission("hreis.appraisal.approve")]

    @extend_schema(request=s.AppraisalDecisionSerializer, responses={200: s.RequestReadSerializer})
    def post(self, request, pk):
        payload = s.AppraisalDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = appraisals.review_appraisal(
            _actor(request),
            request_id=pk,
            **payload.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(s.RequestReadSerializer(row).data)


class ClaimReviewView(HREISWriteThrottleMixin, APIView):
    permission_classes = [MODULE, HasPermission("hreis.claim.review")]

    @extend_schema(request=s.ClaimReviewSerializer, responses={200: s.RequestReadSerializer})
    def post(self, request, pk):
        payload = s.ClaimReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = transitions.verify_claim(
            _actor(request),
            request_id=pk,
            **payload.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(s.RequestReadSerializer(row).data)


class FinancialReviewView(HREISWriteThrottleMixin, APIView):
    permission_classes = [MODULE, HasPermission("hreis.finance.review")]

    @extend_schema(
        request=s.FinancialReviewSerializer,
        responses={200: s.FinancialReviewReadSerializer},
        summary="Independently attest financial correctness of an approved HR claim",
    )
    def post(self, request, pk):
        payload = s.FinancialReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        review = finance.verify_financial_correctness(
            _actor(request), request_id=pk,
            **payload.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(s.FinancialReviewReadSerializer(review).data)


class FinancialProcessingView(HREISWriteThrottleMixin, APIView):
    permission_classes = [MODULE, HasPermission("hreis.finance.update")]

    @extend_schema(
        request=s.FinancialProcessingSerializer, responses={200: s.RequestReadSerializer},
        summary="Record externally referenced Accountant financial processing",
    )
    def post(self, request, pk):
        payload = s.FinancialProcessingSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = finance.record_financial_processing(
            _actor(request),
            request_id=pk,
            **payload.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(s.RequestReadSerializer(row).data)


class RequestDecisionView(HREISWriteThrottleMixin, APIView):
    permission_classes = [
        MODULE, HasPermission("hreis.leave.approve", "hreis.claim.approve"),
    ]

    @extend_schema(request=s.DecisionSerializer, responses={200: s.RequestReadSerializer})
    def post(self, request, pk):
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = transitions.decide_request(
            _actor(request),
            request_id=pk,
            **payload.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(s.RequestReadSerializer(row).data)


class VerifiedLeaveCreditView(HREISWriteThrottleMixin, APIView):
    permission_classes = [MODULE, HasPermission("hreis.balance.manage")]

    @extend_schema(
        request=s.VerifiedLeaveCreditSerializer,
        responses={201: s.VerifiedLeaveCreditReadSerializer},
        summary="Record HR-verified leave entitlement credit against an explicit source",
    )
    def post(self, request):
        payload = s.VerifiedLeaveCreditSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = leave_balances.record_verified_credit(
            _actor(request),
            **payload.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(
            s.VerifiedLeaveCreditReadSerializer(row).data, status=status.HTTP_201_CREATED
        )


class LeaveSubmitView(HREISWriteThrottleMixin, APIView):
    permission_classes = [MODULE, HasPermission("hreis.leave.create")]

    @extend_schema(request=s.LeaveSubmitSerializer, responses={201: s.RequestReadSerializer})
    def post(self, request):
        payload = s.LeaveSubmitSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = request_services.submit_leave(
            _actor(request),
            **payload.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(s.RequestReadSerializer(row).data, status=status.HTTP_201_CREATED)


class ClaimSubmitView(HREISWriteThrottleMixin, APIView):
    permission_classes = [MODULE, HasPermission("hreis.claim.create")]

    @extend_schema(request=s.ClaimSubmitSerializer, responses={201: s.RequestReadSerializer})
    def post(self, request):
        payload = s.ClaimSubmitSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = request_services.submit_claim(
            _actor(request),
            **payload.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(s.RequestReadSerializer(row).data, status=status.HTTP_201_CREATED)


class AppraisalSubmitView(HREISWriteThrottleMixin, APIView):
    permission_classes = [MODULE, HasPermission("hreis.appraisal.create")]

    @extend_schema(request=s.AppraisalSubmitSerializer, responses={201: s.RequestReadSerializer})
    def post(self, request):
        payload = s.AppraisalSubmitSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = request_services.submit_appraisal(
            _actor(request),
            **payload.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(s.RequestReadSerializer(row).data, status=status.HTTP_201_CREATED)


class PolicyListCreateView(HREISWriteThrottleMixin, generics.ListAPIView):
    serializer_class = s.PolicyReadSerializer
    permission_classes = [MODULE, HasPermission("hreis.policy.view")]

    def get_permissions(self):
        permission = "hreis.policy.manage" if self.request.method == "POST" else "hreis.policy.view"
        return [MODULE(), HasPermission(permission)()]

    def get_queryset(self):
        from modules.hreis.models import HRPolicyVersion

        return HRPolicyVersion.objects.order_by("-effective_from", "-version")

    @extend_schema(
        responses={200: s.PolicyReadSerializer(many=True)},
        summary="Read configured institutional HR policy revisions",
    )
    def get(self, request, *args, **kwargs):
        from modules.hreis.services.authz import require

        require(_actor(request), "hreis.policy.view", allowed_roles=frozenset({"hradmin"}))
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=s.PolicyCreateSerializer,
        responses={201: s.PolicyReadSerializer},
        summary="Record an explicit immutable HR policy version",
    )
    def post(self, request):
        payload = s.PolicyCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = policies.create_policy(
            _actor(request),
            **payload.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(s.PolicyReadSerializer(row).data, status=status.HTTP_201_CREATED)


class ComplianceRequestListView(generics.ListAPIView):
    serializer_class = s.ComplianceRequestSerializer
    permission_classes = [MODULE, HasPermission("hreis.audit.view")]

    def get_queryset(self):
        return (
            scoping.compliance_requests_for(_actor(self.request))
            .order_by("-created_at", "-pk")
        )

    @extend_schema(
        responses={200: s.ComplianceRequestSerializer(many=True)},
        summary="HR-only compliance status of all requests, excluding private forms",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ComplianceRequestDetailView(APIView):
    permission_classes = [MODULE, HasPermission("hreis.audit.view")]

    @extend_schema(
        responses={200: s.ComplianceRequestSerializer},
        summary="Read a single redacted HR compliance request status",
    )
    def get(self, request, pk):
        row = scoping.compliance_requests_for(_actor(request)).filter(pk=pk).first()
        if row is None:
            raise NotFoundError(
                "No accessible compliance status was found.", code="compliance_not_found"
            )
        return Response(s.ComplianceRequestSerializer(row).data)


class RequestListView(generics.ListAPIView):
    serializer_class = s.RequestReadSerializer
    permission_classes = [MODULE, HasPermission("hreis.request.view")]

    def get_queryset(self):
        return (
            scoping.requests_for(_actor(self.request))
            .select_related("claim", "appraisal")
            .prefetch_related("authority_steps", "claim__status_history")
            .order_by("-created_at", "-pk")
        )

    @extend_schema(
        responses={200: s.RequestReadSerializer(many=True)},
        summary="Track HR requests in the current acting role's scope",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ApprovalQueueView(generics.ListAPIView):
    serializer_class = s.RequestReadSerializer
    permission_classes = [
        MODULE,
        HasPermission("hreis.approval.view"),
        HasPermission("hreis.request.view"),
    ]

    def get_queryset(self):
        actor = _actor(self.request)
        from modules.hreis.models import HRRequest

        if actor is None or getattr(actor, "active_role", None) not in AUTHORITY_DESIGNATIONS:
            return HRRequest.objects.none()
        return (
            scoping.requests_for(actor)
            .select_related("claim", "appraisal")
            .prefetch_related("authority_steps", "claim__status_history")
            .order_by("-created_at", "-pk")
        )

    @extend_schema(
        responses={200: s.RequestReadSerializer(many=True)},
        summary="Current HR-EIS approval queue for the actor's designated role",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class RequestDetailView(APIView):
    permission_classes = [MODULE, HasPermission("hreis.request.view")]

    @extend_schema(
        responses={200: s.RequestDetailReadSerializer},
        summary="Read one request only within the current role's server-side scope",
    )
    def get(self, request, pk):
        row = (
            scoping.requests_for(_actor(request))
            .select_related("claim", "appraisal")
            .prefetch_related("authority_steps", "claim__status_history")
            .filter(pk=pk)
            .first()
        )
        if row is None:
            raise NotFoundError("No accessible HR request was found.", code="request_not_found")
        return Response(s.RequestDetailReadSerializer(row).data)


class MyLeaveBalancesView(APIView):
    permission_classes = [MODULE, VIEW_RECORD]

    @extend_schema(
        summary="Read the authenticated user's verified ledger balances",
        responses={200: s.MyLeaveBalancesSerializer},
    )
    def get(self, request):
        actor = _actor(request)
        record = scoping.service_records_for(actor).filter(user_id=actor.user_id).first()
        if record is None:
            raise NotFoundError("No service record is accessible.", code="record_not_found")
        return Response({
            "user_id": actor.user_id,
            "leave_balances": s.RecordReadSerializer(record).data["leave_balances"],
        })


class NotificationMarkReadView(HREISWriteThrottleMixin, APIView):
    permission_classes = [MODULE, HasPermission("hreis.notification.view")]

    @extend_schema(
        request=None,
        responses={200: s.NotificationReadSerializer},
        summary="Mark one of the current user's notifications as read",
    )
    @transaction.atomic
    def post(self, request, pk):
        from modules.hreis.models import AuditEvent

        actor = _actor(request)
        row = (
            scoping.notifications_for(actor)
            .select_for_update()
            .filter(pk=pk)
            .first()
        )
        if row is None:
            raise NotFoundError(
                "No accessible notification was found.", code="notification_not_found"
            )
        if row.read_at is None:
            row.read_at = timezone.now()
            row.save(update_fields=["read_at"])
            AuditEvent.objects.create(
                event_key=f"notification-read:{row.pk}:{actor.user_id}",
                actor_user_id=actor.user_id,
                acting_designation=actor.active_role,
                subject_user_id=actor.user_id,
                action="notification_read",
                resource_kind="notification",
                resource_id=row.pk,
                data={},
            )
        return Response(s.NotificationReadSerializer(row).data)


class NotificationListView(generics.ListAPIView):
    serializer_class = s.NotificationReadSerializer
    permission_classes = [MODULE, HasPermission("hreis.notification.view")]

    def get_queryset(self):
        return scoping.notifications_for(_actor(self.request)).order_by("-created_at", "-pk")

    @extend_schema(
        responses={200: s.NotificationReadSerializer(many=True)},
        summary="See notifications addressed to the current employee",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AuditListView(generics.ListAPIView):
    serializer_class = s.AuditReadSerializer
    permission_classes = [MODULE, HasPermission("hreis.audit.view")]

    def get_queryset(self):
        return scoping.audit_events_for(_actor(self.request)).order_by("-recorded_at", "-pk")

    @extend_schema(
        responses={200: s.AuditReadSerializer(many=True)},
        summary="View role-restricted HR compliance audit history",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
