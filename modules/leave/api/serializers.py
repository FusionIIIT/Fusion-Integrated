from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from modules.leave.models import LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ("id", "employee_user_id", "leave_type", "start_date", "end_date",
                  "reason", "status", "reviewed_by_user_id", "reviewer_comment",
                  "created_at")
        read_only_fields = ("id", "employee_user_id", "status", "reviewed_by_user_id",
                            "reviewer_comment", "created_at")

    def validate(self, attrs):
        request = LeaveRequest(employee_user_id=self.context["request"].principal.user_id,
                               **attrs)
        try:
            request.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict")
                                              else exc.messages) from exc
        return attrs

