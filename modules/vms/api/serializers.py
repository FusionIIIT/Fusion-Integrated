"""DRF Serializers for VMS REST API."""
from rest_framework import serializers
from modules.vms.models.visitors import (
    Visitor,
    BlacklistRecord,
    SafeListRecord,
    VisitorIDDocument,
)
from modules.vms.models.visits import (
    VisitRequest,
    VisitPass,
    VisitLog,
)
from modules.vms.models.access import (
    CampusZone,
    AccessPolicy,
    ZoneAccessLog,
    GateAlert,
)
from modules.vms.models.muster import (
    EmergencyMuster,
    MusterRollCall,
)


class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = [
            "id",
            "full_name",
            "phone",
            "email",
            "identity_type",
            "id_number",
            "organization",
            "is_active",
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
    visitor = VisitorSerializer(read_only=True)
    visitor_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = VisitRequest
        fields = [
            "id",
            "visitor",
            "visitor_id",
            "host_user_id",
            "purpose",
            "intended_start",
            "intended_end",
            "actual_arrival",
            "actual_departure",
            "current_zone",
            "status",
            "instructions",
            "rejection_reason",
            "decided_at",
            "decided_by_user_id",
            "created_at",
        ]
        read_only_fields = ["id", "status", "decided_at", "decided_by_user_id", "created_at"]


class VisitRequestDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    instructions = serializers.CharField(required=False, allow_blank=True, default="")
    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")


class VisitPassSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source="visitor.full_name", read_only=True)
    visitor_phone = serializers.CharField(source="visitor.phone", read_only=True)

    class Meta:
        model = VisitPass
        fields = [
            "id",
            "pass_number",
            "visitor",
            "visitor_name",
            "visitor_phone",
            "visit",
            "pass_type",
            "valid_from",
            "valid_to",
            "status",
            "allowed_zones",
            "qr_code_hash",
            "parent_pass",
            "created_at",
        ]
        read_only_fields = ["id", "pass_number", "qr_code_hash", "created_at"]


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
            "id_number",
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
            "id_number",
            "category",
            "valid_until",
            "added_by_user_id",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CampusZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampusZone
        fields = [
            "id",
            "code",
            "name",
            "description",
            "requires_special_elevation",
            "max_occupancy",
            "is_active",
        ]


class GateAlertSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source="visitor.full_name", read_only=True)

    class Meta:
        model = GateAlert
        fields = [
            "id",
            "alert_type",
            "severity",
            "status",
            "visitor",
            "visitor_name",
            "pass_record",
            "gate_machine_id",
            "details",
            "created_at",
            "closed_at",
            "closed_by_user_id",
        ]


class EmergencyMusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyMuster
        fields = [
            "id",
            "muster_code",
            "initiated_by_user_id",
            "reason",
            "status",
            "started_at",
            "completed_at",
            "total_on_site_at_start",
            "total_accounted",
            "total_unaccounted",
            "summary_report",
        ]
        read_only_fields = ["id", "muster_code", "started_at"]


class MusterRollCallSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source="visitor.full_name", read_only=True)
    visitor_phone = serializers.CharField(source="visitor.phone", read_only=True)

    class Meta:
        model = MusterRollCall
        fields = [
            "id",
            "muster",
            "visitor",
            "visitor_name",
            "visitor_phone",
            "status",
            "last_known_zone",
            "checked_by_user_id",
            "checked_at",
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
