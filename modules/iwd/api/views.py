"""REST API views and request dispatching for the IWD module."""

from decimal import Decimal

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.iwd.api.permissions import (
    RequireBillReview,
    RequireComplaintUpdate,
    RequireComplaintView,
    RequireEstimateCreate,
    RequireEstimateReview,
    RequireFeedbackCreate,
    RequireInventoryManage,
    RequireIwdModule,
    RequireWorkVerify,
)
from modules.iwd.api.serializers import (
    ComplaintFeedbackSerializer,
    ComplaintSerializer,
    EstimateSerializer,
    FinalBillSerializer,
    InventoryItemSerializer,
)
from modules.iwd.domain.state_machine import (
    InvalidStateTransitionError,
    RoleSeparationViolationError,
)
from modules.iwd.models import Complaint, InventoryItem
from modules.iwd.selectors.scoping import scope_complaints
from modules.iwd.services import (
    approvals,
    complaints,
    estimates,
    execution,
    feedback,
    inventory,
    settlement,
    verification,
)


class ComplaintListCreateView(APIView):
    """List scoped complaints or submit a new complaint (UC-IWD-001, UC-IWD-005)."""

    permission_classes = [RequireIwdModule, RequireComplaintView]

    @extend_schema(responses=ComplaintSerializer(many=True), operation_id="v1_iwd_complaints_list")
    def get(self, request):
        """Return complaints scoped to the requesting principal's role."""
        qs = scope_complaints(request.principal)
        serializer = ComplaintSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=ComplaintSerializer,
        responses=ComplaintSerializer,
        operation_id="v1_iwd_complaints_create",
    )
    def post(self, request):
        """Submit a new maintenance complaint with automatic engineer assignment."""
        serializer = ComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = getattr(request.principal, "user_id", 101)
        complaint = complaints.submit_complaint(
            requester_user_id=user_id,
            category=serializer.validated_data["category"],
            location=serializer.validated_data["location"],
            urgency=serializer.validated_data.get("urgency", "Low"),
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_201_CREATED)


class ComplaintDetailView(APIView):
    """Retrieve detailed state and history for a specific complaint."""

    permission_classes = [RequireIwdModule, RequireComplaintView]

    @extend_schema(responses=ComplaintSerializer, operation_id="v1_iwd_complaints_detail")
    def get(self, request, pk):
        """Retrieve a scoped complaint record or return 404 if inaccessible."""
        qs = scope_complaints(request.principal)
        try:
            complaint = qs.get(pk=pk)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ComplaintSerializer(complaint).data)


class AssessComplaintView(APIView):
    """Record repair assessment by the assigned engineer (UC-IWD-015)."""

    permission_classes = [RequireIwdModule, RequireComplaintUpdate]

    @extend_schema(
        request=None, responses=ComplaintSerializer, operation_id="v1_iwd_complaints_assess"
    )
    def post(self, request, pk):
        """Record technical assessment."""
        user_id = getattr(request.principal, "user_id", 201)
        details = request.data.get("assessment_details", "")
        try:
            complaint = complaints.assess_complaint(pk, user_id, details)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransitionError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ComplaintSerializer(complaint).data)


class SubmitEstimateView(APIView):
    """Submit a repair estimate and route to approval path (UC-IWD-021, BR-IWD-003)."""

    permission_classes = [RequireIwdModule, RequireEstimateCreate]

    @extend_schema(
        request=EstimateSerializer,
        responses=EstimateSerializer,
        operation_id="v1_iwd_complaints_submit_estimate",
    )
    def post(self, request, pk):
        """Submit a cost and time estimate."""
        user_id = getattr(request.principal, "user_id", 201)
        days = int(request.data.get("estimated_time_days", 1))
        materials = request.data.get("materials_details", "")
        cost = Decimal(str(request.data.get("total_cost", 0)))
        try:
            estimate = estimates.submit_estimate(pk, user_id, days, materials, cost)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransitionError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EstimateSerializer(estimate).data, status=status.HTTP_201_CREATED)


class FlagUrgentView(APIView):
    """Flag complaint for urgent fast-track review (UC-IWD-025, BR-IWD-012)."""

    permission_classes = [RequireIwdModule, RequireComplaintUpdate]

    @extend_schema(
        request=None, responses=ComplaintSerializer, operation_id="v1_iwd_complaints_flag_urgent"
    )
    def post(self, request, pk):
        """Flag active complaint as urgent."""
        user_id = getattr(request.principal, "user_id", 201)
        remarks = request.data.get("remarks", "")
        try:
            complaint = complaints.flag_urgent(pk, user_id, remarks)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransitionError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ComplaintSerializer(complaint).data)


class ReviewUrgentView(APIView):
    """Review urgent escalation request (UC-IWD-055, BR-IWD-012)."""

    permission_classes = [RequireIwdModule, RequireEstimateReview]

    @extend_schema(
        request=None, responses=ComplaintSerializer, operation_id="v1_iwd_complaints_review_urgent"
    )
    def post(self, request, pk):
        """Review urgent escalation."""
        user_id = getattr(request.principal, "user_id", 301)
        role = getattr(request.principal, "active_role", "iwd_department_head")
        accept = bool(request.data.get("accept", True))
        try:
            complaint = complaints.review_urgent(pk, user_id, role, accept)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransitionError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ComplaintSerializer(complaint).data)


class ReviewLowCostView(APIView):
    """IWD Admin approves or rejects low-cost repair estimate (UC-IWD-031, BR-IWD-004)."""

    permission_classes = [RequireIwdModule, RequireEstimateReview]

    @extend_schema(
        request=None, responses=EstimateSerializer, operation_id="v1_iwd_complaints_review_low_cost"
    )
    def post(self, request, pk):
        """Review low-cost estimate."""
        user_id = getattr(request.principal, "user_id", 301)
        approve = bool(request.data.get("approve", True))
        reason = request.data.get("reason", "")
        try:
            estimate = approvals.review_low_cost(pk, user_id, approve, reason)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransitionError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EstimateSerializer(estimate).data)


class ReviewMidRangeView(APIView):
    """Department Head reviews mid-range estimate (UC-IWD-041, BR-IWD-006)."""

    permission_classes = [RequireIwdModule, RequireEstimateReview]

    @extend_schema(
        request=None,
        responses=EstimateSerializer,
        operation_id="v1_iwd_complaints_review_mid_range",
    )
    def post(self, request, pk):
        """Department Head decision on mid-range estimate."""
        user_id = getattr(request.principal, "user_id", 401)
        role = getattr(request.principal, "active_role", "iwd_department_head")

        if role == "iwd_dean":
            return Response(
                {"detail": "Dean cannot perform Department Head reviews."},
                status=status.HTTP_403_FORBIDDEN,
            )

        decision = request.data.get("decision", "approve")
        remarks = request.data.get("remarks", "")
        try:
            estimate = approvals.review_mid_range(pk, user_id, decision, remarks)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except (RoleSeparationViolationError, InvalidStateTransitionError) as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(EstimateSerializer(estimate).data)


class ReviewDirectorView(APIView):
    """Director reviews high-cost or forwarded estimate (UC-IWD-051, BR-IWD-007)."""

    permission_classes = [RequireIwdModule, RequireEstimateReview]

    @extend_schema(
        request=None, responses=EstimateSerializer, operation_id="v1_iwd_complaints_review_director"
    )
    def post(self, request, pk):
        """Review high-cost or forwarded estimate."""
        user_id = getattr(request.principal, "user_id", 501)
        approve = bool(request.data.get("approve", True))
        remarks = request.data.get("remarks", "")
        try:
            estimate = approvals.review_director(pk, user_id, approve, remarks)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransitionError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EstimateSerializer(estimate).data)


class StockCheckIssueView(APIView):
    """Check stock and issue material or route to procurement (UC-IWD-061, BR-IWD-010)."""

    permission_classes = [RequireIwdModule, RequireInventoryManage]

    @extend_schema(
        request=None, responses=ComplaintSerializer, operation_id="v1_iwd_complaints_issue_material"
    )
    def post(self, request, pk):
        """Check stock and issue materials."""
        user_id = getattr(request.principal, "user_id", 301)
        item_id = int(request.data.get("item_id", 1))
        qty = int(request.data.get("quantity", 1))
        remarks = request.data.get("remarks", "")
        try:
            complaint = inventory.check_stock_and_issue(pk, item_id, qty, user_id, remarks)
        except (Complaint.DoesNotExist, InventoryItem.DoesNotExist):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransitionError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ComplaintSerializer(complaint).data)


class CompleteWorkView(APIView):
    """Mark work completed by engineer (UC-IWD-091, BW-IWD-09)."""

    permission_classes = [RequireIwdModule, RequireComplaintUpdate]

    @extend_schema(
        request=None, responses=ComplaintSerializer, operation_id="v1_iwd_complaints_complete_work"
    )
    def post(self, request, pk):
        """Mark repair work completed."""
        user_id = getattr(request.principal, "user_id", 201)
        try:
            complaint = execution.mark_work_complete(pk, user_id)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransitionError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ComplaintSerializer(complaint).data)


class VerifyWorkView(APIView):
    """Department Head physical verification of completed work (UC-IWD-101, BR-IWD-014)."""

    permission_classes = [RequireIwdModule, RequireWorkVerify]

    @extend_schema(
        request=None, responses=ComplaintSerializer, operation_id="v1_iwd_complaints_verify_work"
    )
    def post(self, request, pk):
        """Conduct physical verification."""
        user_id = getattr(request.principal, "user_id", 401)
        role = getattr(request.principal, "active_role", "iwd_department_head")

        if role == "iwd_dean":
            return Response(
                {"detail": "Dean cannot perform Department Head verification."},
                status=status.HTTP_403_FORBIDDEN,
            )

        outcome = request.data.get("outcome", "Approved")
        remarks = request.data.get("remarks", "")
        try:
            complaint = verification.verify_work(pk, user_id, outcome, remarks)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except (
            verification.MaxReworkExceededError,
            RoleSeparationViolationError,
            InvalidStateTransitionError,
        ) as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ComplaintSerializer(complaint).data)


class FinalBillView(APIView):
    """Submit final bill packet guarded by prior physical verification (UC-IWD-111)."""

    permission_classes = [RequireIwdModule, RequireEstimateCreate]

    @extend_schema(
        request=FinalBillSerializer,
        responses=FinalBillSerializer,
        operation_id="v1_iwd_complaints_final_bill",
    )
    def post(self, request, pk):
        """Submit final repair bill packet."""
        user_id = getattr(request.principal, "user_id", 201)
        amount = Decimal(str(request.data.get("total_amount", 0)))
        try:
            bill = settlement.submit_final_bill(pk, user_id, amount)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except (settlement.UnverifiedBillSubmissionError, InvalidStateTransitionError) as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FinalBillSerializer(bill).data, status=status.HTTP_201_CREATED)


class AuditFinalBillView(APIView):
    """Auditor validates final bill against approved estimate (UC-IWD-121, BR-IWD-015)."""

    permission_classes = [RequireIwdModule, RequireBillReview]

    @extend_schema(
        request=None, responses=FinalBillSerializer, operation_id="v1_iwd_complaints_audit_bill"
    )
    def post(self, request, pk):
        """Audit and validate final bill."""
        user_id = getattr(request.principal, "user_id", 601)
        outcome = request.data.get("outcome", "Validated")
        remarks = request.data.get("remarks", "")
        try:
            bill = settlement.audit_bill(pk, user_id, outcome, remarks)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransitionError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FinalBillSerializer(bill).data)


class SettlePaymentView(APIView):
    """Director payment approval and Accounts Department settlement (UC-IWD-131, BR-IWD-016)."""

    permission_classes = [RequireIwdModule, RequireBillReview]

    @extend_schema(
        request=None, responses=FinalBillSerializer, operation_id="v1_iwd_complaints_settle_payment"
    )
    def post(self, request, pk):
        """Approve or record settlement."""
        user_id = getattr(request.principal, "user_id", 701)
        action_type = request.data.get("action_type", "director_approval")
        try:
            if action_type == "director_approval":
                bill = settlement.approve_payment(pk, user_id)
            else:
                ref = request.data.get("reference", "SETTLED-REF")
                bill = settlement.settle_payment(pk, user_id, ref)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransitionError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FinalBillSerializer(bill).data)


class ComplaintFeedbackView(APIView):
    """Submit post-resolution rating, feedback, and post-repair issues (UC-IWD-141, BR-IWD-017)."""

    permission_classes = [RequireIwdModule, RequireFeedbackCreate]

    @extend_schema(
        request=ComplaintFeedbackSerializer,
        responses=ComplaintFeedbackSerializer,
        operation_id="v1_iwd_complaints_feedback",
    )
    def post(self, request, pk):
        """Submit feedback on resolved complaint."""
        user_id = getattr(request.principal, "user_id", 101)
        rating = int(request.data.get("rating", 5))
        comments = request.data.get("comments", "")
        post_issue = bool(request.data.get("post_repair_issue", False))
        post_remarks = request.data.get("post_repair_remarks", "")
        try:
            fb = feedback.submit_feedback(pk, user_id, rating, comments, post_issue, post_remarks)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except (feedback.UnresolvedFeedbackSubmissionError, InvalidStateTransitionError) as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ComplaintFeedbackSerializer(fb).data, status=status.HTTP_201_CREATED)


class ResubmitEstimateView(APIView):
    """Modify and resubmit rejected request (UC-IWD-151, BR-IWD-009)."""

    permission_classes = [RequireIwdModule, RequireEstimateCreate]

    @extend_schema(
        request=None,
        responses=EstimateSerializer,
        operation_id="v1_iwd_complaints_resubmit_estimate",
    )
    def post(self, request, pk):
        """Modify and resubmit rejected estimate."""
        user_id = getattr(request.principal, "user_id", 201)
        days = request.data.get("estimated_time_days")
        materials = request.data.get("materials_details")
        cost = request.data.get("total_cost")
        try:
            est = estimates.resubmit_estimate(pk, user_id, days, materials, cost)
        except Complaint.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except InvalidStateTransitionError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EstimateSerializer(est).data)


class InventoryListCreateView(APIView):
    """List or add inventory stock items (BR-IWD-010)."""

    permission_classes = [RequireIwdModule, RequireInventoryManage]

    @extend_schema(
        responses=InventoryItemSerializer(many=True), operation_id="v1_iwd_inventory_list"
    )
    def get(self, request):
        """List all inventory items."""
        items = InventoryItem.objects.all()
        return Response(InventoryItemSerializer(items, many=True).data)

    @extend_schema(
        request=InventoryItemSerializer,
        responses=InventoryItemSerializer,
        operation_id="v1_iwd_inventory_create",
    )
    def post(self, request):
        """Add new inventory item."""
        serializer = InventoryItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
