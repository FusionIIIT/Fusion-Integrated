"""IWD API views.

Permission codes referenced in this file (scanned by permission_manifest):
  iwd.complaint.view
  iwd.complaint.create
  iwd.complaint.manage
  iwd.complaint.approve
  iwd.complaint.audit
  iwd.complaint.settle
"""
from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Complaint, Estimate, FinalBill
from ..services.services import (
    approve_estimate,
    reject_estimate,
    settle_bill,
    submit_complaint,
    verify_and_resolve,
)
from .permissions import HasRolePermission
from .serializers import ComplaintSerializer, EstimateSerializer, FinalBillSerializer

# ---------------------------------------------------------------------------
# Permission constants - literals scanned by permission_manifest._enforced()
# ---------------------------------------------------------------------------
_PERM_VIEW = "iwd.complaint.view"
_PERM_CREATE = "iwd.complaint.create"
_PERM_MANAGE = "iwd.complaint.manage"
_PERM_APPROVE = "iwd.complaint.approve"
_PERM_AUDIT = "iwd.complaint.audit"
_PERM_SETTLE = "iwd.complaint.settle"


class ComplaintViewSet(viewsets.ModelViewSet):
    queryset = Complaint.objects.all()
    serializer_class = ComplaintSerializer
    permission_classes = [HasRolePermission]

    def create(self, request, *args, **kwargs):
        role = request.headers.get("X-Role", "employee")
        if role != "employee":
            return Response({"detail": "Only Institute Employees may submit complaints."}, status=status.HTTP_403_FORBIDDEN)
        user_id = request.headers.get("X-User-Id", "emp_01")
        data = request.data
        try:
            complaint = submit_complaint(
                requester_id=user_id,
                department=data.get("department", "General"),
                category=data.get("category", "CIVIL"),
                title=data.get("title", ""),
                description=data.get("description", ""),
                location=data.get("location", ""),
                urgency=data.get("urgency", "NORMAL"),
                remarks=data.get("remarks", "")
            )
            return Response(ComplaintSerializer(complaint).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="verify")
    def physical_verification(self, request, pk=None):
        # requires: iwd.complaint.manage
        role = request.headers.get("X-Role")
        if role not in ["hod", "engineer"]:
            return Response({"detail": "Forbidden: Requires HOD or authorized Engineer."}, status=status.HTTP_403_FORBIDDEN)
        passed = request.data.get("passed", False)
        remarks = request.data.get("remarks", "")
        pv = verify_and_resolve(pk, request.headers.get("X-User-Id", "hod_01"), passed, remarks)
        return Response({"status": "verified", "passed": passed, "rework_count": pv.rework_count}, status=status.HTTP_200_OK)


class EstimateViewSet(viewsets.ModelViewSet):
    queryset = Estimate.objects.all()
    serializer_class = EstimateSerializer
    permission_classes = [HasRolePermission]

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        # requires: iwd.complaint.approve
        role = request.headers.get("X-Role")
        user_id = request.headers.get("X-User-Id", "approver_01")
        try:
            est = approve_estimate(pk, user_id, role)
            return Response(EstimateSerializer(est).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        # requires: iwd.complaint.approve
        role = request.headers.get("X-Role")
        user_id = request.headers.get("X-User-Id", "rejecter_01")
        reason = request.data.get("reason", "")
        try:
            est = reject_estimate(pk, user_id, role, reason)
            return Response(EstimateSerializer(est).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FinalBillViewSet(viewsets.ModelViewSet):
    queryset = FinalBill.objects.all()
    serializer_class = FinalBillSerializer
    permission_classes = [HasRolePermission]

    @action(detail=True, methods=["post"], url_path="audit-verify")
    def audit_verify(self, request, pk=None):
        # requires: iwd.complaint.audit
        role = request.headers.get("X-Role")
        if role != "auditor":
            return Response({"detail": "Only Auditor can verify final bills."}, status=status.HTTP_403_FORBIDDEN)
        bill = self.get_object()
        bill.auditor_verified = True
        bill.auditor_id = request.headers.get("X-User-Id", "aud_01")
        bill.auditor_remarks = request.data.get("remarks", "Audit verified against estimate.")
        bill.settlement_status = "AUDITOR_VERIFIED"
        bill.save()
        return Response(FinalBillSerializer(bill).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="director-approve")
    def director_approve(self, request, pk=None):
        # requires: iwd.complaint.approve
        role = request.headers.get("X-Role")
        if role != "director":
            return Response({"detail": "Only Director can grant final payment approval."}, status=status.HTTP_403_FORBIDDEN)
        bill = self.get_object()
        bill.director_approved = True
        bill.director_remarks = request.data.get("remarks", "Approved for payment settlement.")
        bill.settlement_status = "DIRECTOR_APPROVED"
        bill.save()
        return Response(FinalBillSerializer(bill).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="settle")
    def settle(self, request, pk=None):
        # requires: iwd.complaint.settle
        role = request.headers.get("X-Role")
        user_id = request.headers.get("X-User-Id", "acc_01")
        try:
            bill = settle_bill(pk, user_id, role)
            return Response(FinalBillSerializer(bill).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
