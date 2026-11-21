"""DRF serializers for FTS API views."""
from rest_framework import serializers

from modules.fts.models.attachments import FileAttachment
from modules.fts.models.audit import FileAuditLog
from modules.fts.models.comments import FileComment
from modules.fts.models.files import File
from modules.fts.models.movements import FileMovement


class FileAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAttachment
        fields = [
            "id",
            "file_id",
            "movement_id",
            "uploader_user_id",
            "uploader_username",
            "file_name",
            "file_url",
            "file_size",
            "mime_type",
            "created_at",
        ]


class FileCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileComment
        fields = [
            "id",
            "file_id",
            "movement_id",
            "author_user_id",
            "author_username",
            "author_role",
            "comment_text",
            "created_at",
        ]


class FileMovementSerializer(serializers.ModelSerializer):
    comments = FileCommentSerializer(many=True, read_only=True)
    attachments = FileAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = FileMovement
        fields = [
            "id",
            "file_id",
            "sequence",
            "movement_type",
            "from_user_id",
            "from_username",
            "from_role",
            "to_user_id",
            "to_username",
            "to_role",
            "comments",
            "attachments",
            "created_at",
        ]


class FileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = [
            "id",
            "reference_number",
            "subject",
            "status",
            "owner_user_id",
            "owner_username",
            "owner_role",
            "current_holder_user_id",
            "current_holder_username",
            "current_holder_role",
            "created_at",
            "updated_at",
            "archived_at",
        ]


class FileDetailSerializer(serializers.ModelSerializer):
    comments = FileCommentSerializer(many=True, read_only=True)
    attachments = FileAttachmentSerializer(many=True, read_only=True)
    movements = FileMovementSerializer(many=True, read_only=True)

    class Meta:
        model = File
        fields = [
            "id",
            "reference_number",
            "subject",
            "description",
            "status",
            "owner_user_id",
            "owner_username",
            "owner_role",
            "current_holder_user_id",
            "current_holder_username",
            "current_holder_role",
            "comments",
            "attachments",
            "movements",
            "created_at",
            "updated_at",
            "archived_at",
        ]


class CreateFileRequestSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    comment = serializers.CharField()
    is_draft = serializers.BooleanField(required=False, default=False)
    recipient_user_id = serializers.IntegerField(required=False, allow_null=True)
    recipient_username = serializers.CharField(required=False, allow_blank=True, default="")
    recipient_role = serializers.CharField(required=False, allow_blank=True, default="")
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class UpdateDraftRequestSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    comment = serializers.CharField(required=False, allow_blank=True)
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class ForwardFileRequestSerializer(serializers.Serializer):
    to_user_id = serializers.IntegerField()
    to_username = serializers.CharField(max_length=150)
    to_role = serializers.CharField(max_length=100)
    comment = serializers.CharField()
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class ReturnFileRequestSerializer(serializers.Serializer):
    comment = serializers.CharField()
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class FileAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAuditLog
        fields = [
            "id",
            "file_id",
            "action",
            "actor_user_id",
            "actor_username",
            "actor_role",
            "details",
            "timestamp",
        ]


class UsageMetricsSerializer(serializers.Serializer):
    total_files = serializers.IntegerField()
    draft_files = serializers.IntegerField()
    circulated_files = serializers.IntegerField()
    archived_files = serializers.IntegerField()
    discarded_drafts = serializers.IntegerField()
    total_movements = serializers.IntegerField()
