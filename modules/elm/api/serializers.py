from rest_framework import serializers
from modules.elm.models import LeaveRequest, LeaveAccount, LeavePolicy, LeaveCalendarDay

class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ("id","user_id","category","start_date","end_date","days","purpose","station_leave","status","substitute_user_id","substitute_decision","unit_head_decision","final_decision","decision_reason","created_at","updated_at")
        read_only_fields = ("id","user_id","days","status","substitute_decision","unit_head_decision","final_decision","decision_reason","created_at","updated_at")
    def validate(self, attrs):
        if attrs.get("end_date", self.instance.end_date if self.instance else None) < attrs.get("start_date", self.instance.start_date if self.instance else None):
            raise serializers.ValidationError({"end_date":"End date must be on or after start date."})
        return attrs

class LeaveAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAccount
        fields = ("category","balance","year")
        read_only_fields = fields

class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ("id","category","annual_entitlement","requires_substitute","higher_sanction","enabled")
