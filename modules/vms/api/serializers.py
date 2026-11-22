"""DRF serializers for VMS endpoints."""

from __future__ import annotations

from rest_framework import serializers

from modules.vms.models import (
    AccessPolicy,
    BlacklistEntry,
    EmergencyMusterRoster,
    GateCheckLog,
    HostPreAuthorization,
    Pass,
    Visitor,
    VisitRequest,
)


class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "organization",
            "id_document_type",
            "id_document_number",
            "is_vip",
            "vip_reason",
            "created_at",
        ]


class PassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pass
        fields = [
            "id",
            "pass_number",
            "qr_token",
            "pass_type",
            "valid_from",
            "valid_to",
            "status",
            "created_at",
        ]


class VisitRequestSerializer(serializers.ModelSerializer):
    visitor = VisitorSerializer(read_only=True)
    digital_pass = PassSerializer(read_only=True)

    class Meta:
        model = VisitRequest
        fields = [
            "id",
            "visitor",
            "host_id",
            "host_name",
            "purpose",
            "scheduled_start",
            "scheduled_end",
            "actual_check_in",
            "actual_check_out",
            "status",
            "pass_type",
            "access_zones",
            "admin_notes",
            "rejection_reason",
            "is_urgent_exception",
            "extension_hours",
            "external_event_ref",
            "digital_pass",
            "created_at",
        ]


class PreRegisterInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    organization = serializers.CharField(max_length=150, required=False, allow_blank=True)
    id_document_type = serializers.CharField(max_length=30, default="AADHAAR")
    id_document_number = serializers.CharField(max_length=100)
    host_id = serializers.IntegerField(min_value=1)
    purpose = serializers.CharField(max_length=255)
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField()
    access_zones = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    is_urgent_exception = serializers.BooleanField(required=False, default=False)
    external_event_ref = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )


class WalkInInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    organization = serializers.CharField(max_length=150, required=False, allow_blank=True)
    id_document_type = serializers.CharField(max_length=30, default="AADHAAR")
    id_document_number = serializers.CharField(max_length=100)
    host_id = serializers.IntegerField(min_value=1)
    purpose = serializers.CharField(max_length=255)
    duration_hours = serializers.IntegerField(required=False, default=4)
    auto_approve = serializers.BooleanField(required=False, default=False)


class BulkRegisterInputSerializer(serializers.Serializer):
    records = serializers.ListField(child=serializers.DictField())
    host_id = serializers.IntegerField(min_value=1)
    purpose = serializers.CharField(max_length=255)
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField()
    external_event_ref = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )


class DecisionInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["APPROVE", "REJECT", "approve", "reject"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ContingencyInputSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3)


class ExtensionInputSerializer(serializers.Serializer):
    hours = serializers.IntegerField(min_value=1, max_value=8)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class TerminateInputSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3)


class GateValidateInputSerializer(serializers.Serializer):
    qr_token = serializers.CharField()
    gate_name = serializers.CharField(max_length=100, default="Main Gate")


class GateCheckInInputSerializer(serializers.Serializer):
    pass_id = serializers.IntegerField()
    gate_name = serializers.CharField(max_length=100, default="Main Gate")


class GateCheckOutInputSerializer(serializers.Serializer):
    pass_id = serializers.IntegerField()
    gate_name = serializers.CharField(max_length=100, default="Main Gate")


class GateOverrideInputSerializer(serializers.Serializer):
    pass_id = serializers.IntegerField()
    reason = serializers.CharField(min_length=3)
    gate_name = serializers.CharField(max_length=100, default="Main Gate Override")


class OfflineSyncInputSerializer(serializers.Serializer):
    events = serializers.ListField(child=serializers.DictField())


class ZoneValidateInputSerializer(serializers.Serializer):
    pass_id = serializers.IntegerField()
    zone_name = serializers.CharField(max_length=100)


class ZoneElevateInputSerializer(serializers.Serializer):
    pass_id = serializers.IntegerField()
    zone_name = serializers.CharField(max_length=100)
    hours = serializers.IntegerField(min_value=1, max_value=12)
    reason = serializers.CharField(min_length=3)


class BlacklistEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlacklistEntry
        fields = [
            "id",
            "name",
            "id_document_type",
            "id_document_number",
            "phone",
            "reason",
            "status",
            "safe_list_until",
            "safe_list_reason",
            "safe_listed_by_id",
            "created_at",
        ]


class BlacklistCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    id_document_type = serializers.CharField(max_length=30)
    id_document_number = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    reason = serializers.CharField(min_length=3)


class SafeListInputSerializer(serializers.Serializer):
    hours = serializers.IntegerField(min_value=1, max_value=72)
    reason = serializers.CharField(min_length=3)


class EmergencyMusterInputSerializer(serializers.Serializer):
    assembly_point = serializers.CharField(max_length=100, default="Central Ground")


class EmergencyRosterSerializer(serializers.ModelSerializer):
    visitor = VisitorSerializer(read_only=True)
    pass_record = PassSerializer(read_only=True)

    class Meta:
        model = EmergencyMusterRoster
        fields = [
            "id",
            "muster_id",
            "assembly_point",
            "initiated_by_id",
            "initiated_at",
            "visitor",
            "pass_record",
            "check_in_time",
            "accountability_status",
            "accounted_at",
            "accounted_by_id",
            "notes",
        ]


class RollCallInputSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ACCOUNTED", "UNACCOUNTED"], default="ACCOUNTED")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class AccessPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPolicy
        fields = [
            "id",
            "version",
            "visiting_hours_start",
            "visiting_hours_end",
            "max_duration_hours",
            "is_published",
            "published_at",
            "policy_notes",
            "created_at",
        ]


class PreAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostPreAuthorization
        fields = [
            "id",
            "host_id",
            "visitor_email",
            "visitor_name",
            "valid_from",
            "valid_to",
            "is_active",
            "created_at",
        ]


class GateCheckLogSerializer(serializers.ModelSerializer):
    pass_number = serializers.CharField(source="pass_record.pass_number", read_only=True)

    class Meta:
        model = GateCheckLog
        fields = [
            "id",
            "pass_number",
            "gate_name",
            "checkpoint_type",
            "action",
            "operator_id",
            "is_override",
            "override_reason",
            "is_offline_sync",
            "timestamp",
        ]


class GateValidateResponseSerializer(serializers.Serializer):
    is_valid = serializers.BooleanField()
    message = serializers.CharField()
    pass_record = PassSerializer(allow_null=True, required=False)


class ZoneValidateResponseSerializer(serializers.Serializer):
    allowed = serializers.BooleanField()
    message = serializers.CharField()


class ZoneElevateResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()
    valid_to = serializers.DateTimeField()


class EmergencyMusterResponseSerializer(serializers.Serializer):
    muster_id = serializers.CharField()
    status = serializers.CharField()


class OfflineSyncResponseSerializer(serializers.Serializer):
    synced = serializers.IntegerField()
    failed = serializers.IntegerField()


class AnalyticsDashboardSerializer(serializers.Serializer):
    total_today = serializers.IntegerField()
    onsite_now = serializers.IntegerField()
    approved = serializers.IntegerField()
    pending = serializers.IntegerField()
    rejected = serializers.IntegerField()
    overstays = serializers.IntegerField()
    completed = serializers.IntegerField()
