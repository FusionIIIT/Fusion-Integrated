from django.utils import timezone
from rest_framework import serializers
from applications.elm.models import LeaveApplication

VALID_CATEGORIES = ['CL', 'RH', 'SCL', 'EL', 'COL', 'VL']


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            'id',
            'applicant',
            'start_date',
            'end_date',
            'category',
            'reason',
            'status',
            'remarks',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'applicant', 'status', 'created_at', 'updated_at']

    def validate_category(self, value):
        if value not in VALID_CATEGORIES:
            raise serializers.ValidationError(
                f"Invalid category '{value}'. Must be one of: {', '.join(VALID_CATEGORIES)}"
            )
        return value

    def validate_reason(self, value):
        cleaned_reason = value.strip() if value else ''
        if len(cleaned_reason) < 10:
            raise serializers.ValidationError(
                "Reason must be at least 10 characters long."
            )
        return cleaned_reason

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        today = timezone.now().date()

        if start_date and start_date < today:
            raise serializers.ValidationError(
                {"start_date": "Start date cannot be in the past."}
            )

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "End date must be greater than or equal to start date."}
            )

        return attrs