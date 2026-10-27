from rest_framework import serializers
from .models import (
    LeaveApplication,
    SubstituteRequest,
    LeaveBalance,
    LeaveLedgerEntry,
    HolidayCalendar,
    VacationPeriod,
)

class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = "__all__"

class ApplyLeaveSerializer(serializers.Serializer):
    category = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField()
    half_day_type = serializers.ChoiceField(choices=["full", "half"])
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    responsibilities = serializers.CharField(allow_blank=True)
    is_station_leave = serializers.BooleanField(default=False)
    station_departure_date = serializers.DateField(required=False, allow_null=True)
    station_arrival_date = serializers.DateField(required=False, allow_null=True)
    station_destination = serializers.CharField(allow_blank=True)
    address_during_leave = serializers.CharField(allow_blank=True)

class SubstituteRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteRequest
        fields = "__all__"

class SubstituteResponseSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["accepted", "declined"])
    remarks = serializers.CharField(allow_blank=True)

class UnitHeadReviewSerializer(serializers.Serializer):
    recommended = serializers.BooleanField()
    remarks = serializers.CharField(allow_blank=True)

class EstablishmentReviewSerializer(serializers.Serializer):
    remarks = serializers.CharField(allow_blank=True)

class SanctionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    remarks = serializers.CharField(allow_blank=True)

class CancellationRequestSerializer(serializers.Serializer):
    reason = serializers.CharField()

class ResumptionSerializer(serializers.Serializer):
    resumption_date = serializers.DateField()
    remarks = serializers.CharField(allow_blank=True)

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = "__all__"

class LeaveLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveLedgerEntry
        fields = "__all__"

class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = "__all__"

class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = "__all__"

class OfflineLeaveSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reference_no = serializers.CharField()
    sanction_date = serializers.DateField()
    purpose = serializers.CharField()