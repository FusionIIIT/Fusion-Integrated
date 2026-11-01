"""API views and ViewSets for IWD."""
from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from modules.iwd.models import (
    Complaint,
    Estimate,
    InventoryItem,
    InventoryMovement,
    ProcurementRequest,
    WorkVerification,
    BillAndSettlement,
    ComplaintFeedback,
    ComplaintStatus,
    EstimateStatus,
)
from modules.iwd.api.serializers import (
    ComplaintSerializer,
    EstimateSerializer,
    InventoryItemSerializer,
    InventoryMovementSerializer,
    ProcurementRequestSerializer,
    WorkVerificationSerializer,
    BillAndSettlementSerializer,
    ComplaintFeedbackSerializer,
)
from modules.iwd.domain.rules import (
    determine_cost_band,
    CostBand,
    can_resolve_complaint,
    can_proceed_to_settlement,
)


class ComplaintViewSet(viewsets.ModelViewSet):
    queryset = Complaint.objects.all()
    serializer_class = ComplaintSerializer

    def perform_create(self, serializer):
        # BR-IWD-002: Automatic engineer assignment
        serializer.save(
            assigned_engineer_id="eng_default_01",
            status=ComplaintStatus.ASSIGNED,
        )

    @action(detail=True, methods=["post"], url_path="assess")
    def assess_complaint(self, request, pk=None):
        complaint = self.get_object()
        notes = request.data.get("assessment_notes", "")
        complaint.assessment_notes = notes
        complaint.status = ComplaintStatus.ASSESSED
        complaint.save()
        return Response({"status": "assessed", "notes": notes})

    @action(detail=True, methods=["post"], url_path="flag-urgent")
    def flag_urgent(self, request, pk=None):
        complaint = self.get_object()
        complaint.is_urgent = True
        complaint.save()
        return Response({"status": "flagged_urgent", "is_urgent": True})


class EstimateViewSet(viewsets.ModelViewSet):
    queryset = Estimate.objects.all()
    serializer_class = EstimateSerializer

    @action(detail=True, methods=["post"], url_path="committee-review")
    def committee_review(self, request, pk=None):
        estimate = self.get_object()
        remarks = request.data.get("committee_remarks", "Feasible")
        estimate.committee_remarks = remarks
        estimate.status = EstimateStatus.DEPT_HEAD_PENDING
        estimate.save()
        return Response({"status": "reviewed_by_committee", "estimate_status": estimate.status})

    @action(detail=True, methods=["post"], url_path="approve")
    def approve_estimate(self, request, pk=None):
        estimate = self.get_object()
        approver = request.data.get("approved_by", "admin")
        estimate.status = EstimateStatus.APPROVED
        estimate.approved_by = approver
        estimate.save()

        # Update parent complaint
        complaint = estimate.complaint
        complaint.status = ComplaintStatus.ESTIMATE_APPROVED
        complaint.save()

        return Response({"status": "approved", "estimate_status": estimate.status})

    @action(detail=True, methods=["post"], url_path="forward-director")
    def forward_to_director(self, request, pk=None):
        estimate = self.get_object()
        estimate.status = EstimateStatus.DIRECTOR_PENDING
        estimate.save()
        return Response({"status": "forwarded_to_director", "estimate_status": estimate.status})

    @action(detail=True, methods=["post"], url_path="reject")
    def reject_estimate(self, request, pk=None):
        estimate = self.get_object()
        reason = request.data.get("rejection_reason", "Not justified")
        estimate.rejection_reason = reason
        if estimate.cost_band == CostBand.LOW:
            estimate.status = EstimateStatus.REJECTED_LOW
        elif estimate.cost_band == CostBand.MID:
            estimate.status = EstimateStatus.REJECTED_MID
        else:
            estimate.status = EstimateStatus.REJECTED_DIRECTOR
        estimate.save()
        return Response({"status": "rejected", "reason": reason, "estimate_status": estimate.status})


class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer

    @action(detail=True, methods=["post"], url_path="issue")
    def issue_material(self, request, pk=None):
        item = self.get_object()
        quantity = int(request.data.get("quantity", 0))
        complaint_id = request.data.get("complaint_id")
        recorded_by = request.data.get("recorded_by", "admin")

        if quantity <= 0:
            return Response({"error": "Invalid quantity"}, status=status.HTTP_400_BAD_REQUEST)
        if item.quantity_in_stock < quantity:
            return Response({"error": "Insufficient stock"}, status=status.HTTP_400_BAD_REQUEST)

        item.quantity_in_stock -= quantity
        item.save()

        InventoryMovement.objects.create(
            item=item,
            complaint_id=complaint_id,
            movement_type="ISSUE",
            quantity=quantity,
            recorded_by=recorded_by,
        )

        if complaint_id:
            complaint = Complaint.objects.filter(pk=complaint_id).first()
            if complaint:
                complaint.status = ComplaintStatus.MATERIALS_ISSUED
                complaint.save()

        return Response({"status": "issued", "remaining_stock": item.quantity_in_stock})


class WorkVerificationViewSet(viewsets.ModelViewSet):
    queryset = WorkVerification.objects.all()
    serializer_class = WorkVerificationSerializer

    def perform_create(self, serializer):
        verification = serializer.save()
        complaint = verification.complaint
        if verification.passed:
            complaint.status = ComplaintStatus.RESOLVED
        else:
            complaint.status = ComplaintStatus.REWORK_REQUIRED
        complaint.save()


class BillAndSettlementViewSet(viewsets.ModelViewSet):
    queryset = BillAndSettlement.objects.all()
    serializer_class = BillAndSettlementSerializer

    @action(detail=True, methods=["post"], url_path="audit-validate")
    def audit_validate(self, request, pk=None):
        bill = self.get_object()
        bill.auditor_id = request.data.get("auditor_id", "auditor_1")
        bill.auditor_notes = request.data.get("notes", "Validated")
        bill.auditor_validated = True
        bill.save()
        return Response({"status": "audit_validated"})

    @action(detail=True, methods=["post"], url_path="director-approve")
    def director_approve(self, request, pk=None):
        bill = self.get_object()
        bill.director_approved = True
        bill.save()
        return Response({"status": "director_approved"})

    @action(detail=True, methods=["post"], url_path="settle")
    def settle_payment(self, request, pk=None):
        bill = self.get_object()
        if not can_proceed_to_settlement(bill.auditor_validated, bill.director_approved):
            return Response({"error": "Requires Auditor validation and Director approval prior to settlement"}, status=status.HTTP_400_BAD_REQUEST)
        bill.settlement_status = "SETTLED"
        bill.save()
        bill.complaint.status = ComplaintStatus.SETTLED
        bill.complaint.save()
        return Response({"status": "settled"})


class ComplaintFeedbackViewSet(viewsets.ModelViewSet):
    queryset = ComplaintFeedback.objects.all()
    serializer_class = ComplaintFeedbackSerializer

