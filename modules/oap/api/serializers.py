from rest_framework import serializers

from modules.oap.models import (
    AssistantshipClaim,
    BonafideRequest,
    ClaimSupervisorVerification,
    GraduateSeminar,
    LeaveAttachment,
    NoDuesAuthorityClearance,
    NoDuesRequest,
    OAPNotification,
    StudentLeaveApplication,
    TeachingAssistantAssignment,
    ThesisSupervisorAssignment,
)


class LeaveAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAttachment
        fields = ["id", "file_name", "file_url", "created_at"]


class StudentLeaveApplicationSerializer(serializers.ModelSerializer):
    attachments = LeaveAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = StudentLeaveApplication
        fields = [
            "id",
            "user_id",
            "department",
            "programme",
            "leave_type",
            "start_date",
            "end_date",
            "reason",
            "status",
            "decision_by_user_id",
            "decision_remarks",
            "decided_at",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class StudentLeaveApplicationCreateSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=100)
    programme = serializers.CharField(max_length=20, default="ug")
    leave_type = serializers.CharField(max_length=50, default="Casual Leave")
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class LeaveDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class BonafideRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonafideRequest
        fields = [
            "id",
            "user_id",
            "purpose",
            "details",
            "status",
            "decision_by_user_id",
            "decision_remarks",
            "decided_at",
            "certificate_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class BonafideRequestCreateSerializer(serializers.Serializer):
    purpose = serializers.CharField(max_length=255)
    details = serializers.CharField(required=False, allow_blank=True, default="")


class BonafideDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class NoDuesAuthorityClearanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoDuesAuthorityClearance
        fields = [
            "id",
            "domain",
            "status",
            "verified_by_user_id",
            "dues_amount",
            "remarks",
            "verified_at",
            "updated_at",
        ]
        read_only_fields = fields


class NoDuesRequestSerializer(serializers.ModelSerializer):
    clearances = NoDuesAuthorityClearanceSerializer(many=True, read_only=True)

    class Meta:
        model = NoDuesRequest
        fields = [
            "id",
            "user_id",
            "department",
            "programme",
            "status",
            "finalized_by_user_id",
            "finalized_at",
            "certificate_number",
            "clearances",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class NoDuesInitiateSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=100)
    programme = serializers.CharField(max_length=20, default="ug")


class NoDuesClearanceVerifySerializer(serializers.Serializer):
    domain = serializers.CharField(max_length=50)
    status = serializers.ChoiceField(choices=["clear", "dues_outstanding"])
    dues_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00, required=False)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ThesisSupervisorAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThesisSupervisorAssignment
        fields = [
            "id",
            "student_user_id",
            "supervisor_user_id",
            "department",
            "assigned_by_user_id",
            "is_active",
            "start_date",
            "end_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ThesisSupervisorAssignmentCreateSerializer(serializers.Serializer):
    student_user_id = serializers.IntegerField()
    supervisor_user_id = serializers.IntegerField()
    department = serializers.CharField(max_length=100)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)


class TeachingAssistantAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingAssistantAssignment
        fields = [
            "id",
            "student_user_id",
            "ta_supervisor_user_id",
            "course_code",
            "department",
            "semester",
            "year",
            "assigned_by_user_id",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TeachingAssistantAssignmentCreateSerializer(serializers.Serializer):
    student_user_id = serializers.IntegerField()
    ta_supervisor_user_id = serializers.IntegerField(required=False, allow_null=True)
    course_code = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    department = serializers.CharField(max_length=100)
    semester = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    year = serializers.IntegerField(required=False, allow_null=True)


class ClaimSupervisorVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClaimSupervisorVerification
        fields = [
            "id",
            "role",
            "supervisor_user_id",
            "remarks",
            "verified_at",
        ]
        read_only_fields = fields


class AssistantshipClaimSerializer(serializers.ModelSerializer):
    supervisor_verifications = ClaimSupervisorVerificationSerializer(many=True, read_only=True)

    class Meta:
        model = AssistantshipClaim
        fields = [
            "id",
            "user_id",
            "month",
            "year",
            "department",
            "stipend_amount",
            "work_summary",
            "hours_worked",
            "status",
            "thesis_supervisor_user_id",
            "ta_supervisor_user_id",
            "thesis_verified",
            "ta_verified",
            "thesis_verified_at",
            "ta_verified_at",
            "dept_reviewed_by_user_id",
            "dept_reviewed_at",
            "hod_decided_by_user_id",
            "hod_decision_remarks",
            "hod_decided_at",
            "disbursed_by_user_id",
            "disbursed_at",
            "disbursement_reference",
            "supervisor_verifications",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AssistantshipClaimCreateSerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2000)
    department = serializers.CharField(max_length=100)
    stipend_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    work_summary = serializers.CharField()
    hours_worked = serializers.DecimalField(max_digits=6, decimal_places=2, default=0.00, required=False)
    thesis_supervisor_user_id = serializers.IntegerField(required=False, allow_null=True)
    ta_supervisor_user_id = serializers.IntegerField(required=False, allow_null=True)


class AssistantshipSupervisorVerifySerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["thesis_supervisor", "ta_supervisor"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class AssistantshipHodDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class AssistantshipDisburseSerializer(serializers.Serializer):
    disbursement_reference = serializers.CharField(required=False, allow_blank=True, default="")


class GraduateSeminarSerializer(serializers.ModelSerializer):
    class Meta:
        model = GraduateSeminar
        fields = [
            "id",
            "user_id",
            "title",
            "abstract",
            "preferred_dates",
            "status",
            "scheduled_date",
            "scheduled_time",
            "venue",
            "coordinator_user_id",
            "scheduled_by_user_id",
            "scheduled_at",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class GraduateSeminarRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    abstract = serializers.CharField()
    preferred_dates = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class GraduateSeminarScheduleSerializer(serializers.Serializer):
    scheduled_date = serializers.DateField()
    scheduled_time = serializers.CharField(max_length=50)
    venue = serializers.CharField(max_length=100)
    coordinator_user_id = serializers.IntegerField(required=False, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class OAPNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OAPNotification
        fields = [
            "id",
            "recipient_user_id",
            "title",
            "message",
            "channel",
            "related_entity_type",
            "related_entity_id",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields
