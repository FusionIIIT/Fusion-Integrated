"""DRF serializers for FTS."""
from rest_framework import serializers

from modules.fts.models import (
    FileAttachment,
    FileComment,
    FileMovement,
    FTSAuditLog,
    FTSFile,
)


class AttachmentInputSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=255)
    file_path = serializers.CharField(max_length=512, default="")
    file_size = serializers.IntegerField(min_value=0, default=0)
    mime_type = serializers.CharField(max_length=128, default="application/octet-stream")


class FileAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAttachment
        fields = (
            "id",
            "uploader_id",
            "file_name",
            "file_path",
            "file_size",
            "mime_type",
            "created_at",
        )
        read_only_fields = fields


class FileCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileComment
        fields = (
            "id",
            "author_id",
            "author_designation",
            "comment_text",
            "created_at",
        )
        read_only_fields = fields


class FileMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileMovement
        fields = (
            "id",
            "sequence_number",
            "sender_id",
            "sender_designation",
            "receiver_id",
            "receiver_designation",
            "action",
            "remarks",
            "created_at",
        )
        read_only_fields = fields


class FTSFileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = FTSFile
        fields = (
            "id",
            "file_id",
            "subject",
            "description",
            "status",
            "creator_id",
            "creator_designation",
            "owner_id",
            "current_holder_id",
            "current_holder_designation",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class FTSFileDetailSerializer(serializers.ModelSerializer):
    movements = FileMovementSerializer(many=True, read_only=True)
    comments = FileCommentSerializer(many=True, read_only=True)
    attachments = FileAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = FTSFile
        fields = (
            "id",
            "file_id",
            "subject",
            "description",
            "status",
            "creator_id",
            "creator_designation",
            "owner_id",
            "current_holder_id",
            "current_holder_designation",
            "created_at",
            "updated_at",
            "movements",
            "comments",
            "attachments",
        )
        read_only_fields = fields


class CreateFileSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255)
    description = serializers.CharField(allow_blank=True, required=False, default="")
    initial_comment = serializers.CharField()
    is_draft = serializers.BooleanField(default=False)
    receiver_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    receiver_designation = serializers.CharField(allow_blank=True, required=False, default="")
    attachments = AttachmentInputSerializer(many=True, required=False, default=list)


class EditDraftSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(allow_blank=True, required=False)
    comment = serializers.CharField(required=False)
    attachments = AttachmentInputSerializer(many=True, required=False, default=list)


class ForwardFileSerializer(serializers.Serializer):
    receiver_id = serializers.IntegerField()
    receiver_designation = serializers.CharField(allow_blank=True, required=False, default="")
    remarks = serializers.CharField()
    attachments = AttachmentInputSerializer(many=True, required=False, default=list)


class ReturnFileSerializer(serializers.Serializer):
    remarks = serializers.CharField()
    attachments = AttachmentInputSerializer(many=True, required=False, default=list)


class ArchiveFileSerializer(serializers.Serializer):
    remarks = serializers.CharField(allow_blank=True, required=False, default="")


class FTSAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FTSAuditLog
        fields = (
            "id",
            "actor_id",
            "actor_role",
            "action_type",
            "details",
            "timestamp",
        )
        read_only_fields = fields
