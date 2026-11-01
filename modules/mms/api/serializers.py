"""MMS API serializers — explicit field lists only, never fields='__all__'."""
from rest_framework import serializers

from modules.mms.models import RegistrationRequest, RegistrationWindow


class RegistrationWindowSerializer(serializers.ModelSerializer):
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = RegistrationWindow
        fields = ("id", "label", "opens_at", "closes_at", "is_open", "created_at")
        read_only_fields = fields


class RegistrationRequestSerializer(serializers.ModelSerializer):
    window_label = serializers.CharField(source="window.label", read_only=True)

    class Meta:
        model = RegistrationRequest
        fields = (
            "id", "window", "window_label", "student_user_id",
            "remarks", "status", "decision_note", "decided_at", "created_at",
        )
        read_only_fields = fields


class SubmitRegistrationSerializer(serializers.Serializer):
    window_id = serializers.IntegerField()
    remarks = serializers.CharField(max_length=500, required=False, allow_blank=True,
                                    default="")


class DecideRegistrationSerializer(serializers.Serializer):
    DECISIONS = [
        (RegistrationRequest.STATUS_APPROVED, "Approved"),
        (RegistrationRequest.STATUS_REJECTED, "Rejected"),
    ]
    decision = serializers.ChoiceField(choices=DECISIONS)
    decision_note = serializers.CharField(max_length=300, required=False,
                                          allow_blank=True, default="")
