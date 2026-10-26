from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from modules.leave.models import LeaveRequest
from modules.directory.models import UserRef


class LeaveRequestSerializer(serializers.ModelSerializer):
    reason = serializers.CharField(trim_whitespace=True)

    class Meta:
        model = LeaveRequest
        fields = ("id", "employee_user_id", "leave_type", "start_date", "end_date",
                  "reason", "cl_period", "station_leave", "station_leave_details",
                  "status", "reviewed_by_user_id", "reviewer_comment", "created_at")
        read_only_fields = ("id", "employee_user_id", "status", "reviewed_by_user_id",
                            "reviewer_comment", "created_at")

    def validate(self, attrs):
        user_id = self.context["request"].principal.user_id
        if not UserRef.objects.filter(user_id=user_id, kind__in=("faculty", "staff"),
                                      is_active=True).exists():
            raise serializers.ValidationError("Only active faculty or staff may request leave.")
        request = LeaveRequest(employee_user_id=user_id, **attrs)
        try:
            request.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict")
                                              else exc.messages) from exc
        return attrs

