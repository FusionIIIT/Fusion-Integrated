from rest_framework import serializers
from modules.hr_eis.models import (
    EmployeeProfile, LeaveBalance, LeaveRequest,
    AppraisalCycle, AppraisalRecord,
    LtcClaim, CpdaClaim,
    AuditLog, NotificationRecord, WorkflowSetting
)

class EmployeeProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeProfile
        fields = "__all__"

class LeaveBalanceSerializer(serializers.ModelSerializer):
    available_days = serializers.ReadOnlyField()
    class Meta:
        model = LeaveBalance
        fields = "__all__"

class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = "__all__"

class AppraisalCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppraisalCycle
        fields = "__all__"

class AppraisalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppraisalRecord
        fields = "__all__"

class LtcClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = LtcClaim
        fields = "__all__"

class CpdaClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = CpdaClaim
        fields = "__all__"

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationRecord
        fields = "__all__"

class WorkflowSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowSetting
        fields = "__all__"
