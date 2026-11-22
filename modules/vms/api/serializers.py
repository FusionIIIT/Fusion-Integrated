from rest_framework import serializers

from modules.vms.models import VisitRequest


class VisitRequestSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source="visitor.display_name", read_only=True)

    class Meta:
        model = VisitRequest
        fields = (
            "id",
            "visitor_name",
            "host_user_id",
            "kind",
            "status",
            "purpose",
            "starts_at",
            "ends_at",
            "requested_zones",
            "approved_zones",
            "special_instructions",
            "decision_reason",
            "created_at",
        )
        read_only_fields = fields


class RegistrationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    id_type = serializers.ChoiceField(
        choices=[
            (x, x)
            for x in (
                "passport",
                "national_id",
                "driving_license",
                "voter_id",
                "other_government_id",
            )
        ]
    )
    id_value = serializers.CharField(max_length=100, write_only=True, trim_whitespace=True)
    identity_document = serializers.FileField(write_only=True, required=True)
    purpose = serializers.CharField(max_length=500)
    host_user_id = serializers.IntegerField(min_value=1)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    requested_zones = serializers.ListField(
        child=serializers.CharField(max_length=80), required=False, max_length=20
    )


class WalkInSerializer(RegistrationSerializer):
    host_unavailable = serializers.BooleanField(default=False, required=False)
    checkpoint = serializers.CharField(max_length=100, required=False, allow_blank=True)


class OfflineEntrySerializer(serializers.Serializer):
    credential = serializers.CharField(max_length=2048)
    checkpoint = serializers.CharField(max_length=100, required=False, allow_blank=True)
    event_at = serializers.DateTimeField()


class ManualVisitLogSerializer(serializers.Serializer):
    event_type = serializers.ChoiceField(
        choices=[
            ("entry", "Entry"),
            ("exit", "Exit"),
            ("zone_granted", "Zone granted"),
            ("zone_denied", "Zone denied"),
            ("gate_denied", "Gate denied"),
        ]
    )
    occurred_at = serializers.DateTimeField()
    location = serializers.CharField(max_length=160, required=False, allow_blank=True)
    zone = serializers.CharField(max_length=80, required=False, allow_blank=True)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    metadata = serializers.DictField(required=False, default=dict)
    gate_attempt_id = serializers.IntegerField(min_value=1, required=False)

    def validate_metadata(self, value):
        if len(value) > 20 or any(not isinstance(key, str) or len(key) > 80 for key in value):
            raise serializers.ValidationError("Metadata must be a small object with short keys.")
        return value


class GateOverrideDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=[("authorize", "Authorize"), ("deny", "Deny")])
    reason = serializers.CharField(max_length=500)


class GateEscalationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class DecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    zones = serializers.ListField(
        child=serializers.CharField(max_length=80), required=False, max_length=20
    )
    instructions = serializers.CharField(max_length=500, required=False, allow_blank=True)
    starts_at = serializers.DateTimeField(required=False)
    ends_at = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        if ("starts_at" in attrs) != ("ends_at" in attrs):
            raise serializers.ValidationError("starts_at and ends_at must be supplied together.")
        return attrs


class VisitExtensionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=[("approve", "Approve"), ("reject", "Reject")])
    ends_at = serializers.DateTimeField()
    reason = serializers.CharField(max_length=500)


class ZoneElevationSerializer(serializers.Serializer):
    zone = serializers.CharField(max_length=80)
    reason = serializers.CharField(max_length=500)
    minutes = serializers.IntegerField(min_value=1, max_value=240)


class PolicySerializer(serializers.Serializer):
    visiting_hours_start = serializers.TimeField(required=False, allow_null=True)
    visiting_hours_end = serializers.TimeField(required=False, allow_null=True)
    maximum_visit_minutes = serializers.IntegerField(min_value=1, max_value=10080, required=False)
    walk_in_minutes = serializers.IntegerField(min_value=1, max_value=1440, required=False)
    approval_timeout_minutes = serializers.IntegerField(
        min_value=1, max_value=10080, required=False
    )
    contingency_timeout_minutes = serializers.IntegerField(
        min_value=1, max_value=1440, required=False
    )
    advance_registration_minutes = serializers.IntegerField(
        min_value=0, max_value=525600, required=False
    )
    reminder_minutes = serializers.ListField(
        child=serializers.IntegerField(min_value=1), max_length=10, required=False
    )
    restricted_zones = serializers.ListField(
        child=serializers.CharField(max_length=80), max_length=100, required=False
    )


class RoleAssignmentSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    role = serializers.ChoiceField(choices=[("admin", "Admin"), ("security", "Security Personnel")])
    scope_type = serializers.ChoiceField(
        choices=[("campus", "Campus"), ("zone", "Zone"), ("gate", "Gate")]
    )
    scope_value = serializers.CharField(max_length=100, required=False, allow_blank=True)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField(required=False, allow_null=True)


class RegistryEntrySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160, required=False, allow_blank=True)
    fingerprint = serializers.RegexField(r"^[0-9a-f]{64}$", required=False, allow_blank=True)
    reason = serializers.CharField(max_length=500)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class IntegrationSerializer(serializers.Serializer):
    integration_type = serializers.ChoiceField(
        choices=[
            (v, v)
            for v, _ in (
                ("campus_id", "Campus ID"),
                ("directory", "User directory"),
                ("event_management", "Event Management"),
                ("hostel", "Hostel Management"),
                ("access_control", "Access Control"),
                ("notification", "Notifications"),
            )
        ]
    )
    endpoint = serializers.URLField(max_length=500, required=False, allow_blank=True)
    enabled = serializers.BooleanField()
    config = serializers.DictField(required=False, default=dict)


class VipPermissionSerializer(serializers.Serializer):
    visitor_id = serializers.IntegerField(min_value=1)
    zones = serializers.ListField(child=serializers.CharField(max_length=80), max_length=20)
    valid_from = serializers.DateTimeField()
    valid_until = serializers.DateTimeField()
    reason = serializers.CharField(max_length=500)


class PreAuthorizationSerializer(serializers.Serializer):
    visitor_id = serializers.IntegerField(min_value=1)
    zones = serializers.ListField(child=serializers.CharField(max_length=80), max_length=20)
    valid_from = serializers.DateTimeField()
    valid_until = serializers.DateTimeField()
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class EventRecordSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=180)
    external_event_id = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    zones = serializers.ListField(
        child=serializers.CharField(max_length=80), max_length=100, required=False, default=list
    )
    fast_lane_enabled = serializers.BooleanField(default=False)
    overflow_limit = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    rate_limit_per_minute = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class EventControlsSerializer(serializers.Serializer):
    fast_lane_enabled = serializers.BooleanField()
    overflow_limit = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    rate_limit_per_minute = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class EventGuestImportSerializer(serializers.Serializer):
    visit_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), min_length=1, max_length=500
    )

    def validate_visit_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Visit IDs must be unique.")
        return value
