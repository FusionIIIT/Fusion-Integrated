from rest_framework import serializers

from modules.leave_elm.models import LeaveApplication


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "employee_id",
            "category",
            "start_date",
            "end_date",
            "reason",
            "station_leave_required",
            "station_leave_details",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "employee_id",
            "status",
            "created_at",
            "updated_at",
        ]
