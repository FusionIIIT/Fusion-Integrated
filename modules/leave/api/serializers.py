from rest_framework import serializers

from modules.leave.models import LeaveBalance, LeaveRequest, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "code", "name", "annual_allowance"]
        read_only_fields = fields


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    available_days = serializers.SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = ["id", "leave_type", "leave_type_name", "year", "allocated_days",
                  "carried_days", "available_days"]
        read_only_fields = fields

    def get_available_days(self, obj):
        used = sum(LeaveRequest.objects.filter(
            user_id=obj.user_id, leave_type=obj.leave_type, start_date__year=obj.year,
            status__in=["pending", "approved"]).values_list("days", flat=True))
        return max(0, obj.allocated_days + obj.carried_days - used)


class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    user_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = ["id", "user_id", "leave_type", "leave_type_name", "start_date",
                  "end_date", "days", "reason", "status", "review_note", "created_at"]
        read_only_fields = ["id", "days", "status", "review_note", "created_at"]


class ReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
