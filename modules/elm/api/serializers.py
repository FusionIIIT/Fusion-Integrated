from rest_framework import serializers

from modules.elm.domain.leave import Category
from modules.elm.models import (
    HolidayDate, LeaveApplication, LeaveApplicationTransition, LeaveBalance,
)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available = serializers.SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = ("category", "year", "allotted", "reserved", "used", "available")

    def get_available(self, obj):
        return obj.allotted - obj.reserved - obj.used


class LeaveApplicationTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplicationTransition
        fields = ("from_status", "to_status", "from_stage", "to_stage", "actor_user_id",
                  "action", "note", "at")


class LeaveApplicationSerializer(serializers.ModelSerializer):
    history = LeaveApplicationTransitionSerializer(source="transitions", many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = ("id", "employee_id", "category", "start_date", "end_date", "half_day",
                  "chargeable_days", "reason", "station_leave", "station_details", "status",
                  "current_stage", "created_at", "decided_at", "history")
        read_only_fields = fields


class ApplyInputSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=[c.value for c in Category])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(choices=("", "first", "second"), required=False, default="")
    reason = serializers.CharField(max_length=2000, trim_whitespace=True)
    station_leave = serializers.BooleanField(required=False, default=False)
    station_details = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class DecisionInputSerializer(serializers.Serializer):
    approve = serializers.BooleanField(required=False)
    recommended = serializers.BooleanField(required=False)
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")


class BalanceInputSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField(min_value=1)
    category = serializers.ChoiceField(choices=[c.value for c in Category])
    year = serializers.IntegerField(min_value=2000, max_value=9999)
    allotted = serializers.DecimalField(max_digits=7, decimal_places=1, min_value=0)


class RouteStepSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=("unit_head", "establishment", "final", "director_self"))
    approver_user_id = serializers.IntegerField(min_value=1)


class RouteInputSerializer(serializers.Serializer):
    steps = RouteStepSerializer(many=True, allow_empty=False, max_length=3)


class CalendarDateSerializer(serializers.Serializer):
    day = serializers.DateField()
    name = serializers.CharField(max_length=160, trim_whitespace=True)
    kind = serializers.ChoiceField(choices=(HolidayDate.Kind.CLOSED, HolidayDate.Kind.RESTRICTED))


class CalendarInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, trim_whitespace=True)
    dates = CalendarDateSerializer(many=True, allow_empty=True, max_length=500)
