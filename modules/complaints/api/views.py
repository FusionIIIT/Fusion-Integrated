"""HTTP API Views for Complaint Management System."""
from __future__ import annotations

from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.complaints.api import serializers as s
from modules.complaints.selectors import complaints as sel
from modules.complaints.services import complaints as svc

MODULE = HasModuleGrant("complaints")


class ComplaintListCreateView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        if not (request.principal.has_perm("complaints.complaint.view") or
                request.principal.has_perm("complaints.complaint.view_self")):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        qs = sel.visible_complaints(request.principal)
        serializer = s.ComplaintListSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not request.principal.has_perm("complaints.complaint.create"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        serializer = s.ComplaintCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        complaint = svc.submit_complaint(
            complainant_user_id=request.principal.erp_user_id,
            category=data["category"],
            description=data["description"],
            priority=data.get("priority", "low"),
            attachments=data.get("attachments", []),
        )

        out = s.ComplaintDetailSerializer(complaint)
        return Response(out.data, status=status.HTTP_201_CREATED)


class ComplaintDetailView(APIView):
    permission_classes = [MODULE]

    def get(self, request, pk: int):
        complaint = sel.get_complaint_by_id(pk, principal=request.principal)
        if not complaint:
            raise NotFound("Complaint not found.")
        serializer = s.ComplaintDetailSerializer(complaint)
        return Response(serializer.data)


class ComplaintHandlingSetupView(APIView):
    permission_classes = [MODULE, HasPermission("complaints.complaint.assign")]

    def post(self, request, pk: int):
        serializer = s.HandlingSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        complaint = svc.setup_handling(
            complaint_id=pk,
            principal=request.principal,
            handler_user_id=data["handler_user_id"],
            category=data.get("category"),
            priority=data.get("priority"),
        )
        return Response(s.ComplaintDetailSerializer(complaint).data)


class ComplaintProgressUpdateView(APIView):
    permission_classes = [MODULE, HasPermission("complaints.complaint.update")]

    def post(self, request, pk: int):
        serializer = s.ProgressUpdateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        progress = svc.update_progress(
            complaint_id=pk,
            principal=request.principal,
            notes=data["notes"],
        )
        return Response(s.ProgressUpdateSerializer(progress).data, status=status.HTTP_201_CREATED)


class ComplaintResolveView(APIView):
    permission_classes = [MODULE, HasPermission("complaints.complaint.resolve")]

    def post(self, request, pk: int):
        serializer = s.ResolveComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        complaint = svc.resolve_complaint(
            complaint_id=pk,
            principal=request.principal,
            resolution_details=data["resolution_details"],
        )
        return Response(s.ComplaintDetailSerializer(complaint).data)


class ComplaintRejectView(APIView):
    permission_classes = [MODULE, HasPermission("complaints.complaint.reject")]

    def post(self, request, pk: int):
        serializer = s.RejectComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        complaint = svc.reject_complaint(
            complaint_id=pk,
            principal=request.principal,
            rejection_reason=data["rejection_reason"],
        )
        return Response(s.ComplaintDetailSerializer(complaint).data)


class ComplaintVerifyClosureView(APIView):
    permission_classes = [MODULE, HasPermission("complaints.complaint.verify")]

    def post(self, request, pk: int):
        serializer = s.VerifyClosureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        complaint = svc.verify_closure(
            complaint_id=pk,
            principal=request.principal,
            is_satisfied=data.get("is_satisfied", True),
            comments=data.get("comments", ""),
            verifier_role=data.get("verifier_role", "complainant"),
        )
        return Response(s.ComplaintDetailSerializer(complaint).data)


class ComplaintReopeningRequestView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk: int):
        serializer = s.ReopeningRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        req = svc.request_reopening(
            complaint_id=pk,
            principal=request.principal,
            reason=data["reason"],
        )
        return Response(s.ReopeningRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class ComplaintReopeningReviewView(APIView):
    permission_classes = [MODULE, HasPermission("complaints.complaint.reopen")]

    def post(self, request, pk: int):
        serializer = s.ReopeningReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        req = svc.review_reopening(
            reopening_request_id=pk,
            principal=request.principal,
            approved=data["approved"],
            decision_notes=data.get("decision_notes", ""),
        )
        return Response(s.ReopeningRequestSerializer(req).data)


class ComplaintFeedbackView(APIView):
    permission_classes = [MODULE, HasPermission("complaints.feedback.submit")]

    def post(self, request, pk: int):
        serializer = s.FeedbackCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        fb = svc.submit_feedback(
            complaint_id=pk,
            principal=request.principal,
            rating=data["rating"],
            comments=data.get("comments", ""),
        )
        return Response(s.ComplaintFeedbackSerializer(fb).data, status=status.HTTP_201_CREATED)


class ComplaintFeedbackListView(APIView):
    permission_classes = [MODULE, HasPermission("complaints.feedback.view")]

    def get(self, request):
        feedbacks = sel.get_feedback_list(request.principal)
        return Response(s.ComplaintFeedbackSerializer(feedbacks, many=True).data)


class ComplaintEscalateView(APIView):
    permission_classes = [MODULE, HasPermission("complaints.complaint.escalate")]

    def post(self, request, pk: int):
        serializer = s.EscalateComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        complaint = svc.escalate_manually(
            complaint_id=pk,
            principal=request.principal,
            reason=data["reason"],
        )
        return Response(s.ComplaintDetailSerializer(complaint).data)


class AnnouncementListCreateView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        if not request.principal.has_perm("complaints.announcement.view"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        announcements = sel.get_announcements(request.principal)
        return Response(s.AnnouncementSerializer(announcements, many=True).data)

    def post(self, request):
        if not request.principal.has_perm("complaints.announcement.publish"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.AnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ann = svc.publish_announcement(
            principal=request.principal,
            title=data["title"],
            content=data["content"],
            target_audience=data.get("target_audience", "all"),
            expires_at=data.get("expires_at"),
        )
        return Response(s.AnnouncementSerializer(ann).data, status=status.HTTP_201_CREATED)


class CMSRoleManagementView(APIView):
    permission_classes = [MODULE, HasPermission("complaints.role.manage")]

    def post(self, request):
        serializer = s.RoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        assignment = svc.assign_cms_role(
            principal=request.principal,
            user_id=data["user_id"],
            role_name=data["role_name"],
            valid_from=data["valid_from"],
            valid_to=data.get("valid_to"),
        )
        return Response(s.RoleAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class CMSOperationalReportView(APIView):
    permission_classes = [MODULE, HasPermission("complaints.report.view")]

    def get(self, request):
        summary = sel.get_operational_summary()
        return Response(summary)
