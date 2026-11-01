from rest_framework import serializers
from modules.elm.models import CalendarEntry, CalendarVersion, LeaveRequest, Notification, OfflineLeaveRecord

class LeaveRequestSerializer(serializers.ModelSerializer):
    history = serializers.SerializerMethodField()
    class Meta:
        model = LeaveRequest
        fields = ["id", "user_id", "category", "kind", "parent", "start_date", "end_date", "half", "days", "purpose", "station_leave", "station_leave_from", "station_leave_to", "station_leave_address", "substitute_user_id", "substitute_status", "status", "route", "stage", "current_role", "recommendation", "decision_note", "submitted_at", "decided_at", "cancellation_reason", "actual_return_date", "resumption_kind", "resumption_note", "evidence", "created_at", "updated_at", "history"]
        read_only_fields = ["id", "user_id", "kind", "parent", "days", "substitute_status", "status", "route", "stage", "current_role", "recommendation", "decision_note", "submitted_at", "decided_at", "created_at", "updated_at", "history"]
    def get_history(self, obj):
        return [{"from": t.from_status, "to": t.to_status, "event": t.event, "actor_user_id": t.actor_user_id, "actor_role": t.actor_role, "note": t.note, "at": t.created_at} for t in obj.transitions.all()]

class LeaveCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=["", "first", "second"], required=False, allow_blank=True, default="")
    purpose = serializers.CharField(required=False, allow_blank=True, default="")
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    station_leave = serializers.BooleanField(required=False, default=False)
    station_leave_from = serializers.DateField(required=False, allow_null=True)
    station_leave_to = serializers.DateField(required=False, allow_null=True)
    station_leave_address = serializers.CharField(required=False, allow_blank=True, default="")
    evidence = serializers.ListField(child=serializers.JSONField(), required=False, default=list)

class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject", "recommend", "not_recommended", "forward"])
    note = serializers.CharField(required=False, allow_blank=True, default="")

class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True, default="")

class ReplacementSubstituteSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()

class CancellationSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")

class ExtensionSerializer(serializers.Serializer):
    end_date = serializers.DateField()
    purpose = serializers.CharField(required=False, allow_blank=True, default="")
    evidence = serializers.ListField(child=serializers.JSONField(), required=False, default=list)

class ResumptionSerializer(serializers.Serializer):
    actual_return_date = serializers.DateField()
    note = serializers.CharField(required=False, allow_blank=True, default="")

class CalendarEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEntry
        fields = ["id", "kind", "start_date", "end_date", "label"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError("end_date must not be before start_date.")
        return attrs

class CalendarSerializer(serializers.ModelSerializer):
    entries = CalendarEntrySerializer(many=True, required=False)
    class Meta:
        model = CalendarVersion
        fields = ["id", "name", "status", "effective_from", "published_at", "published_by_user_id", "entries"]
        read_only_fields = ["id", "status", "published_at", "published_by_user_id"]

class OfflineRecordSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    days = serializers.DecimalField(max_digits=7, decimal_places=2, required=False)
    sanction_reference = serializers.CharField(required=False, allow_blank=True, default="")
    evidence = serializers.ListField(child=serializers.JSONField(), required=False, default=list)
    note = serializers.CharField(required=False, allow_blank=True, default="")

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "topic", "title", "body", "payload", "read_at", "created_at"]

class BalanceSerializer(serializers.Serializer):
    category = serializers.CharField()
    year = serializers.IntegerField()
    balance = serializers.DecimalField(max_digits=9, decimal_places=2)

class OfflineRecordMaintenanceSerializer(serializers.Serializer):
    sanction_reference = serializers.CharField(required=False, allow_blank=False)
    evidence = serializers.ListField(child=serializers.JSONField(), required=False, allow_empty=False)
    note = serializers.CharField(required=False, allow_blank=True)

class SlaConfigSerializer(serializers.Serializer):
    reminder_hours = serializers.FloatField(required=False, allow_null=True, min_value=0)
    escalation_hours = serializers.FloatField(required=False, allow_null=True, min_value=0)
    escalation_role = serializers.CharField(required=False, allow_blank=True, default="")

class PolicyConfigSerializer(serializers.Serializer):
    params = serializers.JSONField()
    hierarchy = serializers.JSONField()
    updated_at = serializers.DateTimeField(required=False)

class LedgerEntrySerializer(serializers.Serializer):
    category = serializers.CharField()
    delta = serializers.DecimalField(max_digits=9, decimal_places=2)
    entry_type = serializers.CharField()
    year = serializers.IntegerField()
    created_at = serializers.DateTimeField()

class OfflineRecordOutputSerializer(serializers.ModelSerializer):
    synced_request_id = serializers.IntegerField(read_only=True, allow_null=True)
    class Meta:
        model = OfflineLeaveRecord
        fields = ["id", "user_id", "category", "start_date", "end_date", "days", "sanction_reference", "evidence", "recorded_by_user_id", "note", "synced_request_id", "created_at"]

class NoteSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")

class PolicyConfigWriteSerializer(serializers.Serializer):
    params = serializers.JSONField(required=False)
    hierarchy = serializers.JSONField(required=False)

class OfflineRecordCreateResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    synced_request_id = serializers.IntegerField(allow_null=True)

class OfflineRecordMaintenanceOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    category = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    sanction_reference = serializers.CharField(allow_blank=True)
    evidence = serializers.ListField(child=serializers.JSONField())
    note = serializers.CharField(allow_blank=True)
