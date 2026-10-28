from rest_framework import generics
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.models import LeaveApplication
from .serializers import LeaveSerializer

MODULE = HasModuleGrant("elm")


class LeaveApplyAPIView(generics.CreateAPIView):
    """Employee applies for leave."""
    permission_classes = [MODULE, HasPermission("elm.leave.apply")]
    serializer_class = LeaveSerializer

    def perform_create(self, serializer):
        serializer.save(applicant_id=self.request.user.user_id, status="pending")


class MyLeavesAPIView(generics.ListAPIView):
    """Employee sees only their own leaves."""
    permission_classes = [MODULE, HasPermission("elm.leave.view_self")]
    serializer_class = LeaveSerializer

    def get_queryset(self):
        return LeaveApplication.objects.filter(
            applicant_id=self.request.user.user_id).order_by("-start_date")


class LeaveCancelAPIView(APIView):
    """Employee cancels their own leave while it is still pending."""
    permission_classes = [MODULE, HasPermission("elm.leave.cancel")]

    def post(self, request, pk):
        leave = generics.get_object_or_404(LeaveApplication, pk=pk)
        if leave.applicant_id != request.user.user_id:
            raise PermissionDenied("You can only cancel your own leave.")
        if leave.status != "pending":
            raise ValidationError("Only pending leave can be cancelled.")
        leave.status = "cancelled"
        leave.save()
        return Response(LeaveSerializer(leave).data)


class PendingLeavesAPIView(generics.ListAPIView):
    """Approver sees all pending leaves."""
    permission_classes = [MODULE, HasPermission("elm.leave.view_pending")]
    serializer_class = LeaveSerializer

    def get_queryset(self):
        return LeaveApplication.objects.filter(status="pending").order_by("start_date")


class LeaveApproveAPIView(APIView):
    """Approver approves or rejects a pending leave."""
    permission_classes = [MODULE, HasPermission("elm.leave.approve")]

    def post(self, request, pk):
        leave = generics.get_object_or_404(LeaveApplication, pk=pk)
        decision = request.data.get("decision")
        if decision not in ("approved", "rejected"):
            raise ValidationError('decision must be "approved" or "rejected".')
        if leave.status != "pending":
            raise ValidationError("Only pending leave can be approved or rejected.")
        if leave.applicant_id == request.user.user_id:
            raise PermissionDenied("You cannot approve your own leave.")
        leave.status = decision
        leave.approver_id = request.user.user_id
        leave.comments = request.data.get("comments", leave.comments)
        leave.save()
        return Response(LeaveSerializer(leave).data)