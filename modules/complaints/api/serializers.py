"""Explicit API allow-lists for CMS resources."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.complaints.models import (
    Announcement,
    Complaint,
    ComplaintAttachment,
    ComplaintHistory,
    Feedback,
    ReopeningRequest,
)


class ComplaintCreateSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=100, trim_whitespace=True)
    description = serializers.CharField(max_length=10000, trim_whitespace=True)
    attachments = serializers.ListField(
        child=serializers.FileField(), required=False, allow_empty=True, max_length=5
    )


class ComplaintHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintHistory
        fields = ("event", "from_status", "to_status", "actor_kind", "details", "occurred_at")
        read_only_fields = fields


class ComplaintSerializer(serializers.ModelSerializer):
    history = ComplaintHistorySerializer(many=True, read_only=True)
    feedback_submitted = serializers.SerializerMethodField()
    reopening_status = serializers.SerializerMethodField()

    class Meta:
        model = Complaint
        fields = (
            "reference",
            "category",
            "description",
            "status",
            "priority",
            "assigned_to_user_id",
            "sla_due_at",
            "verification_required",
            "submitted_at",
            "resolved_at",
            "closed_at",
            "resolution_details",
            "rejection_reason",
            "history",
            "feedback_submitted",
            "reopening_status",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.BooleanField)
    def get_feedback_submitted(self, obj):
        prefetched = getattr(obj, "_prefetched_objects_cache", {}).get("feedback")
        if prefetched is not None:
            return any(row.submitted_by_user_id == obj.complainant_user_id for row in prefetched)
        return obj.feedback.filter(submitted_by_user_id=obj.complainant_user_id).exists()

    @extend_schema_field(
        serializers.ChoiceField(choices=("pending", "approved", "denied"), allow_null=True)
    )
    def get_reopening_status(self, obj):
        prefetched = getattr(obj, "_prefetched_objects_cache", {}).get("reopening_requests")
        rows = prefetched if prefetched is not None else obj.reopening_requests.all()
        latest = max(rows, key=lambda row: row.created_at, default=None)
        return latest.status if latest else None


class FeedbackCreateSerializer(serializers.Serializer):
    message = serializers.CharField(trim_whitespace=True)


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintAttachment
        fields = ("id", "original_name", "content_type", "byte_size", "uploaded_at")
        read_only_fields = fields


class AttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ("id", "complaint_id", "message", "created_at")
        read_only_fields = fields


class ReopeningCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(trim_whitespace=True)


class ReopeningSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReopeningRequest
        fields = (
            "id",
            "complaint_id",
            "reason",
            "status",
            "decision_reason",
            "created_at",
            "decided_at",
        )
        read_only_fields = fields


class AnnouncementCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, trim_whitespace=True)
    body = serializers.CharField(trim_whitespace=True)


class CMSAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ("id", "title", "body", "published_at")
        read_only_fields = fields


class ReopeningDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approved", "denied"))
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class HandlerAssignmentSerializer(serializers.Serializer):
    assignee_user_id = serializers.IntegerField(min_value=1)
    category = serializers.CharField(max_length=100, trim_whitespace=True)
    priority = serializers.ChoiceField(choices=("low", "medium", "high"), default="medium")


class HandlerOptionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    display_name = serializers.CharField()
    kind = serializers.CharField()
    department = serializers.CharField(allow_blank=True)


class ProgressSerializer(serializers.Serializer):
    details = serializers.CharField(trim_whitespace=True)


class ResolutionSerializer(serializers.Serializer):
    details = serializers.CharField(trim_whitespace=True)


class RejectionSerializer(serializers.Serializer):
    reason = serializers.CharField(trim_whitespace=True)


class EscalationSerializer(serializers.Serializer):
    reference = serializers.UUIDField()
    source = serializers.CharField()
    reason = serializers.CharField(allow_blank=True)
    escalated_at = serializers.DateTimeField()


class FeedbackReadSerializer(serializers.ModelSerializer):
    complaint_reference = serializers.UUIDField(source="complaint.reference", read_only=True)

    class Meta:
        model = Feedback
        fields = ("id", "complaint_reference", "message", "created_at")
        read_only_fields = fields


class ComplaintPageSerializer(serializers.Serializer):
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ComplaintSerializer(many=True)


class HistoryPageSerializer(serializers.Serializer):
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ComplaintHistorySerializer(many=True)


class FeedbackPageSerializer(serializers.Serializer):
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = FeedbackReadSerializer(many=True)


class ReopeningPageSerializer(serializers.Serializer):
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ReopeningSerializer(many=True)


class AnnouncementPageSerializer(serializers.Serializer):
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = CMSAnnouncementSerializer(many=True)


class AttachmentPageSerializer(serializers.Serializer):
    results = AttachmentSerializer(many=True)


class StatusCountSerializer(serializers.Serializer):
    status = serializers.CharField()
    total = serializers.IntegerField()


class EscalationCountSerializer(serializers.Serializer):
    source = serializers.CharField()
    total = serializers.IntegerField()


class EscalationSummarySerializer(serializers.Serializer):
    results = EscalationCountSerializer(many=True)


class ComplaintReportSerializer(serializers.Serializer):
    complaints_by_status = StatusCountSerializer(many=True)
