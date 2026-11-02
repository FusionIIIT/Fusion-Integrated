from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from decimal import Decimal

from ..models import (
    ExpenseRequest,
    TravelAllowanceClaim,
    DepartmentBudget,
    AnomalyRecord,
    AuditObservation,
    ApprovalAction,
)
from .serializers import (
    ExpenseRequestSerializer,
    TravelAllowanceClaimSerializer,
    DepartmentBudgetSerializer,
    AnomalyRecordSerializer,
    AuditObservationSerializer,
    ApprovalActionSerializer,
    ExpenseRequestSubmitSerializer,
    ClarificationQuerySerializer,
    ClarificationResponseSerializer,
    ApprovalDecisionSerializer,
    AnomalyResolutionSerializer,
    AuditResponseSerializer,
    AuditClosureSerializer,
)

class ExpenseRequestViewSet(viewsets.ModelViewSet):
    queryset = ExpenseRequest.objects.all().order_by("-created_at")
    serializer_class = ExpenseRequestSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        dept = self.request.query_params.get("department")
        user_id = self.request.query_params.get("user_id")
        status_filter = self.request.query_params.get("status")
        role = self.request.query_params.get("role")

        if dept:
            qs = qs.filter(department=dept)
        if user_id:
            qs = qs.filter(creator_user_id=user_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if role in ["hod", "dean", "director"]:
            qs = qs.filter(current_authority_role=role, status="pending_approval")
        elif role == "finance":
            qs = qs.filter(status__in=["submitted", "clarification_responded", "approved"])
        return qs

    def perform_create(self, serializer):
        user_id = (
            self.request.headers.get("X-User-Id")
            or getattr(self.request.user, "id", None)
            or self.request.data.get("creator_user_id")
            or 1
        )
        serializer.save(
            creator_user_id=int(user_id),
            status="draft",
            is_locked=False,
            current_authority_role="none",
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        expense = self.get_object()
        if expense.is_locked:
            return Response(
                {"detail": "Request is locked against modifications (IAA-BR-104)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # IAA-BR-101: Submission Completeness Validation
        if not expense.title.strip() or not expense.description.strip() or not expense.department.strip() or expense.amount <= Decimal("0"):
            return Response(
                {"detail": "Submission completeness validation failed: title, description, department, and positive amount are required (IAA-BR-101)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expense.is_locked = True
        expense.status = "submitted"
        expense.submission_date = timezone.now()
        expense.save()

        ApprovalAction.objects.create(
            entity_type="expense",
            entity_id=expense.id,
            actor_user_id=expense.creator_user_id,
            actor_role="creator",
            action="submit",
            remarks=request.data.get("notes", "Submitted formally for Finance validation"),
        )
        return Response(ExpenseRequestSerializer(expense).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def finance_review(self, request, pk=None):
        expense = self.get_object()
        if expense.status not in ["submitted", "clarification_responded"]:
            return Response(
                {"detail": f"Cannot perform finance review on request with status '{expense.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # IAA-BR-102 & IAA-BR-103: Budget Validation and Anomaly Trigger
        budget = DepartmentBudget.objects.filter(department=expense.department).first()
        if not budget or budget.available_budget < expense.amount:
            avail = budget.available_budget if budget else Decimal("0")
            AnomalyRecord.objects.create(
                anomaly_category="budget_insufficiency",
                severity="high",
                description=f"Department '{expense.department}' has insufficient budget. Requested: {expense.amount}, Available: {avail}",
                related_expense=expense,
                flagged_by_role="finance",
                flagged_by_user_id=int(request.data.get("actor_user_id", 1)),
                status="open",
            )

        # IAA-BR-002: Configured Approval Routing by Amount
        if expense.amount <= Decimal("50000.00"):
            target_role = "hod"
        elif expense.amount <= Decimal("200000.00"):
            target_role = "dean"
        else:
            target_role = "director"

        # IAA-BR-001: Segregation of duties check during routing
        actor_id = int(request.data.get("actor_user_id", 1))
        if expense.creator_user_id == actor_id and target_role == "hod":
            target_role = "dean"

        expense.current_authority_role = target_role
        expense.status = "pending_approval"
        expense.save()

        ApprovalAction.objects.create(
            entity_type="expense",
            entity_id=expense.id,
            actor_user_id=actor_id,
            actor_role="finance",
            action="finance_review_passed",
            remarks=request.data.get("remarks", f"Routed to {target_role} for approval"),
        )
        return Response(ExpenseRequestSerializer(expense).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def request_clarification(self, request, pk=None):
        expense = self.get_object()
        serializer = ClarificationQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        expense.clarification_query = serializer.validated_data["query"]
        expense.status = "clarification_requested"
        expense.is_locked = False  # Unlocked so creator can address
        expense.save()

        ApprovalAction.objects.create(
            entity_type="expense",
            entity_id=expense.id,
            actor_user_id=int(request.data.get("actor_user_id", 1)),
            actor_role="finance",
            action="request_clarification",
            remarks=serializer.validated_data["query"],
        )
        return Response(ExpenseRequestSerializer(expense).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def respond_clarification(self, request, pk=None):
        expense = self.get_object()
        serializer = ClarificationResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        expense.clarification_response = serializer.validated_data["response"]
        expense.status = "clarification_responded"
        expense.is_locked = True
        expense.save()

        ApprovalAction.objects.create(
            entity_type="expense",
            entity_id=expense.id,
            actor_user_id=expense.creator_user_id,
            actor_role="creator",
            action="respond_clarification",
            remarks=serializer.validated_data["response"],
        )
        return Response(ExpenseRequestSerializer(expense).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def decision(self, request, pk=None):
        expense = self.get_object()
        serializer = ApprovalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dec_action = serializer.validated_data["action"]
        remarks = serializer.validated_data["remarks"].strip()
        actor_role = serializer.validated_data.get("actor_role") or expense.current_authority_role
        actor_user_id = int(request.data.get("actor_user_id", 1))

        # IAA-BR-005: Remarks Mandatory
        if not remarks:
            return Response(
                {"detail": "Approval/rejection decision remarks are mandatory (IAA-BR-005)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # IAA-BR-001: Segregation of Duties
        if actor_user_id == expense.creator_user_id:
            return Response(
                {"detail": "Segregation of duties violation: Creator cannot approve their own request (IAA-BR-001)."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if dec_action == "approve":
            expense.status = "approved"
            budget = DepartmentBudget.objects.filter(department=expense.department).first()
            if budget:
                budget.committed_amount += expense.amount
                budget.save()
        else:
            expense.status = "rejected"

        expense.save()

        ApprovalAction.objects.create(
            entity_type="expense",
            entity_id=expense.id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action=dec_action,
            remarks=remarks,
        )
        return Response(ExpenseRequestSerializer(expense).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def internal_complete(self, request, pk=None):
        expense = self.get_object()
        if expense.status != "approved":
            return Response(
                {"detail": "Only approved requests can be internally completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # IAA-BR-006: Internal Processing Is Non-Monetary
        expense.status = "internal_completed"
        budget = DepartmentBudget.objects.filter(department=expense.department).first()
        if budget:
            budget.committed_amount = max(Decimal("0"), budget.committed_amount - expense.amount)
            budget.spent_amount += expense.amount
            budget.save()

        expense.save()

        ApprovalAction.objects.create(
            entity_type="expense",
            entity_id=expense.id,
            actor_user_id=int(request.data.get("actor_user_id", 1)),
            actor_role="finance",
            action="internal_complete",
            remarks=request.data.get("remarks", "Internal non-monetary voucher governance completed (IAA-BR-006)."),
        )
        return Response(ExpenseRequestSerializer(expense).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        expense = self.get_object()
        # IAA-BR-401: Approval Timeout Escalation
        role_map = {"hod": "dean", "dean": "director", "director": "director"}
        next_role = role_map.get(expense.current_authority_role, "dean")
        expense.current_authority_role = next_role
        expense.status = "escalated"
        expense.save()

        ApprovalAction.objects.create(
            entity_type="expense",
            entity_id=expense.id,
            actor_user_id=int(request.data.get("actor_user_id", 1)),
            actor_role="system",
            action="escalate_timeout",
            remarks=f"Timeout reached. Escalated to {next_role} (IAA-BR-401).",
        )
        return Response(ExpenseRequestSerializer(expense).data, status=status.HTTP_200_OK)


class TravelAllowanceClaimViewSet(viewsets.ModelViewSet):
    queryset = TravelAllowanceClaim.objects.all().order_by("-created_at")
    serializer_class = TravelAllowanceClaimSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user_id = (
            self.request.headers.get("X-User-Id")
            or getattr(self.request.user, "id", None)
            or self.request.data.get("claimant_user_id")
            or 1
        )
        amount = Decimal(str(self.request.data.get("claimed_amount", "0")))
        is_high = amount >= Decimal("50000.00")  # IAA-BR-202
        serializer.save(
            claimant_user_id=int(user_id),
            status="draft",
            is_high_value=is_high,
            is_locked=False,
            current_authority_role="none",
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        claim = self.get_object()
        if claim.is_locked:
            return Response({"detail": "Claim is locked (IAA-BR-104)."}, status=status.HTTP_400_BAD_REQUEST)

        if not claim.purpose.strip() or not claim.departure_place.strip() or not claim.destination_place.strip() or claim.claimed_amount <= Decimal("0"):
            return Response(
                {"detail": "Incomplete TA claim: departure, destination, purpose, and positive amount are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        claim.is_locked = True
        claim.status = "submitted"
        claim.save()

        ApprovalAction.objects.create(
            entity_type="ta",
            entity_id=claim.id,
            actor_user_id=claim.claimant_user_id,
            actor_role="claimant",
            action="submit",
            remarks="Submitted TA Claim",
        )
        return Response(TravelAllowanceClaimSerializer(claim).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def finance_review(self, request, pk=None):
        claim = self.get_object()
        # IAA-BR-202: High-Value TA Approval routing
        if claim.is_high_value or claim.claimed_amount >= Decimal("50000.00"):
            claim.is_high_value = True
            target_role = "dean"
        else:
            target_role = "hod"

        claim.current_authority_role = target_role
        claim.status = "pending_approval"
        claim.save()

        ApprovalAction.objects.create(
            entity_type="ta",
            entity_id=claim.id,
            actor_user_id=int(request.data.get("actor_user_id", 1)),
            actor_role="finance",
            action="finance_reviewed",
            remarks=f"TA Claim verified and routed to {target_role} (High Value: {claim.is_high_value})",
        )
        return Response(TravelAllowanceClaimSerializer(claim).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def decision(self, request, pk=None):
        claim = self.get_object()
        serializer = ApprovalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dec_action = serializer.validated_data["action"]
        remarks = serializer.validated_data["remarks"].strip()
        actor_user_id = int(request.data.get("actor_user_id", 1))

        # IAA-BR-001: Segregation of Duties
        if actor_user_id == claim.claimant_user_id:
            return Response(
                {"detail": "Segregation of duties: Claimant cannot approve their own TA claim (IAA-BR-001)."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if dec_action == "approve":
            claim.status = "approved"
            claim.approved_amount = claim.claimed_amount
        else:
            claim.status = "rejected"

        claim.save()

        ApprovalAction.objects.create(
            entity_type="ta",
            entity_id=claim.id,
            actor_user_id=actor_user_id,
            actor_role=claim.current_authority_role,
            action=dec_action,
            remarks=remarks,
        )
        return Response(TravelAllowanceClaimSerializer(claim).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def internal_complete(self, request, pk=None):
        claim = self.get_object()
        if claim.status != "approved":
            return Response({"detail": "Only approved TA claims can be completed."}, status=status.HTTP_400_BAD_REQUEST)

        claim.status = "internal_completed"
        claim.save()

        ApprovalAction.objects.create(
            entity_type="ta",
            entity_id=claim.id,
            actor_user_id=int(request.data.get("actor_user_id", 1)),
            actor_role="finance",
            action="internal_complete",
            remarks="Internal non-monetary TA claim recorded (IAA-BR-006).",
        )
        return Response(TravelAllowanceClaimSerializer(claim).data, status=status.HTTP_200_OK)


class DepartmentBudgetViewSet(viewsets.ModelViewSet):
    queryset = DepartmentBudget.objects.all().order_by("department")
    serializer_class = DepartmentBudgetSerializer
    permission_classes = [permissions.AllowAny]


class AnomalyRecordViewSet(viewsets.ModelViewSet):
    queryset = AnomalyRecord.objects.all().order_by("-created_at")
    serializer_class = AnomalyRecordSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        anomaly = self.get_object()
        serializer = AnomalyResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        res = serializer.validated_data["resolution"]
        remarks = serializer.validated_data["remarks"]

        if res == "resolve":
            anomaly.status = "resolved"
            anomaly.resolved_at = timezone.now()
        else:
            anomaly.status = "escalated"

        anomaly.resolution_remarks = remarks
        anomaly.resolver_user_id = int(request.data.get("resolver_user_id", 1))
        anomaly.save()

        ApprovalAction.objects.create(
            entity_type="anomaly",
            entity_id=anomaly.id,
            actor_user_id=anomaly.resolver_user_id,
            actor_role="resolver",
            action=f"anomaly_{res}",
            remarks=remarks,
        )
        return Response(AnomalyRecordSerializer(anomaly).data, status=status.HTTP_200_OK)


class AuditObservationViewSet(viewsets.ModelViewSet):
    queryset = AuditObservation.objects.all().order_by("-created_at")
    serializer_class = AuditObservationSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=["post"])
    def raise_observation(self, request, pk=None):
        obs = self.get_object()
        obs.status = "raised"
        obs.save()
        ApprovalAction.objects.create(
            entity_type="audit",
            entity_id=obs.id,
            actor_user_id=obs.auditor_user_id,
            actor_role="auditor",
            action="raise_observation",
            remarks=f"Raised observation: {obs.subject}",
        )
        return Response(AuditObservationSerializer(obs).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        obs = self.get_object()
        serializer = AuditResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        obs.department_response = serializer.validated_data["department_response"]
        obs.status = "response_submitted"
        obs.save()

        ApprovalAction.objects.create(
            entity_type="audit",
            entity_id=obs.id,
            actor_user_id=int(request.data.get("actor_user_id", 1)),
            actor_role="department",
            action="respond_observation",
            remarks=serializer.validated_data["department_response"],
        )
        return Response(AuditObservationSerializer(obs).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def verify_close(self, request, pk=None):
        obs = self.get_object()
        serializer = AuditClosureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # IAA-BR-302: Audit Closure Verification
        obs.verified_by_auditor = True
        obs.closure_remarks = serializer.validated_data["closure_remarks"]
        obs.status = "verified_closed"
        obs.save()

        ApprovalAction.objects.create(
            entity_type="audit",
            entity_id=obs.id,
            actor_user_id=int(request.data.get("actor_user_id", obs.auditor_user_id)),
            actor_role="auditor",
            action="verify_close",
            remarks=serializer.validated_data["closure_remarks"],
        )
        return Response(AuditObservationSerializer(obs).data, status=status.HTTP_200_OK)


class ApprovalActionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ApprovalAction.objects.all().order_by("-created_at")
    serializer_class = ApprovalActionSerializer
    permission_classes = [permissions.AllowAny]
