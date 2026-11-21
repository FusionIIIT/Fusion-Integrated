from rest_framework import serializers
from modules.fts.models import FTSFile, FileMovement, FileAttachment, FileAuditLog
from modules.directory.models import UserRef

class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRef
        fields = ['user_id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = fields

class FileAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAttachment
        fields = ['id', 'file', 'movement', 'uploader', 'file_name', 'file_url', 'file_size', 'created_at']
        read_only_fields = ['id', 'created_at']

class FileMovementSerializer(serializers.ModelSerializer):
    sender = UserSummarySerializer(read_only=True)
    receiver = UserSummarySerializer(read_only=True)
    attachments = FileAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = FileMovement
        fields = ['id', 'file', 'sender', 'sender_role', 'receiver', 'receiver_role', 'action', 'comments', 'attachments', 'created_at']

class FileAuditLogSerializer(serializers.ModelSerializer):
    actor = UserSummarySerializer(read_only=True)

    class Meta:
        model = FileAuditLog
        fields = ['id', 'file', 'actor', 'actor_role', 'action', 'details', 'created_at']

class FTSFileListSerializer(serializers.ModelSerializer):
    owner = UserSummarySerializer(read_only=True)
    current_holder = UserSummarySerializer(read_only=True)

    class Meta:
        model = FTSFile
        fields = ['id', 'file_number', 'subject', 'description', 'owner', 'creator_role', 'current_holder', 'current_holder_role', 'status', 'is_archived', 'archived_at', 'created_at', 'updated_at']

class FTSFileDetailSerializer(serializers.ModelSerializer):
    owner = UserSummarySerializer(read_only=True)
    current_holder = UserSummarySerializer(read_only=True)
    movements = FileMovementSerializer(many=True, read_only=True)
    attachments = FileAttachmentSerializer(many=True, read_only=True)
    audit_logs = FileAuditLogSerializer(many=True, read_only=True)

    class Meta:
        model = FTSFile
        fields = ['id', 'file_number', 'subject', 'description', 'owner', 'creator_role', 'current_holder', 'current_holder_role', 'status', 'is_archived', 'archived_at', 'movements', 'attachments', 'audit_logs', 'created_at', 'updated_at']

class CreateFileRequestSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    initial_comment = serializers.CharField(required=True)
    creator_role = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")

class ForwardFileRequestSerializer(serializers.Serializer):
    receiver_id = serializers.IntegerField(required=True)
    receiver_role = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    sender_role = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    comment = serializers.CharField(required=True)

class ReturnFileRequestSerializer(serializers.Serializer):
    sender_role = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    comment = serializers.CharField(required=True)

class ArchiveFileRequestSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    user_role = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")

class DraftEditRequestSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    user_role = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")