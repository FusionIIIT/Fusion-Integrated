from decimal import Decimal
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from modules.iwd.api.serializers import (
    ComplaintFeedbackSerializer,
    ComplaintSerializer,
    DecisionAuditTrailSerializer,
    FinalBillSerializer,
    InventoryItemSerializer,
    MaterialIssueLedgerSerializer,
    PhysicalVerificationSerializer,
    ProcurementOrderSerializer,
    RepairAssessmentSerializer,
    RepairEstimateSerializer,
    ReviewCommitteeOutcomeSerializer,
)
from modules.iwd.selectors.complaints import (
    get_all_inventory,
    get_scoped_complaint,
    scope_complaints_for_actor,
    scope_estimates_for_complaint,
)
from modules.iwd.services.complaints import (
    create_complaint,
    flag_urgent,
    record_assessment,
)
from modules.iwd.services.estimates import (
    create_estimate,
    record_committee_review,
    review_director,
    review_low_cost,
    review_mid_range,
)
from modules.iwd.services.execution import (
    audit_final_bill,
    complete_repair_work,
    record_physical_verification,
    settle_payment,
    submit_feedback,
    submit_final_bill,
)
from modules.iwd.services.inventory import (
    conduct_procurement_or_bidding,
    issue_materials,
)


class ComplaintListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = request.headers.get("X-Active-Role", "employee")
        qs = scope_complaints_for_actor(request.user.id, role)
        serializer = ComplaintSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        complaint = create_complaint(
            complainant_user_id=request.user.id,
            category=data["category"],
            location=data["location"],
            urgency=data["urgency"],
            remarks=data.get("remarks", ""),
        )
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_201_CREATED)


class ComplaintDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        role = request.headers.get("X-Active-Role", "employee")
        complaint = get_scoped_complaint(pk, request.user.id, role)
        return Response(ComplaintSerializer(complaint).data)


class ComplaintAssessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        role = request.headers.get("X-Active-Role", "engineer")
        complaint = get_scoped_complaint(pk, request.user.id, role)
        assessment = record_assessment(
            complaint=complaint,
            engineer_id=request.user.id,
            assessment_details=request.data.get("assessment_details", ""),
            is_site_visit_complete=request.data.get("is_site_visit_complete", True),
        )
        return Response(RepairAssessmentSerializer(assessment).data, status=status.HTTP_201_CREATED)


class ComplaintUrgentFlagView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        role = request.headers.get("X-Active-Role", "engineer")
        complaint = get_scoped_complaint(pk, request.user.id, role)
        complaint = flag_urgent(
            complaint=complaint,
            engineer_id=request.user.id,
            escalated_to=request.data.get("escalated_to", "department_head"),
        )
        return Response(ComplaintSerializer(complaint).data)


class ComplaintEstimateListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        role = request.headers.get("X-Active-Role", "employee")
        get_scoped_complaint(pk, request.user.id, role)
        estimates = scope_estimates_for_complaint(pk)
        return Response(RepairEstimateSerializer(estimates, many=True).data)

    def post(self, request, pk):
        role = request.headers.get("X-Active-Role", "engineer")
        complaint = get_scoped_complaint(pk, request.user.id, role)
        estimate = create_estimate(
            complaint=complaint,
            engineer_id=request.user.id,
            time_estimate_days=int(request.data["time_estimate_days"]),
            materials_cost=Decimal(str(request.data["materials_cost"])),
            labor_cost=Decimal(str(request.data["labor_cost"])),
            other_cost=Decimal(str(request.data.get("other_cost", "0.00"))),
        )
        return Response(RepairEstimateSerializer(estimate).data, status=status.HTTP_201_CREATED)


class EstimateReviewLowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from modules.iwd.models.estimate import RepairEstimate
        estimate = RepairEstimate.objects.get(id=pk)
        estimate = review_low_cost(
            estimate=estimate,
            admin_user_id=request.user.id,
            approve=request.data.get("approve", True),
            rejection_reason=request.data.get("rejection_reason", ""),
        )
        return Response(RepairEstimateSerializer(estimate).data)


class EstimateCommitteeReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from modules.iwd.models.estimate import RepairEstimate
        estimate = RepairEstimate.objects.get(id=pk)
        review = record_committee_review(
            estimate=estimate,
            reviewer_user_id=request.user.id,
            is_feasible=request.data.get("is_feasible", True),
            is_necessary=request.data.get("is_necessary", True),
            remarks=request.data.get("remarks", ""),
        )
        return Response(ReviewCommitteeOutcomeSerializer(review).data, status=status.HTTP_201_CREATED)


class EstimateReviewMidView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from modules.iwd.models.estimate import RepairEstimate
        estimate = RepairEstimate.objects.get(id=pk)
        estimate = review_mid_range(
            estimate=estimate,
            dept_head_user_id=request.user.id,
            action=request.data.get("action", "approve"),
            reason=request.data.get("reason", ""),
        )
        return Response(RepairEstimateSerializer(estimate).data)


class EstimateReviewDirectorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from modules.iwd.models.estimate import RepairEstimate
        estimate = RepairEstimate.objects.get(id=pk)
        estimate = review_director(
            estimate=estimate,
            director_user_id=request.user.id,
            action=request.data.get("action", "approve_high"),
            reason=request.data.get("reason", ""),
        )
        return Response(RepairEstimateSerializer(estimate).data)


class InventoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = get_all_inventory()
        return Response(InventoryItemSerializer(items, many=True).data)


class ComplaintIssueMaterialsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        role = request.headers.get("X-Active-Role", "iwd_admin")
        complaint = get_scoped_complaint(pk, request.user.id, role)
        ledger = issue_materials(
            complaint=complaint,
            admin_user_id=request.user.id,
            item_id=request.data["item_id"],
            quantity=int(request.data["quantity"]),
        )
        return Response(MaterialIssueLedgerSerializer(ledger).data, status=status.HTTP_201_CREATED)


class ComplaintProcureView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        role = request.headers.get("X-Active-Role", "iwd_admin")
        complaint = get_scoped_complaint(pk, request.user.id, role)
        order = conduct_procurement_or_bidding(
            complaint=complaint,
            admin_user_id=request.user.id,
            procurement_type=request.data.get("procurement_type", "internal_quotation"),
            vendor_name=request.data["vendor_name"],
            quoted_amount=Decimal(str(request.data["quoted_amount"])),
            vendor_details=request.data.get("vendor_details", ""),
        )
        return Response(ProcurementOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class ComplaintCompleteWorkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        role = request.headers.get("X-Active-Role", "engineer")
        complaint = get_scoped_complaint(pk, request.user.id, role)
        complaint = complete_repair_work(complaint, request.user.id)
        return Response(ComplaintSerializer(complaint).data)


class ComplaintVerifyWorkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        role = request.headers.get("X-Active-Role", "department_head")
        complaint = get_scoped_complaint(pk, request.user.id, role)
        verif = record_physical_verification(
            complaint=complaint,
            dept_head_user_id=request.user.id,
            approve=request.data.get("approve", True),
            remarks=request.data.get("remarks", ""),
            rework_notes=request.data.get("rework_notes", ""),
        )
        return Response(PhysicalVerificationSerializer(verif).data, status=status.HTTP_201_CREATED)


class ComplaintFinalBillView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        role = request.headers.get("X-Active-Role", "engineer")
        complaint = get_scoped_complaint(pk, request.user.id, role)
        bill = submit_final_bill(
            complaint=complaint,
            engineer_id=request.user.id,
            invoice_number=request.data["invoice_number"],
            claimed_amount=Decimal(str(request.data["claimed_amount"])),
        )
        return Response(FinalBillSerializer(bill).data, status=status.HTTP_201_CREATED)


class BillAuditView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from modules.iwd.models.completion import FinalBill
        bill = FinalBill.objects.get(id=pk)
        bill = audit_final_bill(
            bill=bill,
            auditor_user_id=request.user.id,
            remarks=request.data.get("remarks", "Audited and verified against estimate"),
        )
        return Response(FinalBillSerializer(bill).data)


class BillSettleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from modules.iwd.models.completion import FinalBill
        bill = FinalBill.objects.get(id=pk)
        role = request.headers.get("X-Active-Role", "director")
        bill = settle_payment(
            bill=bill,
            user_id=request.user.id,
            role=role,
            accounts_ref=request.data.get("accounts_reference", ""),
        )
        return Response(FinalBillSerializer(bill).data)


class ComplaintFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        role = request.headers.get("X-Active-Role", "employee")
        complaint = get_scoped_complaint(pk, request.user.id, role)
        try:
            return Response(ComplaintFeedbackSerializer(complaint.feedback).data)
        except Exception:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, pk):
        role = request.headers.get("X-Active-Role", "employee")
        complaint = get_scoped_complaint(pk, request.user.id, role)
        feedback = submit_feedback(
            complaint=complaint,
            user_id=request.user.id,
            rating=int(request.data["rating"]),
            feedback_text=request.data.get("feedback_text", ""),
            post_repair_issue=request.data.get("post_repair_issue", ""),
        )
        return Response(ComplaintFeedbackSerializer(feedback).data, status=status.HTTP_201_CREATED)
