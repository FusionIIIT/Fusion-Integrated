"""Serializers. Read serializers are fully read-only; every write goes through
an explicit allow-list serializer, so `status`, `student_id`, `department` and
every `*_by_id` / `*_at` / `certificate_number` can never be set by a client.
"""
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.oap.models import (
    AssistantshipClaim,
    BonafideRequest,
    CaseEvent,
    LeaveApplication,
    NoDuesClearance,
    NoDuesRequest,
    SeminarRequest,
    SupervisorAssignment,
    SupervisorVerification,
    TAAssignment,
)
from modules.oap.services import assistantship as assistantship_service
from modules.oap.services import bonafide as bonafide_service
from modules.oap.services import leave as leave_service
from modules.oap.services import nodues as nodues_service


# -- History -------------------------------------------------------------------
class CaseEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseEvent
        fields = (
            "from_state", "to_state", "action", "actor_id", "remark", "created_at",
        )
        read_only_fields = fields


def _history(case_type, obj):
    events = CaseEvent.objects.filter(case_type=case_type, case_id=obj.id)
    return CaseEventSerializer(events, many=True).data


# -- Decisions (shared) --------------------------------------------------------
class DecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    remark = serializers.CharField(required=False, allow_blank=True, default="")


# -- Leave ---------------------------------------------------------------------
class LeaveSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = LeaveApplication
        fields = (
            "id", "student_id", "department", "status", "start_date", "end_date",
            "reason", "supporting_document", "decided_by_id", "decided_at",
            "decision_remark", "created_at", "updated_at",
        )
        read_only_fields = fields


class LeaveDetailSerializer(LeaveSerializer):
    history = serializers.SerializerMethodField()

    class Meta(LeaveSerializer.Meta):
        fields = (*LeaveSerializer.Meta.fields, "history")
        read_only_fields = fields

    @extend_schema_field(CaseEventSerializer(many=True))
    def get_history(self, obj):
        return _history(leave_service.CASE_TYPE, obj)


class LeaveSubmitSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    supporting_document = serializers.FileField(required=False)


# -- Bonafide ------------------------------------------------------------------
class BonafideSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = BonafideRequest
        fields = (
            "id", "student_id", "department", "status", "purpose", "decided_by_id",
            "decided_at", "decision_remark", "certificate_number", "created_at",
            "updated_at",
        )
        read_only_fields = fields


class BonafideDetailSerializer(BonafideSerializer):
    history = serializers.SerializerMethodField()

    class Meta(BonafideSerializer.Meta):
        fields = (*BonafideSerializer.Meta.fields, "history")
        read_only_fields = fields

    @extend_schema_field(CaseEventSerializer(many=True))
    def get_history(self, obj):
        return _history(bonafide_service.CASE_TYPE, obj)


class BonafideSubmitSerializer(serializers.Serializer):
    purpose = serializers.CharField(max_length=200, required=False, allow_blank=True,
                                    default="")


class BonafideCertificateSerializer(serializers.Serializer):
    certificate_number = serializers.CharField()
    student_id = serializers.IntegerField()
    purpose = serializers.CharField(allow_blank=True)
    issued_on = serializers.DateField(allow_null=True)


# -- Seminar -------------------------------------------------------------------
class SeminarSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = SeminarRequest
        fields = (
            "id", "student_id", "department", "status", "scheduled_at", "venue",
            "scheduled_by_id", "created_at", "updated_at",
        )
        read_only_fields = fields


class SeminarScheduleSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField()
    venue = serializers.CharField(max_length=200, required=False, allow_blank=True,
                                  default="")


# -- No-dues -------------------------------------------------------------------
class NoDuesClearanceSerializer(serializers.ModelSerializer):
    domain_code = serializers.CharField(read_only=True)
    result = serializers.CharField(read_only=True)

    class Meta:
        model = NoDuesClearance
        fields = ("domain_code", "result", "remark", "recorded_at")
        read_only_fields = fields


class NoDuesSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = NoDuesRequest
        fields = (
            "id", "student_id", "department", "status", "finalized_by_id",
            "finalized_at", "certificate_number", "created_at", "updated_at",
        )
        read_only_fields = fields


class NoDuesWithClearancesSerializer(NoDuesSerializer):
    clearances = serializers.SerializerMethodField()

    class Meta(NoDuesSerializer.Meta):
        fields = (*NoDuesSerializer.Meta.fields, "clearances")
        read_only_fields = fields

    @extend_schema_field(NoDuesClearanceSerializer(many=True))
    def get_clearances(self, obj):
        rows = sorted(obj.clearances.all(), key=lambda c: c.id)
        return NoDuesClearanceSerializer(rows, many=True).data


class NoDuesDetailSerializer(NoDuesWithClearancesSerializer):
    history = serializers.SerializerMethodField()

    class Meta(NoDuesWithClearancesSerializer.Meta):
        fields = (*NoDuesWithClearancesSerializer.Meta.fields, "history")
        read_only_fields = fields

    @extend_schema_field(CaseEventSerializer(many=True))
    def get_history(self, obj):
        return _history(nodues_service.CASE_TYPE, obj)


class NoDuesClearanceInputSerializer(serializers.Serializer):
    result = serializers.CharField()  # the service validates the value
    remark = serializers.CharField(required=False, allow_blank=True, default="")


class NoDuesCertificateSerializer(serializers.Serializer):
    certificate_number = serializers.CharField()
    student_id = serializers.IntegerField()
    issued_on = serializers.DateField(allow_null=True)


# -- Assistantship -------------------------------------------------------------
class SupervisorVerificationSerializer(serializers.ModelSerializer):
    role = serializers.CharField(read_only=True)

    class Meta:
        model = SupervisorVerification
        fields = ("role", "verified_by_id", "created_at")
        read_only_fields = fields


class AssistantshipSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = AssistantshipClaim
        fields = (
            "id", "student_id", "department", "status", "claim_period",
            "thesis_supervisor_id", "ta_supervisor_id",
            "department_reviewed_by_id", "decided_by_id",
            "stipend_processed_by_id", "decided_at", "decision_remark",
            "created_at", "updated_at",
        )
        read_only_fields = fields


class AssistantshipDetailSerializer(AssistantshipSerializer):
    verifications = serializers.SerializerMethodField()
    history = serializers.SerializerMethodField()

    class Meta(AssistantshipSerializer.Meta):
        fields = (*AssistantshipSerializer.Meta.fields, "verifications", "history")
        read_only_fields = fields

    @extend_schema_field(SupervisorVerificationSerializer(many=True))
    def get_verifications(self, obj):
        rows = obj.verifications.order_by("created_at", "id")
        return SupervisorVerificationSerializer(rows, many=True).data

    @extend_schema_field(CaseEventSerializer(many=True))
    def get_history(self, obj):
        return _history(assistantship_service.CASE_TYPE, obj)


class ClaimSubmitSerializer(serializers.Serializer):
    claim_period = serializers.CharField(max_length=20, required=False,
                                         allow_blank=True, default="")


class ClaimVerifySerializer(serializers.Serializer):
    role = serializers.CharField()  # the service validates the value
    remark = serializers.CharField(required=False, allow_blank=True, default="")


class RemarkSerializer(serializers.Serializer):
    remark = serializers.CharField(required=False, allow_blank=True, default="")


# -- Records -------------------------------------------------------------------
class SupervisorAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupervisorAssignment
        fields = (
            "id", "student_id", "faculty_id", "assigned_by_id",
            "decision_reference", "created_at", "updated_at",
        )
        read_only_fields = fields


class SupervisorAssignmentWriteSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    faculty_id = serializers.IntegerField()
    decision_reference = serializers.CharField(max_length=200, required=False,
                                               allow_blank=True, default="")


class TAAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TAAssignment
        fields = (
            "id", "student_id", "course_code", "faculty_id", "assigned_by_id",
            "created_at",
        )
        read_only_fields = fields


class TAAssignmentWriteSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    course_code = serializers.CharField(max_length=20, required=False,
                                        allow_blank=True, default="")
    faculty_id = serializers.IntegerField(required=False, allow_null=True,
                                          default=None)
