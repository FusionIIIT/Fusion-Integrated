"""Wire shapes for VMS.

Ref: 02_VMS_Requirement_Registry_CFR_AFR_v1.3
"""
from rest_framework import serializers

from modules.visitors.models import (
    ID_DOCUMENT_TYPES,
    AccessPolicy,
    BlacklistEntry,
    EmergencyMuster,
    GateLog,
    MusterRollCall,
    PreAuthorization,
    SafeListEntry,
    TemporaryZoneElevation,
    VIPPermission,
    VisitApproval,
    VisitRequest,
    ZoneAccessLog,
    ZoneDefinition,
)


# --- Nested / read-only serializers ------------------------------------------

class VisitApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitApproval
        fields = ["id", "action", "actor_user_id", "actor_role", "note",
                  "created_at"]


class GateLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GateLog
        fields = ["id", "visit", "event_type", "gate_name", "recorded_by",
                  "is_offline", "synced_at", "note", "created_at"]


class ZoneAccessLogSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)

    class Meta:
        model = ZoneAccessLog
        fields = ["id", "visit", "zone_code", "zone_name", "action",
                  "recorded_by", "note", "created_at"]


# --- Core visit request ------------------------------------------------------

class VisitRequestSerializer(serializers.ModelSerializer):
    approvals = VisitApprovalSerializer(many=True, read_only=True)

    class Meta:
        model = VisitRequest
        fields = [
            "id", "kind", "parent", "status",
            "visitor_name", "visitor_email", "visitor_phone",
            "visitor_organization", "visitor_id_type", "visitor_id_number",
            "host_user_id", "purpose", "expected_date",
            "expected_time_from", "expected_time_until",
            "number_of_visitors", "allowed_zones",
            "pass_type", "pass_code", "pass_valid_from", "pass_valid_until",
            "checked_in_at", "checked_in_by",
            "checked_out_at", "checked_out_by",
            "decided_by", "decided_at", "decision_note",
            "pre_authorization", "vip_permission",
            "registered_by", "event_name", "bulk_upload_batch",
            "created_at", "updated_at", "approvals",
        ]


# --- Input serializers -------------------------------------------------------

class PreRegisterSerializer(serializers.Serializer):
    """VMS-UC-010: pre-register a visit."""
    visitor_name = serializers.CharField(max_length=200)
    visitor_phone = serializers.CharField(max_length=20)
    visitor_email = serializers.EmailField(required=False, default="")
    visitor_organization = serializers.CharField(required=False, default="",
                                                  max_length=200)
    visitor_id_type = serializers.ChoiceField(
        choices=[c for c, _ in ID_DOCUMENT_TYPES])
    visitor_id_number = serializers.CharField(max_length=50)
    host_user_id = serializers.IntegerField()
    purpose = serializers.CharField(max_length=500)
    expected_date = serializers.DateField()
    expected_time_from = serializers.TimeField(required=False, allow_null=True)
    expected_time_until = serializers.TimeField(required=False, allow_null=True)
    number_of_visitors = serializers.IntegerField(required=False, default=1,
                                                   min_value=1)


class WalkInSerializer(serializers.Serializer):
    """VMS-UC-017: walk-in registration by Security Personnel."""
    visitor_name = serializers.CharField(max_length=200)
    visitor_phone = serializers.CharField(max_length=20)
    visitor_id_type = serializers.ChoiceField(
        choices=[c for c, _ in ID_DOCUMENT_TYPES])
    visitor_id_number = serializers.CharField(max_length=50)
    host_user_id = serializers.IntegerField()
    purpose = serializers.CharField(max_length=500)
    gate_name = serializers.CharField(required=False, default="main",
                                      max_length=60)


class DecisionSerializer(serializers.Serializer):
    """VMS-UC-013: approve or reject a visit request."""
    action = serializers.ChoiceField(choices=["approve", "reject"])
    note = serializers.CharField(required=False, allow_blank=True, default="")


class GateValidationSerializer(serializers.Serializer):
    """VMS-UC-018: validate pass at gate."""
    gate_name = serializers.CharField(max_length=60)


class CheckoutSerializer(serializers.Serializer):
    """VMS-UC-021: check out visitor."""
    gate_name = serializers.CharField(max_length=60)


class TerminateSerializer(serializers.Serializer):
    """VMS-UC-016/036: terminate visit early."""
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class OverrideSerializer(serializers.Serializer):
    """VMS-UC-019: manual gate override."""
    gate_name = serializers.CharField(max_length=60)
    reason = serializers.CharField()


class ZoneAccessSerializer(serializers.Serializer):
    """VMS-UC-023: validate zone access."""
    zone_code = serializers.CharField(max_length=30)


class ZoneElevationSerializer(serializers.Serializer):
    """VMS-UC-024: grant temporary zone elevation."""
    zone_code = serializers.CharField(max_length=30)
    valid_minutes = serializers.IntegerField(required=False, default=60,
                                              min_value=5, max_value=480)


class MusterTriggerSerializer(serializers.Serializer):
    """VMS-UC-026/032: trigger emergency muster."""
    reason = serializers.CharField()


class RollCallSerializer(serializers.Serializer):
    """VMS-UC-027: account a visitor in muster roll-call."""
    location_note = serializers.CharField(required=False, allow_blank=True,
                                          default="")


class ExtensionSerializer(serializers.Serializer):
    """VMS-UC-034: request visit extension."""
    extended_until_time = serializers.TimeField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


# --- Supporting model serializers --------------------------------------------

class AccessPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPolicy
        fields = ["id", "version", "visiting_hours_start", "visiting_hours_end",
                  "max_visit_duration_hours", "default_walkin_duration_minutes",
                  "advance_registration_days", "approval_timeout_hours",
                  "is_published", "published_by", "created_at"]


class BlacklistEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlacklistEntry
        fields = ["id", "entry_type", "full_name", "id_document_type",
                  "id_document_number", "reason", "added_by", "is_active",
                  "created_at"]


class PreAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreAuthorization
        fields = ["id", "user_id", "visitor_name", "visitor_phone",
                  "visitor_email", "visitor_id_type", "visitor_id_number",
                  "purpose", "valid_from", "valid_until", "allowed_zones",
                  "is_active", "created_at"]


class ZoneDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZoneDefinition
        fields = ["id", "code", "name", "access_level", "description",
                  "is_active"]


class EmergencyMusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyMuster
        fields = ["id", "triggered_by", "trigger_role", "reason", "status",
                  "resolved_at", "resolved_by", "total_on_site",
                  "total_accounted", "created_at"]


class MusterRollCallSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source="visit.visitor_name",
                                         read_only=True)

    class Meta:
        model = MusterRollCall
        fields = ["id", "muster", "visit", "visitor_name", "accounted",
                  "accounted_by", "accounted_at", "location_note"]


class VIPPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VIPPermission
        fields = ["id", "visitor_name", "visitor_id_number",
                  "scope_description", "valid_from", "valid_until",
                  "bypass_host_approval", "bypass_zone_restriction",
                  "granted_by", "is_active", "created_at"]


class TemporaryZoneElevationSerializer(serializers.ModelSerializer):
    zone_code = serializers.CharField(source="zone.code", read_only=True)

    class Meta:
        model = TemporaryZoneElevation
        fields = ["id", "visit", "zone_code", "granted_by", "valid_until",
                  "used", "used_at", "created_at"]
