from rest_framework import serializers

from modules.elm.models import LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = (
            "id",
            "leave_type_code",
            "requested_start_date",
            "requested_end_date",
            "day_part",
            "total_days",
            "status",
            "submitted_at",
            "updated_at",
            "approved_at",
            "rejection_reason",
        )
        read_only_fields = fields


class LeaveRequestSubmissionSerializer(serializers.Serializer):
    leave_type_code = serializers.ChoiceField(
        choices=LeaveRequest.LEAVE_CHOICES
    )
    requested_start_date = serializers.DateField()
    requested_end_date = serializers.DateField()
    day_part = serializers.ChoiceField(
        choices=LeaveRequest.DAY_PART_CHOICES,
        default="FULL",
    )


class LeaveRequestApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("APPROVE", "REJECT"))
    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
    )
