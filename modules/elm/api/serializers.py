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
        read_only_fields = ("id", "created_at", "updated_at", "status")

    def validate_employee_id(self, value):
        if value <= 0:
            raise serializers.ValidationError("Employee ID must be a positive integer.")
        return value

    def validate_reason(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("A leave reason is required.")
        return value.strip()

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                "end_date": "End date cannot be before start date."
            })
        return attrs
