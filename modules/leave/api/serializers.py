"""Wire representations for the Employee Leave Management API."""
from rest_framework import serializers

from modules.leave.models import (HolidayCalendar, LeaveAccountEntry, LeaveBalance,
    LeaveAuditEvent, LeaveCategory, LeavePolicy, LeaveRequest, LeaveRouteConfiguration,
    LeaveSanction, LeaveSLAConfiguration, WorkflowTask)


class LeaveCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCategory
        fields = ["code", "label", "description"]
        read_only_fields = fields


class LeaveBalanceSerializer(serializers.ModelSerializer):
    category_code = serializers.CharField(source="category_id", read_only=True)
    class Meta:
        model = LeaveBalance
        fields = ["id", "category_code", "year", "entitlement", "carried_over", "available", "updated_at"]
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    category_code = serializers.CharField(source="category_id", read_only=True)
    class Meta:
        model = LeaveRequest
        fields = ["id", "employee_id", "category_code", "request_type", "parent_request", "status", "start_date", "end_date",
                  "duration_days", "cl_portion", "reason", "station_leave", "station_destination",
                  "station_departure_at", "station_return_at", "medical_evidence_ref", "substitute_user_id",
                  "actual_resume_date", "submitted_at", "decided_at", "created_at", "updated_at"]
        read_only_fields = ["id", "employee_id", "category_code", "request_type", "parent_request", "status", "duration_days", "submitted_at",
                            "decided_at", "created_at", "updated_at"]


class LeaveDraftSerializer(serializers.ModelSerializer):
    category_code = serializers.SlugRelatedField(source="category", slug_field="code", queryset=LeaveCategory.objects.all())
    class Meta:
        model = LeaveRequest
        fields = ["category_code", "start_date", "end_date", "cl_portion", "reason", "station_leave",
                  "station_destination", "station_departure_at", "station_return_at", "medical_evidence_ref",
                  "substitute_user_id"]


class LeaveTaskSerializer(serializers.ModelSerializer):
    category_code = serializers.CharField(source="request.category_id", read_only=True)
    employee_id = serializers.IntegerField(source="request.employee_id", read_only=True)
    class Meta:
        model = WorkflowTask
        fields = ["id", "request_id", "employee_id", "category_code", "sequence", "role", "state", "due_at", "created_at"]
        read_only_fields = fields


class LeaveSanctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveSanction
        fields = ["id", "task_id", "actor_user_id", "decision", "notes", "decided_at"]
        read_only_fields = fields


class LeaveAuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAuditEvent
        fields = ["id", "action", "from_status", "to_status", "actor_user_id", "occurred_at", "details"]
        read_only_fields = fields


class LeaveAccountEntrySerializer(serializers.ModelSerializer):
    category_code = serializers.CharField(source="category_id", read_only=True)
    class Meta:
        model = LeaveAccountEntry
        fields = ["id", "category_code", "year", "amount", "kind", "request_id", "source_key", "explanation", "created_at"]
        read_only_fields = fields


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ["policy_key", "cl_days", "rh_days", "scl_days", "faculty_vl_days",
                  "nonfaculty_el_days", "col_days", "col_medical_evidence_required",
                  "year_end_month", "year_end_day", "updated_at"]
        read_only_fields = ["policy_key", "updated_at"]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "year", "revision", "holidays", "state", "published_by_user_id", "published_at", "created_at"]
        read_only_fields = ["id", "revision", "state", "published_by_user_id", "published_at", "created_at"]


class HolidayCalendarDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["year", "holidays"]


class LeaveRouteConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRouteConfiguration
        fields = ["id", "category", "employee_kind", "designation", "unit_code",
                  "final_authority_role", "final_authority_user_id", "establishment_role",
                  "establishment_user_id", "requires_substitute", "active", "updated_at"]
        read_only_fields = ["id", "updated_at"]

    def validate(self, attrs):
        role = attrs.get("establishment_role", getattr(self.instance, "establishment_role", ""))
        establishment_id = attrs.get("establishment_user_id", getattr(self.instance, "establishment_user_id", None))
        final_id = attrs.get("final_authority_user_id", getattr(self.instance, "final_authority_user_id", None))
        if not final_id:
            raise serializers.ValidationError({"final_authority_user_id": "A final authority user must be assigned."})
        if role and not establishment_id:
            raise serializers.ValidationError({"establishment_user_id": "Assign a user when an Establishment step is configured."})
        return attrs


class LeaveSLAConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveSLAConfiguration
        fields = ["id", "role", "reminder_after_hours", "escalate_after_hours",
                  "escalation_role", "escalation_user_id", "updated_by_user_id", "updated_at"]
        read_only_fields = ["id", "updated_by_user_id", "updated_at"]

    def validate(self, attrs):
        reminder = attrs.get("reminder_after_hours", getattr(self.instance, "reminder_after_hours", 24))
        escalate = attrs.get("escalate_after_hours", getattr(self.instance, "escalate_after_hours", 72))
        if escalate < reminder:
            raise serializers.ValidationError({"escalate_after_hours": "Escalation must be at or after the reminder threshold."})
        return attrs


class LeaveExtensionInputSerializer(serializers.Serializer):
    new_end_date = serializers.DateField()
    reason = serializers.CharField()
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class LeaveResumptionInputSerializer(serializers.Serializer):
    actual_resume_date = serializers.DateField()
    reason = serializers.CharField()


class OfflineLeaveInputSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField(min_value=1)
    category_code = serializers.SlugRelatedField(slug_field="code", queryset=LeaveCategory.objects.all())
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    sanction_reference = serializers.CharField(max_length=240)
    evidence_reference = serializers.CharField(max_length=500)


class AccountAdjustmentInputSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField(min_value=1)
    category_code = serializers.SlugRelatedField(slug_field="code", queryset=LeaveCategory.objects.all())
    year = serializers.IntegerField(min_value=2000, max_value=9999)
    amount = serializers.DecimalField(max_digits=8, decimal_places=2)
    reference = serializers.CharField(max_length=100)
    explanation = serializers.CharField(max_length=240)
