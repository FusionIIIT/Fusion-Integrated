"""DRF serializers for File Tracking System."""

from rest_framework import serializers

from modules.filetracking.models import FileAttachment, FileAuditLog, FileMovement, TrackedFile


class FileAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAttachment
        fields = [
            "id",
            "file_id",
            "movement_id",
            "uploaded_by_user_id",
            "uploader_designation",
            "file_name",
            "file_path",
            "file_size",
            "mime_type",
            "created_at",
        ]
        read_only_fields = fields


class FileMovementSerializer(serializers.ModelSerializer):
    attachments = FileAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = FileMovement
        fields = [
            "id",
            "sequence_number",
            "action",
            "sender_user_id",
            "sender_designation",
            "receiver_user_id",
            "receiver_designation",
            "comment",
            "created_at",
            "attachments",
        ]
        read_only_fields = fields


class TrackedFileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackedFile
        fields = [
            "id",
            "file_number",
            "subject",
            "status",
            "created_by_user_id",
            "creator_designation",
            "current_holder_user_id",
            "current_holder_designation",
            "is_archived",
            "archived_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TrackedFileDetailSerializer(serializers.ModelSerializer):
    movements = FileMovementSerializer(many=True, read_only=True)
    attachments = FileAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = TrackedFile
        fields = [
            "id",
            "file_number",
            "subject",
            "description",
            "status",
            "created_by_user_id",
            "creator_designation",
            "current_holder_user_id",
            "current_holder_designation",
            "is_archived",
            "archived_at",
            "created_at",
            "updated_at",
            "movements",
            "attachments",
        ]
        read_only_fields = fields


class AttachmentInputSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=255)
    file_path = serializers.CharField(max_length=512, required=False, default="")
    file_size = serializers.IntegerField(min_value=1)
    mime_type = serializers.CharField(max_length=128, default="application/pdf")


class CreateFileRequestSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255)
    initial_comment = serializers.CharField()
    is_draft = serializers.BooleanField(default=False)
    recipient_user_id = serializers.IntegerField(required=False, allow_null=True)
    recipient_designation = serializers.CharField(
        max_length=128, required=False, allow_blank=True, default=""
    )
    attachments = serializers.ListField(
        child=AttachmentInputSerializer(), required=False, default=list
    )


class UpdateDraftRequestSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False)
    attachments = serializers.ListField(
        child=AttachmentInputSerializer(), required=False, default=list
    )


class ForwardFileRequestSerializer(serializers.Serializer):
    recipient_user_id = serializers.IntegerField()
    recipient_designation = serializers.CharField(
        max_length=128, required=False, allow_blank=True, default=""
    )
    comment = serializers.CharField()
    attachments = serializers.ListField(
        child=AttachmentInputSerializer(), required=False, default=list
    )


class ReturnFileRequestSerializer(serializers.Serializer):
    comment = serializers.CharField()
    attachments = serializers.ListField(
        child=AttachmentInputSerializer(), required=False, default=list
    )


class ArchiveFileRequestSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class FileAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAuditLog
        fields = [
            "id",
            "file_id",
            "action",
            "actor_user_id",
            "actor_designation",
            "payload",
            "ip_address",
            "created_at",
        ]
        read_only_fields = fields


class IntegrationInitiateRequestSerializer(serializers.Serializer):
    initiator_user_id = serializers.IntegerField()
    initiator_designation = serializers.CharField(max_length=128)
    subject = serializers.CharField(max_length=255)
    initial_comment = serializers.CharField()
    recipient_user_id = serializers.IntegerField()
    recipient_designation = serializers.CharField(
        max_length=128, required=False, allow_blank=True, default=""
    )
    external_reference = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )


class IntegrationInitiateResponseSerializer(serializers.Serializer):
    file_id = serializers.IntegerField()
    file_number = serializers.CharField()
    status = serializers.CharField()
    current_holder_user_id = serializers.IntegerField(allow_null=True)
