"""DRF serializers for VMS."""
from rest_framework import serializers
from modules.vms.models import (
    Visitor,
    Host,
    VisitRequest,
    HostDecision,
    VisitorPass,
    VisitLog,
    CampusGate,
    BlacklistRegistry,
)


class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = ["visitor_id", "full_name", "email", "phone", "id_document_type", "id_document_number", "organization"]


class HostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Host
        fields = ["host_id", "user_id", "employee_id", "full_name", "department", "designation", "email", "office_location"]


class VisitRequestSerializer(serializers.ModelSerializer):
    visitor = VisitorSerializer(read_only=True)
    host = HostSerializer(read_only=True)

    class Meta:
        model = VisitRequest
        fields = [
            "request_id",
            "visitor",
            "host",
            "purpose",
            "scheduled_start_time",
            "scheduled_end_time",
            "status",
            "submission_timestamp",
            "remarks",
        ]


class PreRegisterInputSerializer(serializers.Serializer):
    visitor_name = serializers.CharField(max_length=120)
    visitor_phone = serializers.CharField(max_length=20)
    visitor_email = serializers.EmailField()
    id_doc_type = serializers.CharField(max_length=40, default="AADHAAR")
    id_doc_number = serializers.CharField(max_length=64)
    organization = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    host_id = serializers.IntegerField()
    purpose = serializers.CharField(max_length=255)
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class HostDecisionInputSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    allowed_start = serializers.DateTimeField(required=False, allow_null=True)
    allowed_end = serializers.DateTimeField(required=False, allow_null=True)
    permitted_zones = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    special_instructions = serializers.CharField(required=False, allow_blank=True, default="")


class VisitorPassSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source="request.visitor.full_name", read_only=True)
    host_name = serializers.CharField(source="request.host.full_name", read_only=True)

    class Meta:
        model = VisitorPass
        fields = [
            "pass_id",
            "request_id",
            "visitor_name",
            "host_name",
            "pass_type",
            "credential_data",
            "valid_from",
            "valid_until",
            "status",
            "permitted_zones",
        ]


class GateValidationInputSerializer(serializers.Serializer):
    credential_data = serializers.CharField(max_length=128)
    gate_id = serializers.CharField(max_length=32)
    verifier_notes = serializers.CharField(required=False, allow_blank=True, default="")


class GateCheckoutInputSerializer(serializers.Serializer):
    pass_id = serializers.CharField(max_length=32)
    gate_id = serializers.CharField(max_length=32)
    verifier_notes = serializers.CharField(required=False, allow_blank=True, default="")


class VisitLogSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source="visitor_pass.request.visitor.full_name", read_only=True)
    entry_gate_name = serializers.CharField(source="entry_gate.gate_name", read_only=True)
    exit_gate_name = serializers.CharField(source="exit_gate.gate_name", read_only=True, allow_null=True)

    class Meta:
        model = VisitLog
        fields = [
            "log_id",
            "visitor_pass_id",
            "visitor_name",
            "entry_gate_id",
            "entry_gate_name",
            "exit_gate_id",
            "exit_gate_name",
            "check_in_time",
            "check_out_time",
            "status",
            "verifier_notes",
        ]


class CampusGateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampusGate
        fields = ["gate_id", "gate_name", "gate_type", "location_zone", "is_operational"]
