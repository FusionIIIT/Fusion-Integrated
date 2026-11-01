# serializers.py

from rest_framework import serializers
from modules.mess.models import (
    MenuItem,
    RegistrationRequest,
    DeregistrationRequest,
    RebateRequest,
    SpecialFoodRequest,
    VacationResponse,
    MonthlyBill,
    Feedback,
    Announcement,
    RequestTransition,
)

class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = '__all__'

class RegistrationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationRequest
        fields = '__all__'
        read_only = ('user_id', 'status', 'decided_by_user_id', 'decided_at')

class DeregistrationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeregistrationRequest
        fields = '__all__'
        read_only = ('user_id', 'status', 'decided_by_user_id', 'decided_at')

class RebateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RebateRequest
        fields = '__all__'
        read_only = ('user_id', 'status', 'decided_by_user_id', 'decided_at')

class SpecialFoodRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialFoodRequest
        fields = '__all__'
        read_only = ('user_id', 'status', 'decided_by_user_id', 'decided_at')

class VacationResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationResponse
        fields = '__all__'
        read_only = ('user_id', 'status', 'decided_by_user_id', 'decided_at')

class MonthlyBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyBill
        fields = '__all__'
        read_only = ('user_id', 'status', 'decided_by_user_id', 'decided_at')

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = '__all__'
        read_only = ('user_id', 'status', 'decided_by_user_id', 'decided_at')

class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = '__all__'
        read_only = ('user_id', 'status', 'decided_by_user_id', 'decided_at')

class RequestTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestTransition
        fields = '__all__'
        read_only = ('user_id', 'status', 'decided_by_user_id', 'decided_at')
