"""Serializers for the Complaint Management System API."""
from rest_framework import serializers

from modules.complaints.models import (
    CmsRoleAssignment,
    Complaint,
    ComplaintAnnouncement,
    ComplaintAttachment,
    ComplaintCategory,
    ComplaintFeedback,
    ComplaintTransition,
)


class ComplaintCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintCategory
        fields = ["id", "name", "description", "default_sla_hours", "is_active"]


class ComplaintAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintAttachment
        fields = ["id", "file", "file_name", "file_size", "uploaded_by_user_id", "created_at"]
        read_only_fields = fields


class ComplaintTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintTransition
        fields = [
            "id",
            "from_status",
            "to_status",
            "actor_user_id",
            "actor_role",
            "remarks",
            "created_at",
        ]
        read_only_fields = fields


class ComplaintFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintFeedback
        fields = ["id", "rating", "comments", "created_at"]
        read_only_fields = ["id", "created_at"]


class ComplaintDetailSerializer(serializers.ModelSerializer):
    category = ComplaintCategorySerializer(read_only=True)
    attachments = ComplaintAttachmentSerializer(many=True, read_only=True)
    transitions = ComplaintTransitionSerializer(many=True, read_only=True)
    feedback = ComplaintFeedbackSerializer(read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "complaint_id",
            "complainant_user_id",
            "category",
            "location",
            "description",
            "status",
            "priority",
            "assigned_worker_id",
            "assigned_worker_name",
            "resolution_details",
            "rejection_reason",
            "verification_required",
            "is_escalated",
            "escalation_type",
            "escalated_at",
            "escalation_remarks",
            "resolved_at",
            "closed_at",
            "rejected_at",
            "reopening_status",
            "reopening_reason",
            "reopening_review_remarks",
            "sla_deadline",
            "sla_reminder_sent",
            "attachments",
            "transitions",
            "feedback",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ComplaintListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "complaint_id",
            "complainant_user_id",
            "category_id",
            "category_name",
            "location",
            "description",
            "status",
            "priority",
            "assigned_worker_name",
            "is_escalated",
            "verification_required",
            "reopening_status",
            "sla_deadline",
            "created_at",
            "resolved_at",
            "closed_at",
        ]


class SubmitComplaintSerializer(serializers.Serializer):
    category_id = serializers.IntegerField(required=True)
    location = serializers.CharField(max_length=160, required=True)
    description = serializers.CharField(max_length=4000, required=True)
    priority = serializers.ChoiceField(choices=["low", "medium", "high"], default="medium")
    verification_required = serializers.ChoiceField(
        choices=["none", "user", "supervisor"], default="none"
    )


class AssignComplaintSerializer(serializers.Serializer):
    worker_id = serializers.IntegerField(required=False, allow_null=True)
    worker_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=["low", "medium", "high"], required=False)
    category_id = serializers.IntegerField(required=False)
    remarks = serializers.CharField(required=False, allow_blank=True)


class ProgressUpdateSerializer(serializers.Serializer):
    progress_notes = serializers.CharField(required=True)


class ResolveComplaintSerializer(serializers.Serializer):
    resolution_details = serializers.CharField(required=True)


class RejectComplaintSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(required=True)


class VerifyCloseSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True)


class ReopeningRequestSerializer(serializers.Serializer):
    reopening_reason = serializers.CharField(required=True)


class ReopeningReviewSerializer(serializers.Serializer):
    approved = serializers.BooleanField(required=True)
    review_remarks = serializers.CharField(required=False, allow_blank=True)


class ManualEscalateSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=True)


class SubmitFeedbackSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5, required=True)
    comments = serializers.CharField(required=False, allow_blank=True)


class ComplaintAnnouncementSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = ComplaintAnnouncement
        fields = [
            "id",
            "title",
            "content",
            "category_id",
            "category_name",
            "author_user_id",
            "author_name",
            "is_active",
            "pinned",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CmsRoleAssignmentSerializer(serializers.ModelSerializer):
    role_type_label = serializers.CharField(source="get_role_type_display", read_only=True)

    class Meta:
        model = CmsRoleAssignment
        fields = [
            "id",
            "role_type",
            "role_type_label",
            "user_id",
            "assigned_by_user_id",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "assigned_by_user_id", "created_at"]


class SlaCheckResultSerializer(serializers.Serializer):
    escalated_count = serializers.IntegerField()
    reminders_sent = serializers.IntegerField()
