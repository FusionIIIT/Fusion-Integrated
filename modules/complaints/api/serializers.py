"""DRF Serializers for Complaint Management System."""
from __future__ import annotations

from rest_framework import serializers

from modules.complaints.models import (
    CMSRoleAssignment,
    ClosureVerification,
    Complaint,
    ComplaintAnnouncement,
    ComplaintAssignment,
    ComplaintAttachment,
    ComplaintFeedback,
    ProgressUpdate,
    ReopeningRequest,
    StatusHistoryEntry,
)


class ComplaintAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintAttachment
        fields = ["id", "file_name", "file_size", "content_type", "file_path", "created_at"]
        read_only_fields = fields


class ProgressUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressUpdate
        fields = ["id", "user_id", "notes", "created_at"]
        read_only_fields = fields


class StatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusHistoryEntry
        fields = ["id", "from_status", "to_status", "changed_by_user_id", "reason", "created_at"]
        read_only_fields = fields


class ClosureVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClosureVerification
        fields = ["id", "verified_by_user_id", "verifier_role", "is_satisfied", "comments", "verified_at"]
        read_only_fields = fields


class ReopeningRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReopeningRequest
        fields = [
            "id", "complaint_id", "requested_by_user_id", "reason",
            "status", "reviewed_by_user_id", "decision_notes", "requested_at", "reviewed_at"
        ]
        read_only_fields = fields


class ComplaintFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintFeedback
        fields = ["id", "complaint_id", "complainant_user_id", "rating", "comments", "created_at"]
        read_only_fields = fields


class ComplaintListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = [
            "id", "complaint_id", "complainant_user_id", "category",
            "description", "priority", "status", "assigned_handler_id",
            "is_escalated", "created_at", "sla_deadline"
        ]
        read_only_fields = fields


class ComplaintDetailSerializer(serializers.ModelSerializer):
    attachments = ComplaintAttachmentSerializer(many=True, read_only=True)
    progress_updates = ProgressUpdateSerializer(many=True, read_only=True)
    status_history = StatusHistorySerializer(many=True, read_only=True)
    closure_verification = ClosureVerificationSerializer(read_only=True)
    feedback = ComplaintFeedbackSerializer(read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id", "complaint_id", "complainant_user_id", "category", "description",
            "priority", "status", "assigned_handler_id", "is_escalated",
            "escalation_type", "escalated_at", "escalation_reason",
            "resolution_details", "resolved_at", "rejection_reason", "rejected_at",
            "closed_at", "closed_by_user_id", "sla_deadline", "sla_reminder_sent",
            "created_at", "updated_at", "attachments", "progress_updates",
            "status_history", "closure_verification", "feedback"
        ]
        read_only_fields = fields


class ComplaintCreateSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=64)
    description = serializers.CharField(max_length=4000)
    priority = serializers.CharField(max_length=16, default="low", required=False)
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class HandlingSetupSerializer(serializers.Serializer):
    handler_user_id = serializers.IntegerField()
    category = serializers.CharField(max_length=64, required=False, allow_blank=True)
    priority = serializers.CharField(max_length=16, required=False, allow_blank=True)


class ProgressUpdateCreateSerializer(serializers.Serializer):
    notes = serializers.CharField(max_length=2000)


class ResolveComplaintSerializer(serializers.Serializer):
    resolution_details = serializers.CharField(max_length=2000)


class RejectComplaintSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(max_length=2000)


class VerifyClosureSerializer(serializers.Serializer):
    is_satisfied = serializers.BooleanField(default=True)
    comments = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    verifier_role = serializers.ChoiceField(choices=["complainant", "supervisor"], default="complainant")


class ReopeningRequestCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)


class ReopeningReviewSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    decision_notes = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")


class FeedbackCreateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comments = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class EscalateComplaintSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintAnnouncement
        fields = [
            "id", "title", "content", "author_user_id", "target_audience",
            "published_at", "expires_at"
        ]
        read_only_fields = ["id", "author_user_id", "published_at"]


class RoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CMSRoleAssignment
        fields = [
            "id", "user_id", "role_name", "assigned_by_user_id", "valid_from",
            "valid_to", "is_active", "created_at"
        ]
        read_only_fields = ["id", "assigned_by_user_id", "is_active", "created_at"]

