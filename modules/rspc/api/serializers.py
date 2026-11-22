"""DRF Serializers for RSPC module."""
from __future__ import annotations

from rest_framework import serializers

from modules.rspc.domain.rules import (
    validate_consultancy_project,
    validate_research_proposal,
)
from modules.rspc.models import (
    ConsultancyProject,
    FinancialRequest,
    ProcurementRequest,
    ProgressReport,
    ProjectClosure,
    ProjectStaffAppointment,
    ResearchProposal,
    RSPCAuditTrail,
)


class ResearchProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchProposal
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        # Validate through domain rules
        instance = getattr(self, "instance", None)
        merged = {}
        if instance:
            merged = {
                "title": instance.title,
                "pi_id": instance.pi_id,
                "department": instance.department,
                "funding_agency": instance.funding_agency,
                "budget": instance.budget,
                "objectives": instance.objectives,
                "start_date": instance.start_date,
                "end_date": instance.end_date,
                "timeline_months": instance.timeline_months,
            }
        merged.update(attrs)
        errors = validate_research_proposal(merged)
        if errors:
            raise serializers.ValidationError({"detail": errors})
        return attrs


class ConsultancyProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultancyProject
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        merged = {}
        if instance:
            merged = {
                "title": instance.title,
                "pi_id": instance.pi_id,
                "client_name": instance.client_name,
                "scope_of_work": instance.scope_of_work,
                "deliverables": instance.deliverables,
                "total_cost": instance.total_cost,
                "institutional_share": instance.institutional_share,
            }
        merged.update(attrs)
        errors = validate_consultancy_project(merged)
        if errors:
            raise serializers.ValidationError({"detail": errors})
        return attrs


class ProjectStaffAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStaffAppointment
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class FinancialRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialRequest
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ProcurementRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementRequest
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ProgressReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressReport
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class ProjectClosureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectClosure
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class RSPCAuditTrailSerializer(serializers.ModelSerializer):
    class Meta:
        model = RSPCAuditTrail
        fields = "__all__"
        read_only_fields = ("id", "timestamp")
