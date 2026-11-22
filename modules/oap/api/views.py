"""HTTP API ViewSets for Other Academic Procedures.

Handles requests, serialization, permission enforcement, and delegates to service workflows.
"""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from modules.oap.api.permissions import (
    MODULE,
    P_BONAFIDE_CREATE,
    P_BONAFIDE_ISSUE,
    P_BONAFIDE_VIEW_SELF,
    P_BRANCHCHANGE_APPLY,
    P_BRANCHCHANGE_APPROVE,
    P_BRANCHCHANGE_MANAGE,
    P_LEAVE_APPROVE,
    P_LEAVE_CREATE,
    P_LEAVE_RECOMMEND,
    P_LEAVE_VIEW_SELF,
    P_NODUES_FINALIZE,
    P_NODUES_INITIATE,
    P_NODUES_SIGNOFF,
    P_NODUES_VIEW,
    P_REQUEST_VIEW_SELF,
    HasPermission,
)
from modules.oap.api.serializers import (
    BonafideRequestSerializer,
    BranchChangeRequestSerializer,
    NoDuesDepartmentalSignoffSerializer,
    NoDuesRequestSerializer,
    StudentLeaveRequestSerializer,
)
from modules.oap.domain.exceptions import OAPDomainError
from modules.oap.models.bonafide import BonafideRequest, BonafideStatus
from modules.oap.models.branch_change import BranchChangeRequest
from modules.oap.models.leave import StudentLeaveRequest
from modules.oap.models.nodues import NoDuesRequest
from modules.oap.services.bonafide_service import (
    approve_and_issue_bonafide,
    reject_bonafide,
    submit_bonafide_request,
)
from modules.oap.services.branch_change_service import (
    allocate_and_sanction,
    submit_branch_change,
    verify_branch_change,
)
from modules.oap.services.leave_service import (
    cancel_leave,
    hod_approve_leave,
    hod_reject_leave,
    recommend_leave,
    submit_leave_application,
)
from modules.oap.services.nodues_service import (
    finalize_no_dues,
    initiate_no_dues,
    record_department_signoff,
)


class StudentLeaveViewSet(viewsets.ModelViewSet):
    queryset = StudentLeaveRequest.objects.all().order_by("-created_at")
    serializer_class = StudentLeaveRequestSerializer
    permission_classes = [MODULE]

    def get_permissions(self):
        if self.action in ["create"]:
            return [MODULE(), HasPermission(P_LEAVE_CREATE)()]
        if self.action in ["recommend"]:
            return [MODULE(), HasPermission(P_LEAVE_RECOMMEND)()]
        if self.action in ["hod_approve", "hod_reject"]:
            return [MODULE(), HasPermission(P_LEAVE_APPROVE)()]
        if self.action in ["cancel"]:
            return [MODULE(), HasPermission(P_LEAVE_CREATE, P_LEAVE_VIEW_SELF)()]
        return [
            MODULE(),
            HasPermission(
                P_LEAVE_VIEW_SELF,
                P_LEAVE_APPROVE,
                P_LEAVE_RECOMMEND,
                P_REQUEST_VIEW_SELF,
            )(),
        ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            leave = submit_leave_application(
                student_id=data["student_id"],
                student_name=data["student_name"],
                leave_type=data.get("leave_type", "CASUAL"),
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data["reason"],
                document_url=data.get("document_url"),
            )
            return Response(self.get_serializer(leave).data, status=status.HTTP_201_CREATED)
        except OAPDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="recommend")
    def recommend(self, request, pk=None):
        default_user = str(getattr(request.user, "username", "FACULTY"))
        supervisor_id = request.data.get("supervisor_id", default_user)
        remarks = request.data.get("remarks", "")
        try:
            leave = recommend_leave(request_id=pk, supervisor_id=supervisor_id, remarks=remarks)
            return Response(self.get_serializer(leave).data, status=status.HTTP_200_OK)
        except OAPDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="hod_approve")
    def hod_approve(self, request, pk=None):
        default_user = str(getattr(request.user, "username", "HOD"))
        hod_id = request.data.get("hod_id", default_user)
        remarks = request.data.get("remarks", "Approved by HoD.")
        try:
            leave = hod_approve_leave(request_id=pk, hod_id=hod_id, remarks=remarks)
            return Response(self.get_serializer(leave).data, status=status.HTTP_200_OK)
        except OAPDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="hod_reject")
    def hod_reject(self, request, pk=None):
        default_user = str(getattr(request.user, "username", "HOD"))
        hod_id = request.data.get("hod_id", default_user)
        remarks = request.data.get("remarks", "Disapproved by HoD.")
        try:
            leave = hod_reject_leave(request_id=pk, hod_id=hod_id, remarks=remarks)
            return Response(self.get_serializer(leave).data, status=status.HTTP_200_OK)
        except OAPDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        student_id = request.data.get("student_id", str(getattr(request.user, "username", "")))
        try:
            leave = cancel_leave(request_id=pk, student_id=student_id)
            return Response(self.get_serializer(leave).data, status=status.HTTP_200_OK)
        except OAPDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BonafideViewSet(viewsets.ModelViewSet):
    queryset = BonafideRequest.objects.all().order_by("-created_at")
    serializer_class = BonafideRequestSerializer
    permission_classes = [MODULE]

    def get_permissions(self):
        if self.action in ["create"]:
            return [MODULE(), HasPermission(P_BONAFIDE_CREATE)()]
        if self.action in ["approve_and_issue", "reject"]:
            return [MODULE(), HasPermission(P_BONAFIDE_ISSUE)()]
        return [
            MODULE(),
            HasPermission(
                P_BONAFIDE_VIEW_SELF,
                P_BONAFIDE_ISSUE,
                P_REQUEST_VIEW_SELF,
            )(),
        ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            req = submit_bonafide_request(
                student_id=data["student_id"],
                purpose=data.get("purpose", "GENERAL"),
                details=data.get("details", ""),
            )
            return Response(self.get_serializer(req).data, status=status.HTTP_201_CREATED)
        except OAPDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="approve_and_issue")
    def approve_and_issue(self, request, pk=None):
        default_user = str(getattr(request.user, "username", "ACADEMIC_ADMIN"))
        admin_id = request.data.get("issued_by", default_user)
        remarks = request.data.get("remarks", "Verified academic standing and issued.")
        try:
            cert_num = approve_and_issue_bonafide(
                request_id=pk, admin_id=admin_id, remarks=remarks
            )
            req = BonafideRequest.objects.get(pk=pk)
            return Response(
                {
                    "status": "APPROVED",
                    "certificate_number": cert_num,
                    "data": self.get_serializer(req).data,
                },
                status=status.HTTP_200_OK,
            )
        except OAPDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        default_user = str(getattr(request.user, "username", "ACADEMIC_ADMIN"))
        admin_id = request.data.get("issued_by", default_user)
        reason = request.data.get("reason", "Incomplete verification details.")
        try:
            req = reject_bonafide(request_id=pk, admin_id=admin_id, reason=reason)
            return Response(self.get_serializer(req).data, status=status.HTTP_200_OK)
        except OAPDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        bonafide = self.get_object()
        if bonafide.status != BonafideStatus.APPROVED:
            return Response(
                {"error": "Certificate has not been approved and issued yet."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            {
                "download_url": f"/media/bonafide/{bonafide.certificate_number}.pdf",
                "certificate_number": bonafide.certificate_number,
                "student_id": bonafide.student_id,
                "status": bonafide.status,
            },
            status=status.HTTP_200_OK,
        )


class NoDuesViewSet(viewsets.ModelViewSet):
    queryset = NoDuesRequest.objects.all().prefetch_related("signoffs")
    serializer_class = NoDuesRequestSerializer
    permission_classes = [MODULE]

    def get_permissions(self):
        if self.action in ["create"]:
            return [MODULE(), HasPermission(P_NODUES_INITIATE)()]
        if self.action in ["department_signoff"]:
            return [MODULE(), HasPermission(P_NODUES_SIGNOFF)()]
        if self.action in ["finalize"]:
            return [MODULE(), HasPermission(P_NODUES_FINALIZE)()]
        return [
            MODULE(),
            HasPermission(
                P_NODUES_VIEW,
                P_NODUES_FINALIZE,
                P_REQUEST_VIEW_SELF,
            )(),
        ]

    def create(self, request, *args, **kwargs):
        student_id = request.data.get("student_id", str(getattr(request.user, "username", "")))
        reason = request.data.get("reason", "GRADUATION")
        try:
            no_dues = initiate_no_dues(student_id=student_id, reason=reason)
            return Response(self.get_serializer(no_dues).data, status=status.HTTP_201_CREATED)
        except OAPDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="department_signoff")
    def department_signoff(self, request, pk=None):
        dept = request.data.get("department")
        signoff_status = request.data.get("status", "CLEARED")
        default_officer = str(getattr(request.user, "username", "OFFICER"))
        signoff_by = request.data.get("signoff_by", default_officer)
        dues_amount = request.data.get("dues_amount", "0.00")
        remarks = request.data.get("remarks", "")
        try:
            signoff = record_department_signoff(
                request_id=pk,
                department=dept,
                status=signoff_status,
                signoff_by=signoff_by,
                dues_amount=dues_amount,
                remarks=remarks,
            )
            return Response(
                NoDuesDepartmentalSignoffSerializer(signoff).data,
                status=status.HTTP_200_OK,
            )
        except OAPDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="finalize")
    def finalize(self, request, pk=None):
        default_admin = str(getattr(request.user, "username", "ACADEMIC_ADMIN"))
        admin_id = request.data.get("finalized_by", default_admin)
        cleared = finalize_no_dues(request_id=pk, admin_id=admin_id)
        no_dues = self.get_object()
        return Response(
            {
                "cleared": cleared,
                "overall_status": no_dues.overall_status,
                "data": self.get_serializer(no_dues).data,
            },
            status=status.HTTP_200_OK,
        )


class BranchChangeViewSet(viewsets.ModelViewSet):
    queryset = BranchChangeRequest.objects.all().order_by("-current_cpi")
    serializer_class = BranchChangeRequestSerializer
    permission_classes = [MODULE]

    def get_permissions(self):
        if self.action in ["create"]:
            return [MODULE(), HasPermission(P_BRANCHCHANGE_APPLY)()]
        if self.action in ["verify"]:
            return [MODULE(), HasPermission(P_BRANCHCHANGE_MANAGE)()]
        if self.action in ["allocate"]:
            return [
                MODULE(),
                HasPermission(P_BRANCHCHANGE_APPROVE, P_BRANCHCHANGE_MANAGE)(),
            ]
        return [
            MODULE(),
            HasPermission(
                P_BRANCHCHANGE_APPLY,
                P_BRANCHCHANGE_MANAGE,
                P_REQUEST_VIEW_SELF,
            )(),
        ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            bc = submit_branch_change(
                student_id=data["student_id"],
                current_branch=data["current_branch"],
                preferred_branch_1=data["preferred_branch_1"],
                preferred_branch_2=data.get("preferred_branch_2", ""),
                current_cpi=data["current_cpi"],
                credits_completed=data.get("credits_completed", 0),
                has_backlogs=data.get("has_backlogs", False),
            )
            return Response(self.get_serializer(bc).data, status=status.HTTP_201_CREATED)
        except OAPDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request, pk=None):
        eligible = verify_branch_change(request_id=pk)
        bc = self.get_object()
        return Response(
            {"eligible": eligible, "status": bc.status, "data": self.get_serializer(bc).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="allocate")
    def allocate(self, request, pk=None):
        allocated_branch = request.data.get("allocated_branch")
        default_approver = str(getattr(request.user, "username", "DEAN_ACADEMICS"))
        approved_by = request.data.get("approved_by", default_approver)
        try:
            bc = allocate_and_sanction(
                request_id=pk, allocated_branch=allocated_branch, approved_by=approved_by
            )
            return Response(self.get_serializer(bc).data, status=status.HTTP_200_OK)
        except OAPDomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
