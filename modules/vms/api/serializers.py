"""DRF Serializers for VMS REST API."""
from rest_framework import serializers

from modules.vms.models.access import (
    Zone,
)
from modules.vms.models.muster import (
    Muster,
    MusterEntry,
)
from modules.vms.models.visitors import (
    Alert,
    BlacklistRecord,
    SafeListRecord,
    Visitor,
)
from modules.vms.models.visits import (
    Pass,
    VisitRequest,
)


class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = [
            "id",
            "full_name",
            "phone",
            "email",
            "id_doc_type",
            "id_doc_number",
            "photo_url",
            "is_anonymous",
            "is_disabled",
            "disabled_reason",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class VisitorRegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    identity_type = serializers.CharField(max_length=50, default="aadhaar")
    id_number = serializers.CharField(max_length=100)
    organization = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class VisitRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitRequest
        fields = [
            "id",
            "visitor_id",
            "host_user_id",
            "purpose",
            "requested_start",
            "requested_end",
            "requested_zones",
            "status",
            "instructions",
            "decision_notes",
            "rejection_reason",
            "decision_at",
            "decided_by_user_id",
            "created_at",
        ]
        read_only_fields = ["id", "status", "decision_at", "decided_by_user_id", "created_at"]


class VisitRequestDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    instructions = serializers.CharField(required=False, allow_blank=True, default="")
    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")


class VisitPassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pass
        fields = [
            "id",
            "visit_id",
            "visitor_id",
            "pass_type",
            "pass_code",
            "status",
            "valid_from",
            "valid_until",
            "permitted_zones",
            "parent_pass_id",
            "created_at",
        ]
        read_only_fields = ["id", "pass_code", "created_at"]


class GateCheckInSerializer(serializers.Serializer):
    qr_code_hash = serializers.CharField(max_length=128)
    gate_machine_id = serializers.CharField(max_length=100, default="GATE-01")
    gate_name = serializers.CharField(max_length=100, default="Main Gate")


class GateCheckOutSerializer(serializers.Serializer):
    pass_number = serializers.CharField(max_length=50)
    gate_machine_id = serializers.CharField(max_length=100, default="GATE-01")
    gate_name = serializers.CharField(max_length=100, default="Main Gate")


class ZoneAccessCheckSerializer(serializers.Serializer):
    pass_number = serializers.CharField(max_length=50)
    zone_code = serializers.CharField(max_length=50)
    gate_machine_id = serializers.CharField(max_length=100, default="READER-01")


class ZoneElevationSerializer(serializers.Serializer):
    pass_number = serializers.CharField(max_length=50)
    zone_code = serializers.CharField(max_length=50)
    reason = serializers.CharField(max_length=255, default="Temporary Elevation Granted")


class BlacklistRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlacklistRecord
        fields = [
            "id",
            "full_name",
            "phone",
            "email",
            "id_doc_type",
            "id_doc_number",
            "reason",
            "added_by_user_id",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SafeListRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafeListRecord
        fields = [
            "id",
            "full_name",
            "phone",
            "email",
            "id_doc_type",
            "id_doc_number",
            "expiry_date",
            "notes",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CampusZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = [
            "id",
            "code",
            "name",
            "is_restricted",
            "is_vip_designated",
            "description",
        ]


class GateAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            "id",
            "alert_type",
            "severity",
            "message",
            "visitor_id",
            "visit_id",
            "pass_id",
            "zone_code",
            "status",
            "created_at",
        ]


class EmergencyMusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Muster
        fields = [
            "id",
            "status",
            "muster_type",
            "reason",
            "triggered_by_user_id",
            "started_at",
            "completed_at",
            "summary",
        ]
        read_only_fields = ["id", "started_at"]


class MusterRollCallSerializer(serializers.ModelSerializer):
    class Meta:
        model = MusterEntry
        fields = [
            "id",
            "muster",
            "visit_id",
            "visitor_id",
            "host_user_id",
            "last_seen_zone",
            "status",
            "marked_present",
            "marked_at",
            "notes",
        ]


class BulkEventUploadSerializer(serializers.Serializer):
    event_name = serializers.CharField(max_length=150)
    duration_hours = serializers.IntegerField(default=8)
    allowed_zones = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
    )
    attendees = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of objects containing 'name', 'phone', 'email'",
    )
