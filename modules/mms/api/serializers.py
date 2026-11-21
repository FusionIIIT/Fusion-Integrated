"""DRF Serializers for MMS."""

from rest_framework import serializers
from modules.mms.models import (
    DailyMenuItem,
    MessActionLog,
    MessFeedback,
    MessRegistration,
    MessRoleAssignment,
    RebateRequest,
    RegistrationWindow,
)


class MessRoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessRoleAssignment
        fields = "__all__"


class RegistrationWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationWindow
        fields = "__all__"


class MessRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessRegistration
        fields = "__all__"


class DailyMenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyMenuItem
        fields = "__all__"


class RebateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RebateRequest
        fields = "__all__"


class MessFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessFeedback
        fields = "__all__"


class MessActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessActionLog
        fields = "__all__"

