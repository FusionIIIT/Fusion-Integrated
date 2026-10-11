from rest_framework import serializers

from modules.elm.models import Leave

class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leave
        fields = [
            'id', 'user_id', 'user_details', 'leave_type', 'start_date', 'end_date',
            'reason', 'status', 'approved_by', 'cancelled_by', 'resumed_by', 'extended_by'
        ]

class LeaveRequestWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leave
        fields = [
            'user_id', 'leave_type', 'start_date', 'end_date', 'reason',
            'approved_by', 'cancelled_by', 'resumed_by', 'extended_by'
        ]
        extra_kwargs = {
            'user_id': {'required': True},
            'leave_type': {'required': True},
            'start_date': {'required': True},
            'end_date': {'required': True}
        }

class EligibilityVerdictSerializer(serializers.Serializer):
    eligible = serializers.BooleanField()
    reason = serializers.CharField(allow_blank=True, allow_null=True)

