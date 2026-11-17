from decimal import Decimal
from rest_framework import serializers
from modules.leave.models import LeaveType, LeaveBalance, LeaveRequest, LeaveLedger


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            "id",
            "code",
            "name",
            "max_days_per_year",
            "allows_half_day",
            "requires_attachment",
            "is_active",
        ]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    remaining_days = serializers.FloatField(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "leave_type",
            "leave_type_code",
            "leave_type_name",
            "year",
            "allocated_days",
            "used_days",
            "remaining_days",
        ]


class LeaveLedgerSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveLedger
        fields = [
            "id",
            "user_id",
            "leave_type",
            "leave_type_code",
            "leave_type_name",
            "transaction_type",
            "days",
            "balance_after",
            "reference_request",
            "remarks",
            "created_at",
        ]


class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "leave_type",
            "leave_type_code",
            "leave_type_name",
            "start_date",
            "end_date",
            "duration_days",
            "is_half_day",
            "half_day_slot",
            "reason",
            "status",
            "is_station_leave",
            "station_start_date",
            "station_end_date",
            "station_address",
            "emergency_contact_no",
            "attachment_path",
            "recommender_user_id",
            "recommendation_remarks",
            "recommended_at",
            "approver_user_id",
            "rejection_reason",
            "approval_remarks",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "status",
            "recommender_user_id",
            "recommendation_remarks",
            "recommended_at",
            "approver_user_id",
            "rejection_reason",
            "approval_remarks",
            "approved_at",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if start and end and start > end:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})

        is_half_day = attrs.get("is_half_day", False)
        leave_type = attrs.get("leave_type")
        if is_half_day:
            if leave_type and not leave_type.allows_half_day:
                raise serializers.ValidationError({"is_half_day": f"Half day is not permitted for {leave_type.name}."})
            if not attrs.get("half_day_slot"):
                raise serializers.ValidationError({"half_day_slot": "Slot (Forenoon/Afternoon) is required for half day leave."})
            if start != end:
                raise serializers.ValidationError({"duration_days": "Half day leave must have identical start and end dates."})
            attrs["duration_days"] = Decimal("0.5")

        # Station Leave validation (BR-EL-013)
        if attrs.get("is_station_leave"):
            if not attrs.get("station_start_date") or not attrs.get("station_end_date"):
                raise serializers.ValidationError({"station_dates": "Station leave requires both start and end dates."})
            if attrs["station_start_date"] > attrs["station_end_date"]:
                raise serializers.ValidationError({"station_end_date": "Station end date must be on or after start date."})
            if not attrs.get("station_address"):
                raise serializers.ValidationError({"station_address": "Station address outside Jabalpur is required."})
            if not attrs.get("emergency_contact_no"):
                raise serializers.ValidationError({"emergency_contact_no": "Emergency contact number is required."})

        # Attachment validation (BR-EL-009)
        if leave_type and leave_type.requires_attachment and not attrs.get("attachment_path"):
            raise serializers.ValidationError({"attachment_path": f"Supporting attachment/certificate is required for {leave_type.name}."})

        return attrs


class LeaveRecommendationSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
