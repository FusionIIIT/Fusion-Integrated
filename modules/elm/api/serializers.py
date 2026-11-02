from rest_framework import serializers

from modules.elm.models import LeaveCategory, LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    category = serializers.ChoiceField(choices=LeaveCategory.choices)

    class Meta:
        model = LeaveRequest
        fields = ['id', 'user_id', 'category', 'start_date', 'end_date',
                  'reason', 'status', 'created_at', 'updated_at']
        # The owner comes from the session and status only moves via review.
        read_only_fields = ['user_id', 'status', 'created_at', 'updated_at']

    def validate(self, attrs):
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {'end_date': 'The end date cannot be before the start date.'})
        return attrs
