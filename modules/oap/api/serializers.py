from rest_framework import serializers

from modules.oap.models import (
    AssistantshipClaim,
    BonafideRequest,
    LeaveApplication,
    Notification,
    SeminarRequest,
    SeminarSchedule,
    SupervisorVerification,
    TAAssignment,
    ThesisSupervisorAssignment,
)


class LeaveSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "status",
            "reason",
            "from_date",
            "to_date",
            "supporting_document_link",
            "decided_at",
            "created_at",
        ]
        read_only_fields = fields


class LeaveCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)
    from_date = serializers.DateField()
    to_date = serializers.DateField()
    supporting_document_link = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )


class OutcomeSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["approve", "reject"])


class BonafideSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = BonafideRequest
        fields = ["id", "status", "purpose", "verified_at", "decided_at", "created_at"]
        read_only_fields = fields


class BonafideCreateSerializer(serializers.Serializer):
    purpose = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class NoDuesResultSerializer(serializers.Serializer):
    result = serializers.ChoiceField(choices=["clear", "outstanding"])


class VerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupervisorVerification
        fields = ["role", "verified_at"]
        read_only_fields = fields


class ClaimSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    verifications = VerificationSerializer(many=True, read_only=True)

    class Meta:
        model = AssistantshipClaim
        fields = [
            "id",
            "status",
            "thesis_supervisor_user_id",
            "ta_supervisor_user_id",
            "verifications",
            "department_forwarded_at",
            "hod_decided_at",
            "stipend_processed_at",
            "created_at",
        ]
        read_only_fields = fields


class VerifyClaimSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["thesis", "ta"])


class ThesisAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThesisSupervisorAssignment
        fields = ["id", "student_user_id", "supervisor_user_id", "assigned_at", "superseded_at"]
        read_only_fields = ["id", "assigned_at", "superseded_at"]


class ThesisAssignmentInputSerializer(serializers.Serializer):
    student_user_id = serializers.IntegerField(min_value=1)
    supervisor_user_id = serializers.IntegerField(min_value=1)


class TAAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TAAssignment
        fields = ["id", "student_user_id", "course_code", "supervisor_user_id", "assigned_at"]
        read_only_fields = fields


class TAAssignmentInputSerializer(serializers.Serializer):
    student_user_id = serializers.IntegerField(min_value=1)
    course_code = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    supervisor_user_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, default=None
    )


class SeminarRequestSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = SeminarRequest
        fields = ["id", "status", "created_at"]
        read_only_fields = fields


class SeminarScheduleInputSerializer(serializers.Serializer):
    scheduled_for = serializers.DateTimeField()
    venue = serializers.CharField(max_length=200)


class SeminarScheduleSerializer(serializers.ModelSerializer):
    request_id = serializers.IntegerField(source="request.id", read_only=True)

    class Meta:
        model = SeminarSchedule
        fields = ["id", "request_id", "scheduled_for", "venue", "scheduled_at"]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "subject", "body", "status", "created_at"]
        read_only_fields = fields
