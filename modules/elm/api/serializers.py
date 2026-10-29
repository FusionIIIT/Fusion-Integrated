from rest_framework import serializers

from modules.elm.models import Leave


class LeaveSerializer(serializers.ModelSerializer):
    employee_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Leave
        fields = [
            "id",
            "employee_id",
            "category",
            "start_date",
            "end_date",
            "reason",
            "status",
        ]
        read_only_fields = ["id", "employee_id", "status"]