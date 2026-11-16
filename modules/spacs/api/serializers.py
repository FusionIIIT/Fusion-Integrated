"""Serializers for SPACS module."""

from rest_framework import serializers

from modules.spacs.models import (
    SpacsApplication,
    SpacsAuditLog,
    SpacsAwardCandidate,
    SpacsAwardCycle,
    SpacsCatalogueEntry,
    SpacsNotification,
    SpacsTask,
)


class SchemeSerializer(serializers.ModelSerializer):
    """Serializer for award/scholarship scheme catalogue."""

    class Meta:
        model = SpacsCatalogueEntry
        fields = [
            "id",
            "scheme_code",
            "name",
            "scheme_type",
            "description",
            "status",
            "min_cpi",
            "max_family_income",
            "academic_cycle",
            "version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SchemeCreateSerializer(serializers.Serializer):
    """Input serializer for scheme creation."""

    scheme_code = serializers.CharField(max_length=64)
    name = serializers.CharField(max_length=255)
    scheme_type = serializers.ChoiceField(
        choices=[("scholarship", "Scholarship"), ("award", "Award")]
    )
    description = serializers.CharField(required=False, allow_blank=True, default="")
    min_cpi = serializers.DecimalField(max_digits=4, decimal_places=2, required=False, default=0.0)
    max_family_income = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    academic_cycle = serializers.CharField(max_length=32, required=False, default="2026-27")


class CycleSerializer(serializers.ModelSerializer):
    """Serializer for award cycle instances."""

    class Meta:
        model = SpacsAwardCycle
        fields = [
            "id",
            "catalogue_entry_id",
            "academic_cycle",
            "state",
            "criteria_version",
            "approval_evidence",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CycleCreateSerializer(serializers.Serializer):
    """Input serializer for opening an award cycle."""

    scheme_code = serializers.CharField(max_length=64)
    academic_cycle = serializers.CharField(max_length=32)


class SpacsApplicationSerializer(serializers.ModelSerializer):
    """Serializer for student applications."""

    class Meta:
        model = SpacsApplication
        fields = [
            "id",
            "application_id",
            "catalogue_entry_id",
            "applicant_user_id",
            "academic_cycle",
            "is_renewal",
            "state",
            "cpi",
            "family_income",
            "submitted_at",
            "verification_findings",
            "correction_reason",
            "decision_reason",
            "decision_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "application_id",
            "applicant_user_id",
            "state",
            "submitted_at",
            "decision_at",
            "created_at",
            "updated_at",
        ]


ApplicationSerializer = SpacsApplicationSerializer


class ApplicationCreateSerializer(serializers.Serializer):
    """Input serializer for submitting an application."""

    scheme_code = serializers.CharField(max_length=64)
    academic_cycle = serializers.CharField(max_length=32)
    cpi = serializers.DecimalField(max_digits=4, decimal_places=2)
    family_income = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    documents = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class ApplicationAmendSerializer(serializers.Serializer):
    """Input serializer for amending a pending application."""

    cpi = serializers.DecimalField(max_digits=4, decimal_places=2, required=False)
    family_income = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    documents = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class VerificationActionSerializer(serializers.Serializer):
    """Input serializer for verification decision."""

    action = serializers.ChoiceField(choices=["verify", "defect"])
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class DecisionActionSerializer(serializers.Serializer):
    """Input serializer for convener decision."""

    application_id = serializers.CharField(max_length=64)
    outcome = serializers.ChoiceField(choices=["approved", "rejected"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class RenewalCreateSerializer(serializers.Serializer):
    """Input serializer for submitting renewal."""

    previous_application_id = serializers.CharField(max_length=64, required=False)
    parent_application_id = serializers.CharField(max_length=64, required=False)
    academic_cycle = serializers.CharField(max_length=32, required=False, default="2026-27")
    cpi = serializers.DecimalField(max_digits=4, decimal_places=2, required=False, default=8.0)
    family_income = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )

    def validate(self, attrs):
        if not attrs.get("previous_application_id") and not attrs.get("parent_application_id"):
            msg = "Either previous_application_id or parent_application_id is required."
            raise serializers.ValidationError(msg)
        return attrs


class AwardCandidateSerializer(serializers.ModelSerializer):
    """Serializer for award candidates."""

    class Meta:
        model = SpacsAwardCandidate
        fields = [
            "id",
            "award_cycle",
            "student_user_id",
            "cpi",
            "academic_standing",
            "shortlisted",
            "evaluation_score",
            "committee_recommendation",
            "remarks",
        ]
        read_only_fields = ["id"]


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for workflow and SLA tasks."""

    class Meta:
        model = SpacsTask
        fields = [
            "id",
            "task_type",
            "entity_type",
            "entity_id",
            "assigned_role",
            "assigned_user_id",
            "status",
            "due_at",
            "created_at",
        ]
        read_only_fields = ["id"]


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications."""

    class Meta:
        model = SpacsNotification
        fields = [
            "id",
            "recipient_user_id",
            "event_type",
            "message",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id"]


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit logs."""

    class Meta:
        model = SpacsAuditLog
        fields = [
            "id",
            "event_type",
            "entity_type",
            "entity_id",
            "actor_user_id",
            "details",
            "timestamp",
        ]
        read_only_fields = ["id"]
