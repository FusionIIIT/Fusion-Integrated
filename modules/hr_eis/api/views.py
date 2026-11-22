from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from modules.hr_eis.models import (
    EmployeeProfile, LeaveBalance, LeaveRequest,
    AppraisalCycle, AppraisalRecord,
    LtcClaim, CpdaClaim,
    AuditLog, NotificationRecord, WorkflowSetting
)
from modules.hr_eis.api.serializers import (
    EmployeeProfileSerializer, LeaveBalanceSerializer, LeaveRequestSerializer,
    AppraisalCycleSerializer, AppraisalRecordSerializer,
    LtcClaimSerializer, CpdaClaimSerializer,
    AuditLogSerializer, NotificationSerializer, WorkflowSettingSerializer
)
from modules.hr_eis.services import LeaveService, ClaimService, AppraisalService
from modules.hr_eis.domain.rules import DomainValidationError
from modules.hr_eis.domain.state_machine import InvalidStateTransitionError

class EmployeeProfileViewSet(viewsets.ModelViewSet):
    queryset = EmployeeProfile.objects.all()
    serializer_class = EmployeeProfileSerializer

    @action(detail=False, methods=["get"])
    def me(self, request):
        user_id = getattr(request.user, "username", "EMP001")
        profile = EmployeeProfile.objects.filter(user_id=user_id).first()
        if not profile:
            profile = EmployeeProfile.objects.first()
        if not profile:
            return Response({"detail": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(EmployeeProfileSerializer(profile).data)

class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer

class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        req = self.get_object()
        action_name = request.data.get("action")
        role = request.data.get("role", "HOD")
        actor_id = request.data.get("actor_id", "EMP_APPROVER")
        remarks = request.data.get("remarks", "")
        try:
            decided = LeaveService.decide_leave(req, action_name, role, actor_id, remarks)
            return Response(LeaveRequestSerializer(decided).data)
        except (DomainValidationError, InvalidStateTransitionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AppraisalRecordViewSet(viewsets.ModelViewSet):
    queryset = AppraisalRecord.objects.all()
    serializer_class = AppraisalRecordSerializer

class LtcClaimViewSet(viewsets.ModelViewSet):
    queryset = LtcClaim.objects.all()
    serializer_class = LtcClaimSerializer

    @action(detail=True, methods=["post"])
    def settle(self, request, pk=None):
        claim = self.get_object()
        ref = request.data.get("disbursement_ref", "")
        role = request.data.get("role", "Accountant")
        actor_id = request.data.get("actor_id", "FIN_ACC")
        try:
            settled = ClaimService.settle_ltc(claim, ref, role, actor_id)
            return Response(LtcClaimSerializer(settled).data)
        except (DomainValidationError, InvalidStateTransitionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CpdaClaimViewSet(viewsets.ModelViewSet):
    queryset = CpdaClaim.objects.all()
    serializer_class = CpdaClaimSerializer

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().order_by("-timestamp")
    serializer_class = AuditLogSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = NotificationRecord.objects.all().order_by("-created_at")
    serializer_class = NotificationSerializer

class WorkflowSettingViewSet(viewsets.ModelViewSet):
    queryset = WorkflowSetting.objects.all()
    serializer_class = WorkflowSettingSerializer
