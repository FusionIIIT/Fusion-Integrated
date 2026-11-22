"""Serializers for MMS endpoints."""
from rest_framework import serializers

from modules.mms.models import (
    MessAnnouncement,
    MessBill,
    MessDeregistration,
    MessFeedback,
    MessMenu,
    MessRebate,
    MessRegistration,
    MessRegistrationWindow,
    MessRoleAssignment,
    SpecialFoodRequest,
    VacationFoodResponse,
    VacationFoodSurvey,
)


class MessRoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessRoleAssignment
        fields = "__all__"


class MessRegistrationWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessRegistrationWindow
        fields = "__all__"


class MessRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessRegistration
        fields = "__all__"


class MessDeregistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessDeregistration
        fields = "__all__"


class MessMenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessMenu
        fields = "__all__"


class MessRebateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessRebate
        fields = "__all__"


class VacationFoodSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationFoodSurvey
        fields = "__all__"


class VacationFoodResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationFoodResponse
        fields = "__all__"


class SpecialFoodRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialFoodRequest
        fields = "__all__"


class MessBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessBill
        fields = "__all__"


class MessAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessAnnouncement
        fields = "__all__"


class MessFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessFeedback
        fields = "__all__"
