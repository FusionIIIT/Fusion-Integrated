from rest_framework import serializers

from modules.elm.models import (
    LeaveCategory,
    LeaveDayPart,
    LeaveRequest,
    LeaveRequestEvent,
)


class LeaveRequestEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequestEvent
        fields = ['event_type', 'from_status', 'to_status', 'created_at']
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    category = serializers.ChoiceField(choices=LeaveCategory.choices)
    day_part = serializers.ChoiceField(
        choices=LeaveDayPart.choices,
        default=LeaveDayPart.FULL_DAY,
    )
    events = LeaveRequestEventSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = ['id', 'user_id', 'category', 'start_date', 'end_date',
                  'day_part', 'reason', 'status', 'events', 'created_at',
                  'updated_at']
        # The owner comes from the session and status only moves via review.
        read_only_fields = ['user_id', 'status', 'created_at', 'updated_at']

    def validate(self, attrs):
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        category = attrs.get('category', getattr(self.instance, 'category', None))
        day_part = attrs.get(
            'day_part',
            getattr(self.instance, 'day_part', LeaveDayPart.FULL_DAY),
        )
        if start and end and end < start:
            raise serializers.ValidationError(
                {'end_date': 'The end date cannot be before the start date.'})
        if day_part != LeaveDayPart.FULL_DAY and not (
            category == LeaveCategory.CL
            and start
            and start == end
        ):
            raise serializers.ValidationError({
                'day_part': (
                    'Half-day selection is only available for a single-day '
                    'Casual Leave request.'
                ),
            })
        return attrs
