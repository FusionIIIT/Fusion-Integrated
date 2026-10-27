from rest_framework import serializers

from modules.elm.models import LeaveApplication, LeaveCategory


class LeaveCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCategory
        fields = "__all__"


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")