from rest_framework import serializers
from ..models import LeavePolicy, HolidayCalendar, LeaveApplication, RoleBasedUnit


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = "__all__"


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = "__all__"


class LeaveApplicationStatusChoices(serializers.ChoiceField):
    CHOICES = [
        ("Pending", "Pending"),
        ("Withdrawn", "Withdrawn"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
        ("Cancelled", "Cancelled"),
        ("Extension Approved", "Extension Approved"),
        ("Resumption Recorded", "Resumption Recorded"),
    ]
