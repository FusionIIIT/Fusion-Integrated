from rest_framework import serializers

from modules.elm.models import LeaveApplication, LeaveBalance, LeaveType


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = ["id", "leave_type", "start_date", "end_date", "half_day",
                  "days", "special_purpose", "special_purpose_admissible",
                  "status", "created_at"]
        read_only_fields = fields


class LeaveBalanceSerializer(serializers.ModelSerializer):
    remaining = serializers.SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = ["id", "year", "leave_type", "entitled", "used", "lapsed",
                  "remaining"]
        read_only_fields = fields

    def get_remaining(self, obj):
        return obj.entitled - obj.used - obj.lapsed


class ApplyInputSerializer(serializers.Serializer):
    leave_type = serializers.ChoiceField(choices=LeaveType.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(choices=["NONE", "FIRST", "SECOND"],
                                       default="NONE")
    special_purpose = serializers.CharField(allow_blank=True, required=False,
                                            default="")
    special_purpose_admissible = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError(
                "end_date cannot be before start_date.")
        return attrs
