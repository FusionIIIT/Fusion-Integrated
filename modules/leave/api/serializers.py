from rest_framework import serializers

from modules.leave.models import LeaveApplication, LeaveBalance


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "leave_type",
            "year",
            "allocated",
            "used",
        ]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField()
    status = serializers.ReadOnlyField()
    reviewed_by = serializers.ReadOnlyField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "user_id",
            "leave_type",
            "start_date",
            "end_date",
            "half_day",
            "days",
            "reason",
            "is_station_leave",
            "station_leave_address",
            "replacement_user_id",
            "status",
            "reviewed_by",
            "review_remarks",
            "created_at",
            "updated_at",
        ]


class LeaveReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
