"""Fusion Clean Architecture - File Tracking System (FTS) Serializers."""

from rest_framework import serializers

from modules.fts.models import FTSFile


class FTSFileSerializer(serializers.ModelSerializer):
    """Serializer for FTSFile model."""

    class Meta:
        model = FTSFile
        fields = [
            "id",
            "uin",
            "subject",
            "description",
            "priority",
            "category",
            "status",
            "creator_id",
            "creator_role",
            "current_holder_id",
            "current_holder_role",
            "is_draft",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "uin",
            "status",
            "creator_id",
            "current_holder_id",
            "is_draft",
            "created_at",
            "updated_at",
        ]


class CreateDraftSerializer(serializers.Serializer):
    """Input serializer for creating a new file draft."""

    subject = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default="", allow_blank=True)
    initial_comment = serializers.CharField()
    priority = serializers.ChoiceField(
        choices=["low", "medium", "high", "urgent"], default="medium"
    )
    category = serializers.CharField(max_length=64, default="general")
    creator_role = serializers.CharField(max_length=64, default="Employee")


class ForwardFileSerializer(serializers.Serializer):
    """Input serializer for forwarding an active file."""

    receiver_id = serializers.CharField(max_length=64)
    receiver_role = serializers.CharField(max_length=64, default="")
    comment = serializers.CharField()
    sender_role = serializers.CharField(max_length=64, default="")


class ReturnFileSerializer(serializers.Serializer):
    """Input serializer for returning a file to a previous sender."""

    comment = serializers.CharField()
    sender_role = serializers.CharField(max_length=64, default="")
    target_receiver_id = serializers.CharField(max_length=64, required=False, allow_null=True)


class ArchiveFileSerializer(serializers.Serializer):
    """Input serializer for closing and archiving a file."""

    remarks = serializers.CharField()
    user_role = serializers.CharField(max_length=64, default="")
