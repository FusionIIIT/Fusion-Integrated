from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from fusion_auth.permissions import HasModuleGrant, HasPermission
from ..models import LeaveBalance, LeaveApplication, LeaveAction, LeaveStatus, SubstituteStatus
from .serializers import (
    LeaveBalanceSerializer,
    LeaveApplicationSerializer,
    LeaveApplicationCreateSerializer,
    SubstituteActionSerializer,
    ApprovalActionSerializer,
)


def get_caller_id(request) -> int:
    if hasattr(request, "principal") and request.principal:
        uid = getattr(request.principal, "erp_user_id", None)
        if uid:
            return uid
    if hasattr(request, "user") and request.user and request.user.is_authenticated:
        return request.user.id
    return 1


class LeaveBalanceListView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]
    serializer_class = LeaveBalanceSerializer

    def get_queryset(self):
        user_id = get_caller_id(self.request)
        return LeaveBalance.objects.filter(user_id=user_id)


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [HasModuleGrant("elm"), HasPermission("elm.leave.create")]
        return [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return LeaveApplicationCreateSerializer
        return LeaveApplicationSerializer

    def get_queryset(self):
        user_id = get_caller_id(self.request)
        return LeaveApplication.objects.filter(applicant_id=user_id).order_by("-created_at")

    def perform_create(self, serializer):
        user_id = get_caller_id(self.request)
        substitute_id = serializer.validated_data.get("substitute_id")
        initial_status = LeaveStatus.PENDING_SUBSTITUTE if substitute_id else LeaveStatus.PENDING_UNIT_HEAD
        sub_status = SubstituteStatus.PENDING if substitute_id else SubstituteStatus.ACCEPTED

        app = serializer.save(
            applicant_id=user_id,
            status=initial_status,
            substitute_status=sub_status,
        )
        LeaveAction.objects.create(
            application=app,
            actor_id=user_id,
            action="submitted",
            comments=serializer.validated_data.get("reason", ""),
        )


class LeaveApplicationDetailView(generics.RetrieveAPIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]
    serializer_class = LeaveApplicationSerializer
    queryset = LeaveApplication.objects.all()


class LeaveWithdrawView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]
    serializer_class = LeaveApplicationSerializer

    def post(self, request, pk: int):
        user_id = get_caller_id(request)
        try:
            app = LeaveApplication.objects.get(pk=pk, applicant_id=user_id)
        except LeaveApplication.DoesNotExist:
            return Response({"error": "Leave application not found."}, status=status.HTTP_404_NOT_FOUND)

        if app.status in [LeaveStatus.APPROVED, LeaveStatus.REJECTED, LeaveStatus.WITHDRAWN, LeaveStatus.CANCELLED]:
            return Response({"error": f"Cannot withdraw leave with status {app.status}."}, status=status.HTTP_400_BAD_REQUEST)

        app.status = LeaveStatus.WITHDRAWN
        app.save(update_fields=["status", "updated_at"])
        LeaveAction.objects.create(
            application=app,
            actor_id=user_id,
            action="withdrawn",
            comments="Withdrawn by applicant.",
        )
        return Response(LeaveApplicationSerializer(app).data)


class ApprovalQueueListView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.approve")]
    serializer_class = LeaveApplicationSerializer

    def get_queryset(self):
        return LeaveApplication.objects.filter(
            status__in=[LeaveStatus.SUBMITTED, LeaveStatus.PENDING_UNIT_HEAD, LeaveStatus.PENDING_SANCTION]
        ).order_by("-created_at")


class ApprovalActionView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.approve")]
    serializer_class = ApprovalActionSerializer

    def post(self, request, pk: int):
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_caller_id(request)

        try:
            app = LeaveApplication.objects.get(pk=pk)
        except LeaveApplication.DoesNotExist:
            return Response({"error": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        act = serializer.validated_data["action"]
        comments = serializer.validated_data.get("comments", "")

        if act == "approve":
            app.status = LeaveStatus.APPROVED
        elif act == "reject":
            app.status = LeaveStatus.REJECTED
            app.rejection_reason = comments
        elif act == "recommend":
            app.status = LeaveStatus.PENDING_SANCTION
            app.unit_head_recommendation = "recommended"

        app.save()
        LeaveAction.objects.create(
            application=app,
            actor_id=user_id,
            action=act,
            comments=comments,
        )
        return Response(LeaveApplicationSerializer(app).data)


class SubstituteQueueListView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.substitute")]
    serializer_class = LeaveApplicationSerializer

    def get_queryset(self):
        user_id = get_caller_id(self.request)
        return LeaveApplication.objects.filter(
            substitute_id=user_id,
            substitute_status=SubstituteStatus.PENDING,
        ).order_by("-created_at")


class SubstituteActionView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.substitute")]
    serializer_class = SubstituteActionSerializer

    def post(self, request, pk: int):
        serializer = SubstituteActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_caller_id(request)

        try:
            app = LeaveApplication.objects.get(pk=pk, substitute_id=user_id)
        except LeaveApplication.DoesNotExist:
            return Response({"error": "Substitute request not found."}, status=status.HTTP_404_NOT_FOUND)

        act = serializer.validated_data["action"]
        comments = serializer.validated_data.get("comments", "")

        if act == "accept":
            app.substitute_status = SubstituteStatus.ACCEPTED
            app.status = LeaveStatus.PENDING_UNIT_HEAD
        else:
            app.substitute_status = SubstituteStatus.DECLINED

        app.save()
        LeaveAction.objects.create(
            application=app,
            actor_id=user_id,
            action=f"substitute_{act}ed",
            comments=comments,
        )
        return Response(LeaveApplicationSerializer(app).data)


class LeaveAdminListView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.manage")]
    serializer_class = LeaveApplicationSerializer
    queryset = LeaveApplication.objects.all().order_by("-created_at")
