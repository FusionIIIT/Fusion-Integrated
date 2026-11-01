"""Serializers for File Tracking System (FTS) API endpoints."""
from rest_framework import serializers

from modules.filetracking.models import (
    FileAttachment,
    FileAuditLog,
    FileComment,
    FileMovement,
    TrackedFile,
)


class FileAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAttachment
        fields = [
            "id",
            "uploaded_by_user_id",
            "file_name",
            "file_path",
            "file_size",
            "mime_type",
            "created_at",
        ]


class FileCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileComment
        fields = [
            "id",
            "author_user_id",
            "author_role",
            "comment_text",
            "created_at",
        ]


class FileMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileMovement
        fields = [
            "id",
            "movement_type",
            "sender_user_id",
            "sender_role",
            "receiver_user_id",
            "receiver_role",
            "comment",
            "created_at",
        ]


class TrackedFileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackedFile
        fields = [
            "id",
            "file_code",
            "subject",
            "description",
            "status",
            "creator_user_id",
            "creator_role",
            "owner_user_id",
            "current_holder_user_id",
            "current_holder_role",
            "source_module",
            "external_reference",
            "created_at",
            "updated_at",
            "archived_at",
        ]


class TrackedFileDetailSerializer(serializers.ModelSerializer):
    comments = FileCommentSerializer(many=True, read_only=True)
    attachments = FileAttachmentSerializer(many=True, read_only=True)
    movements = FileMovementSerializer(many=True, read_only=True)

    class Meta:
        model = TrackedFile
        fields = [
            "id",
            "file_code",
            "subject",
            "description",
            "status",
            "creator_user_id",
            "creator_role",
            "owner_user_id",
            "current_holder_user_id",
            "current_holder_role",
            "source_module",
            "external_reference",
            "created_at",
            "updated_at",
            "archived_at",
            "comments",
            "attachments",
            "movements",
        ]


class CreateDraftSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    initial_comment = serializers.CharField(required=True)
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class EditDraftSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    comment = serializers.CharField(required=False, allow_blank=True)
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class ForwardFileSerializer(serializers.Serializer):
    receiver_user_id = serializers.IntegerField(required=True)
    receiver_role = serializers.CharField(max_length=64, required=True)
    comment = serializers.CharField(required=True)
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class ReturnFileSerializer(serializers.Serializer):
    comment = serializers.CharField(required=True)
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
            "actor_role",
            "details",
            "created_at",
        ]

