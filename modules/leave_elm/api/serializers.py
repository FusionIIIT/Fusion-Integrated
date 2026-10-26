from rest_framework import serializers

from modules.leave_elm.models import LeaveApplication, LeaveBalance


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ("id", "user_id", "year", "leave_type", "balance")
        read_only_fields = fields


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "user_id",
            "leave_type",
            "start_date",
            "end_date",
            "is_half_day",
            "purpose",
            "status",
            "is_station_leave",
            "station_address",
            "substitute_user_id",
            "substitute_accepted",
            "created_at",
        )
        read_only_fields = ("id", "user_id", "status", "substitute_accepted", "created_at")


class LeaveApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = (
            "leave_type",
            "start_date",
            "end_date",
            "is_half_day",
            "purpose",
            "is_station_leave",
            "station_address",
            "substitute_user_id",
        )

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        leave_type = attrs.get("leave_type")
        is_half_day = attrs.get("is_half_day", False)
        is_station_leave = attrs.get("is_station_leave", False)
        station_address = attrs.get("station_address", "")
        substitute_user_id = attrs.get("substitute_user_id")

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                {"end_date": "end_date must be on or after start_date."}
            )

        if is_half_day:
            if leave_type != "CL":
                raise serializers.ValidationError(
                    {"is_half_day": "Half-day leave is only permitted for Casual Leave (CL)."}
                )
            if start_date != end_date:
                raise serializers.ValidationError(
                    {"is_half_day": "Half-day leave must be for a single date."}
                )

        if is_station_leave and not station_address.strip():
            raise serializers.ValidationError(
                {"station_address": "Station address is required when station leave is requested."}
            )

        request = self.context.get("request")
        actor = getattr(request, "principal", None)
        if actor and substitute_user_id and substitute_user_id == actor.user_id:
            raise serializers.ValidationError(
                {"substitute_user_id": "Applicant cannot nominate themselves as substitute."}
            )

        return attrs
