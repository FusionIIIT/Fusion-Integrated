from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.leave.models import LeaveType, LeaveApplication
from modules.leave.api.serializers import (
    LeaveTypeSerializer,
    LeaveApplicationSerializer,
    LeaveReviewSerializer,
)


class LeaveTypeListView(generics.ListAPIView):
    queryset = LeaveType.objects.filter(is_active=True)
    serializer_class = LeaveTypeSerializer
    permission_classes = [HasPermission("leave.application.view")]


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    serializer_class = LeaveApplicationSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasPermission("leave.application.apply")]
        return [HasPermission("leave.application.view")]

    def get_queryset(self):
        user = getattr(self.request, "principal", None)
        user_id = getattr(user, "username", "") if user else ""
        qs = LeaveApplication.objects.select_related("leave_type").all()
        # Non-approvers only see their own applications
        if user and not user.has_any_permission("leave.application.approve"):
            qs = qs.filter(applicant_id=user_id)
        return qs

    def perform_create(self, serializer):
        user = getattr(self.request, "principal", None)
        user_id = getattr(user, "username", "unknown") if user else "unknown"
        serializer.save(applicant_id=user_id)


class LeaveApplicationDetailView(generics.RetrieveAPIView):
    queryset = LeaveApplication.objects.select_related("leave_type").all()
    serializer_class = LeaveApplicationSerializer
    permission_classes = [HasPermission("leave.application.view")]


class LeaveApplicationReviewView(APIView):
    permission_classes = [HasPermission("leave.application.approve")]
    serializer_class = LeaveReviewSerializer

    def post(self, request, pk):
        try:
            application = LeaveApplication.objects.get(pk=pk)
        except LeaveApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LeaveReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = getattr(request, "principal", None)
        reviewer_id = getattr(user, "username", "system") if user else "system"

        action = serializer.validated_data["action"]
        remarks = serializer.validated_data.get("remarks", "")

        if action == "approve":
            application.status = LeaveApplication.STATUS_APPROVED
        else:
            application.status = LeaveApplication.STATUS_REJECTED

        application.reviewer_id = reviewer_id
        application.review_remarks = remarks
        application.save(update_fields=["status", "reviewer_id", "review_remarks", "updated_at"])

        return Response(LeaveApplicationSerializer(application).data)
