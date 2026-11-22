from rest_framework import serializers

from modules.cms.models import (
    CmsRoleAssignment,
    Complaint,
    ComplaintAnnouncement,
    ComplaintAttachment,
    ComplaintFeedback,
    ComplaintHistory,
    ComplaintProgress,
    ReopeningRequest,
)


class ComplaintAttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ComplaintAttachment
        fields = ["id", "file_name", "content_type", "size_bytes", "created_at", "download_url"]

    def get_download_url(self, obj) -> str:
        return f"/api/v1/cms/attachments/{obj.pk}/download"


class ComplaintHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintHistory
        fields = ["from_status", "to_status", "actor_user_id", "actor_role", "note", "created_at"]


class ComplaintProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintProgress
        fields = ["id", "actor_user_id", "update_text", "created_at"]


class ReopeningRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReopeningRequest
        fields = [
            "id",
            "complaint",
            "requested_by_user_id",
            "request_reason",
            "decision",
            "decided_by_user_id",
            "decision_note",
            "created_at",
            "decided_at",
        ]


class ComplaintSerializer(serializers.ModelSerializer):
    attachments = ComplaintAttachmentSerializer(many=True, read_only=True)
    history = ComplaintHistorySerializer(many=True, read_only=True)
    progress_updates = ComplaintProgressSerializer(many=True, read_only=True)
    reopening_requests = ReopeningRequestSerializer(many=True, read_only=True)
    escalated = serializers.SerializerMethodField()

    class Meta:
        model = Complaint
        fields = [
            "id",
            "complaint_id",
            "complainant_user_id",
            "category",
            "description",
            "status",
            "priority",
            "assigned_handler_user_id",
            "assignment_note",
            "resolution_details",
            "rejection_reason",
            "closure_verifier",
            "closed_at",
            "reopened_at",
            "sla_due_at",
            "escalated",
            "escalated_at",
            "escalation_kind",
            "attachments",
            "history",
            "progress_updates",
            "reopening_requests",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_escalated(self, obj) -> bool:
        return bool(obj.escalated_at)


class ComplaintSubmissionSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=120, trim_whitespace=True)
    description = serializers.CharField(max_length=10000, trim_whitespace=True)
    attachments = serializers.ListField(
        child=serializers.FileField(), required=False, allow_empty=True
    )


class HandlingSetupSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=120)
    priority = serializers.ChoiceField(choices=["low", "medium", "high"])
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class TextActionSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=10000, trim_whitespace=True)


class OutcomeSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["resolved", "rejected"])
    details = serializers.CharField(max_length=10000, trim_whitespace=True)


class ReopeningDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "denied"])
    note = serializers.CharField(max_length=5000, required=False, allow_blank=True)


class CmsAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintAnnouncement
        fields = ["id", "title", "body", "published_by_user_id", "notify_users", "published_at"]
        read_only_fields = ["id", "published_by_user_id", "published_at"]


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintFeedback
        fields = ["id", "complaint", "submitted_by_user_id", "feedback_text", "created_at"]
        read_only_fields = ["id", "complaint", "submitted_by_user_id", "created_at"]


class RoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CmsRoleAssignment
        fields = [
            "id",
            "role",
            "user_id",
            "starts_at",
            "ends_at",
            "is_active",
            "created_at",
            "assigned_by_user_id",
        ]
        read_only_fields = ["id", "is_active", "created_at", "assigned_by_user_id"]
        # Reassignment is atomic in the service: the current appointment is
        # deactivated before the replacement is inserted. The conditional DB
        # constraint remains the final concurrency guard.
        validators = []


class CmsConfigSerializer(serializers.Serializer):
    attachment_max_bytes = serializers.IntegerField()
    attachment_max_count = serializers.IntegerField()
    attachment_allowed_extensions = serializers.ListField(child=serializers.CharField())


class CmsCountRowSerializer(serializers.Serializer):
    status = serializers.CharField(required=False)
    priority = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False)
    count = serializers.IntegerField()


class CmsReportSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    by_status = CmsCountRowSerializer(many=True)
    by_priority = CmsCountRowSerializer(many=True)
    by_category = CmsCountRowSerializer(many=True)
    escalated = serializers.IntegerField()
    unresolved = serializers.IntegerField()
    oldest_unresolved_at = serializers.DateTimeField(allow_null=True)
