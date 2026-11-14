from rest_framework import serializers

from modules.elm.domain.leave_policy import LeaveCategory, LeavePolicy
from modules.elm.models import LEAVE_CATEGORY_CHOICES


class LeaveApplicationSubmitSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=LEAVE_CATEGORY_CHOICES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=5000, trim_whitespace=True)
    half_day_portion = serializers.ChoiceField(
        choices=(("first_half", "First half"), ("second_half", "Second half")),
        required=False,
        allow_blank=True,
        default="",
    )

    def validate(self, attrs):
        try:
            policy = LeavePolicy(LeaveCategory(attrs["category"]), 0)
            attrs["requested_days"] = policy.calculate_days(
                attrs["start_date"],
                attrs["end_date"],
                half_day=bool(attrs["half_day_portion"]),
            )
        except (TypeError, ValueError) as err:
            raise serializers.ValidationError({"dates": str(err)}) from err
        if not attrs["purpose"].strip():
            raise serializers.ValidationError({"purpose": "Please enter a reason."})
        return attrs
