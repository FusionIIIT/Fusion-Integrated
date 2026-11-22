"""VMS DRF Serializers with OpenAPI schema documentation."""

from rest_framework import serializers

from modules.vms.models.access import GateAlert
from modules.vms.models.muster import EmergencyMuster
from modules.vms.models.visitors import BlacklistEntry, Visitor
from modules.vms.models.visits import Visit


class VisitorSerializer(serializers.ModelSerializer):
    id_number = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Visitor
        fields = [
            "id",
            "first_name",
            "last_name",
            "phone",
            "email",
            "id_type",
            "id_number",
            "id_number_hash",
            "organization",
            "is_active",
        ]
        read_only_fields = ["id", "id_number_hash", "is_active"]


class VisitRequestSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=64)
    last_name = serializers.CharField(max_length=64)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    id_type = serializers.ChoiceField(choices=Visitor.ID_TYPES, default="aadhaar")
    id_number = serializers.CharField(max_length=64)
    organization = serializers.CharField(
        max_length=128, required=False, allow_blank=True, default=""
    )

    host_user_id = serializers.IntegerField()
    purpose = serializers.CharField(max_length=255)
    valid_from = serializers.DateTimeField()
    valid_to = serializers.DateTimeField()
    allowed_zones = serializers.ListField(
        child=serializers.CharField(max_length=64), required=False, default=list
    )
    visit_type = serializers.ChoiceField(choices=Visit.VISIT_TYPES, default="pre_registered")
    is_multi_entry = serializers.BooleanField(default=False)


class VisitResponseSerializer(serializers.ModelSerializer):
    visitor = VisitorSerializer(read_only=True)

    class Meta:
        model = Visit
        fields = [
            "id",
            "pass_number",
            "qr_code_hash",
            "visitor",
            "host_user_id",
            "purpose",
            "visit_type",
            "status",
            "valid_from",
            "valid_to",
            "allowed_zones",
            "is_multi_entry",
            "check_in_time",
            "check_out_time",
            "rejection_reason",
            "created_at",
        ]


class VisitRejectRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=False, default="Host unavailable")


class QRScanRequestSerializer(serializers.Serializer):
    qr_code_hash = serializers.CharField(max_length=64)
    gate_name = serializers.CharField(max_length=64, default="Main Gate")
    reader_machine_id = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default=""
    )


class CheckOutRequestSerializer(serializers.Serializer):
    visit_id = serializers.IntegerField()
    gate_name = serializers.CharField(max_length=64, default="Main Gate")


class ZoneVerifyRequestSerializer(serializers.Serializer):
    visit_id = serializers.IntegerField()
    requested_zone = serializers.CharField(max_length=64)


class OfflineEventRecordSerializer(serializers.Serializer):
    qr_code_hash = serializers.CharField(max_length=64)
    action = serializers.ChoiceField(choices=["check_in", "check_out"])
    gate_name = serializers.CharField(max_length=64, default="Main Gate")
    reader_machine_id = serializers.CharField(max_length=64, default="offline_device")


class OfflineSyncRequestSerializer(serializers.Serializer):
    records = serializers.ListField(child=OfflineEventRecordSerializer())


class BlacklistCreateSerializer(serializers.Serializer):
    id_type = serializers.ChoiceField(choices=Visitor.ID_TYPES, default="aadhaar")
    id_number = serializers.CharField(max_length=64)
    full_name = serializers.CharField(max_length=128)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    reason = serializers.CharField(max_length=255)
    severity = serializers.ChoiceField(choices=["info", "warning", "critical"], default="critical")


class BlacklistResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlacklistEntry
        fields = "__all__"


class GateAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = GateAlert
        fields = "__all__"


class EmergencyMusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyMuster
        fields = "__all__"
