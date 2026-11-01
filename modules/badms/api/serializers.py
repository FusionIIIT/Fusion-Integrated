from rest_framework import serializers

from core.files import drive
from core.files.drive import InvalidDriveLink
from modules.badms.models import ArchivalRequest


class ArchivalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivalRequest
        fields = (
            "id", "requester_user_id", "department", "file_name", "file_date",
            "owners", "file_type", "reason", "attachment_url",
            "initial_classification", "status", "decided_by_user_id",
            "decision_note", "created_at", "decided_at",
        )
        read_only_fields = fields


class ArchivalRequestCreateSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=180)
    file_date = serializers.DateField()
    owners = serializers.ListField(
        child=serializers.CharField(max_length=150),
        allow_empty=False,
        max_length=20,
    )
    file_type = serializers.CharField(max_length=80)
    reason = serializers.CharField(max_length=2000)
    attachment_url = serializers.URLField(max_length=500)
    initial_classification = serializers.ChoiceField(
        choices=[value for value, _ in ArchivalRequest.CLASSIFICATIONS],
        required=False,
        default="routine",
    )

    def validate_attachment_url(self, value):
        try:
            return drive.parse(value).url
        except InvalidDriveLink as exc:
            raise serializers.ValidationError(exc.message) from exc


class ArchivalDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approve", "reject"))
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
