from rest_framework import serializers
from modules.leave.models import LeaveType, LeaveApplication


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "code", "name", "max_days_per_year", "is_active"]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "applicant_id",
            "leave_type",
            "leave_type_code",
            "leave_type_name",
            "start_date",
            "end_date",
            "reason",
            "status",
            "reviewer_id",
            "review_remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "reviewer_id", "review_remarks", "created_at", "updated_at"]

    def validate(self, attrs):
        if attrs.get("start_date") and attrs.get("end_date"):
            if attrs["start_date"] > attrs["end_date"]:
                raise serializers.ValidationError({"end_date": "End date must be after start date."})
        return attrs


class LeaveReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
