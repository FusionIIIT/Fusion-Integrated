from rest_framework import serializers

from modules.vms.models import (
    AccessPolicy,
    BlacklistEntry,
    BlacklistVersion,
    Gate,
    RoleAssignment,
    SafeListEntry,
    VipPermission,
    Zone,
)
from modules.vms.services import policy_admin

# --- roles ------------------------------------------------------------------------

class RoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAssignment
        fields = ["id", "user_id", "role", "scope_type", "scope_id", "starts_at",
                  "ends_at", "assigned_by_user_id", "revoked_at"]


class RoleAssignInput(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    role = serializers.ChoiceField(choices=RoleAssignment.Role.choices)
    scope_type = serializers.ChoiceField(choices=RoleAssignment.ScopeType.choices,
                                         default="campus")
    scope_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    starts_at = serializers.DateTimeField(required=False, default=None)
    ends_at = serializers.DateTimeField()


class RoleReassignInput(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    ends_at = serializers.DateTimeField(required=False, default=None)


# --- integrations -----------------------------------------------------------------

class IntegrationInput(serializers.Serializer):
    value = serializers.DictField()


# --- vip --------------------------------------------------------------------------

class VipSerializer(serializers.ModelSerializer):
    zone_ids = serializers.SerializerMethodField()

    class Meta:
        model = VipPermission
        fields = ["id", "visitor", "zone_ids", "valid_from", "valid_until",
                  "granted_by_user_id", "revoked_at"]

    def get_zone_ids(self, obj):
        return sorted(z.pk for z in obj.zones.all())


class VipGrantInput(serializers.Serializer):
    visitor_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    id_doc_type = serializers.CharField(required=False, allow_blank=True, default="")
    id_doc_number = serializers.CharField(required=False, allow_blank=True, default="")
    full_name = serializers.CharField(required=False, allow_blank=True, default="")
    phone = serializers.CharField(required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    zone_ids = serializers.ListField(child=serializers.IntegerField(), default=list)
    restricted_zone_ids = serializers.ListField(child=serializers.IntegerField(),
                                                default=list)
    valid_from = serializers.DateTimeField(required=False, default=None)
    valid_until = serializers.DateTimeField()


# --- policy -----------------------------------------------------------------------

class PolicySerializer(serializers.ModelSerializer):
    restricted_zones = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = AccessPolicy
        fields = ["id", "version", "status", "published_at", *policy_admin.FIELDS,
                  "restricted_zones", "created_by_user_id"]


class PolicyCreateInput(serializers.Serializer):
    base_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class PolicyUpdateInput(serializers.Serializer):
    visiting_hours_start = serializers.TimeField(required=False)
    visiting_hours_end = serializers.TimeField(required=False)
    max_visit_hours = serializers.IntegerField(required=False)
    walk_in_pass_hours = serializers.IntegerField(required=False)
    approval_timeout_hours = serializers.IntegerField(required=False)
    reminder_after_hours = serializers.IntegerField(required=False)
    advance_registration_hours = serializers.IntegerField(required=False)
    allow_same_day_urgent = serializers.BooleanField(required=False)
    contingency_sla_minutes = serializers.IntegerField(required=False)
    walkin_rate_limit_per_hour = serializers.IntegerField(required=False)
    restricted_zone_ids = serializers.ListField(child=serializers.IntegerField(),
                                                required=False)


# --- blacklist --------------------------------------------------------------------

class BlacklistVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlacklistVersion
        fields = ["id", "version", "status", "published_at", "published_by_user_id"]


class BlacklistEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlacklistEntry
        fields = ["id", "version", "name", "id_doc_number", "phone", "email", "reason",
                  "severity", "expiry_date", "is_active"]
        read_only_fields = ["id", "version"]


class BlacklistEntryInput(serializers.ModelSerializer):
    class Meta:
        model = BlacklistEntry
        fields = ["name", "id_doc_number", "phone", "email", "reason", "severity",
                  "expiry_date", "is_active"]
        extra_kwargs = {"name": {"required": True}, "reason": {"required": True}}


class SafeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafeListEntry
        fields = ["id", "visitor_id_doc_number", "reason", "expires_at",
                  "created_by_user_id", "revoked_at"]


class SafeListInput(serializers.Serializer):
    visitor_id_doc_number = serializers.CharField(max_length=60)
    reason = serializers.CharField(max_length=255)
    expires_at = serializers.DateTimeField()


# --- zones and gates --------------------------------------------------------------

class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ["id", "name", "is_restricted", "parent_zone", "is_active"]


class ZoneInput(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    is_restricted = serializers.BooleanField(required=False)
    parent_zone_id = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)


class GateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gate
        fields = ["id", "name", "zone", "device_id", "is_active"]


class GateInput(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    zone_id = serializers.IntegerField()
    device_id = serializers.CharField(max_length=80, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)


# --- audit ------------------------------------------------------------------------

class AuditFilterInput(serializers.Serializer):
    actor = serializers.IntegerField(required=False)
    action = serializers.CharField(required=False)
    entity_type = serializers.CharField(required=False)
    entity_id = serializers.CharField(required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)

    def filters(self) -> dict:
        d = self.validated_data
        return {"actor_user_id": d.get("actor"), "action": d.get("action"),
                "entity_type": d.get("entity_type"), "entity_id": d.get("entity_id"),
                "date_from": d.get("date_from"), "date_to": d.get("date_to")}


class AuditRowSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    actor_user_id = serializers.IntegerField(allow_null=True)
    actor_role = serializers.CharField()
    action = serializers.CharField()
    entity_type = serializers.CharField()
    entity_id = serializers.CharField()
    detail = serializers.JSONField()
