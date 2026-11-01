from rest_framework import serializers

from modules.leave_elm.models import LeaveApplication, SubstituteResponse


class LeaveBalanceSerializer(serializers.Serializer):
    """Serializer for LeaveBalance object."""

    available_balance = serializers.DecimalField(max_digits=5, decimal_places=1)
    annual_entitlement = serializers.DecimalField(max_digits=5, decimal_places=1)


class LeaveApplicationSerializer(serializers.ModelSerializer):
    """Serializer for LeaveApplication object."""

    # Custom field to display category nicely
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    is_half_day_start = serializers.BooleanField(required=False)
    is_half_day_end = serializers.BooleanField(required=False)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "employee_id",
            "category",
            "category_display",
            "start_date",
            "end_date",
            "reason",
            "is_station_leave",
            "duration_days",
            "status",
            "substitute_id",
            "is_half_day_start",
            "is_half_day_end",
        ]
        read_only_fields = ["status", "duration_days"]


class SubstituteResponseSerializer(serializers.ModelSerializer):
    """Serializer for SubstituteResponse object."""

    class Meta:
        model = SubstituteResponse
        fields = ["id", "application_id", "substitute_id", "response_status", "notes"]


class LeaveApplicationCreateSerializer(serializers.Serializer):
    """Input serializer for creating a new leave application."""

    employee_id = serializers.CharField(max_length=64)
    category = serializers.CharField(max_length=10)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(max_length=500)
    substitute_id = serializers.CharField(max_length=64, required=False, allow_null=True)
    is_station_leave = serializers.BooleanField(default=False)
    is_half_day_start = serializers.BooleanField(default=False)
    is_half_day_end = serializers.BooleanField(default=False)

    def validate_leave_application(self, data: dict) -> dict:
        """
        Validates application eligibility (balance and overlap) before creation.
        In a full implementation, this would call a service layer.
        """
        # Mock validation logic based on business requirements:
        # 1. Balance Check (Assume service layer handles this)
        # 2. Overlap Check (Assume service layer handles this)

        # For now, we pass the data through, but flag this as the implementation point.
        return data

    def create(self, validated_data):
        """
        Creates a leave application via the service layer, enforcing all business rules.
        """
        try:
            # Call the service layer to handle balance checks, duration calculation, and persistence
            from modules.leave_elm.services.leave import apply_leave

            return apply_leave(
                employee_id=validated_data["employee_id"],
                category=validated_data["category"],
                start_date_str=validated_data["start_date"].isoformat(),
                end_date_str=validated_data["end_date"].isoformat(),
                reason=validated_data["reason"],
                substitute_id=validated_data.get("substitute_id"),
                is_station_leave=validated_data["is_station_leave"],
                is_half_day_start=validated_data["is_half_day_start"],
                is_half_day_end=validated_data["is_half_day_end"],
            )
        except (ValueError, KeyError) as e:
            # Return error response with the exception message
            raise serializers.ValidationError(
                {"detail": f"Error creating leave application: {e!s}"}
            ) from e


class LeaveApplicationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating leave application status."""

    notes = serializers.CharField(max_length=500, required=False, write_only=True)

    class Meta:
        model = LeaveApplication
        fields = ["status", "notes"]
        read_only_fields = ["id"]
