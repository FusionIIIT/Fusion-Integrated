from rest_framework import serializers

from modules.directory.models import UserRef
from modules.elm.models import LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_id = serializers.IntegerField(
        source="employee.user_id", read_only=True
    )

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "employee_id", "category", "start_date", "end_date",
            "reason", "substitute", "substitute_required", "status",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "employee_id", "status", "created_at", "updated_at",
        ]


class LeaveRequestCreateSerializer(serializers.ModelSerializer):
    substitute = serializers.PrimaryKeyRelatedField(
        queryset=UserRef.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = LeaveRequest
        fields = [
            "category", "start_date", "end_date", "reason",
            "substitute", "substitute_required",
        ]

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        substitute = attrs.get("substitute")
        substitute_required = attrs.get("substitute_required", False)

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                "end_date": "End date cannot precede start date."
            })

        if substitute_required and substitute is None:
            raise serializers.ValidationError({
                "substitute": "A substitute is required."
            })

        employee_id = self.context["request"].principal.user_id
        if substitute is not None and substitute.user_id == employee_id:
            raise serializers.ValidationError({
                "substitute": "You cannot nominate yourself."
            })

        return attrs
