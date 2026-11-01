"""RSPC API serializers."""
from rest_framework import serializers

from modules.rspc.models import (
    ResearchProject, ConsultancyProject, StaffAppointment,
    FinanceRequest, ProcurementRequest, ProgressReport, ProjectClosure,
    ResearchProjectTransition, ConsultancyTransition, AppointmentTransition,
    FinanceTransition, ProcurementTransition, ProgressReportTransition,
    ClosureTransition,
)


# ---------------------------------------------------------------------------
# Research Project Proposal
# ---------------------------------------------------------------------------

class ResearchProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchProject
        fields = [
            "id", "user_id", "title", "objectives", "funding_source",
            "budget_requested", "start_date", "end_date",
            "resource_requirements", "department", "status",
            "hod_remarks", "admin_remarks", "dean_remarks", "director_remarks",
            "submitted_at", "hod_decided_at", "admin_verified_at",
            "dean_decided_at", "director_decided_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user_id", "status",
            "hod_remarks", "admin_remarks", "dean_remarks", "director_remarks",
            "submitted_at", "hod_decided_at", "admin_verified_at",
            "dean_decided_at", "director_decided_at",
            "created_at", "updated_at",
        ]


class WriteResearchProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchProject
        fields = [
            "title", "objectives", "funding_source", "budget_requested",
            "start_date", "end_date", "resource_requirements", "department",
        ]


class ResearchProjectTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchProjectTransition
        fields = ["id", "from_status", "to_status", "actor_user_id",
                  "remarks", "at"]


class TransitionRequestSerializer(serializers.Serializer):
    to_status = serializers.CharField()
    remarks   = serializers.CharField(required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Consultancy Project
# ---------------------------------------------------------------------------

class ConsultancyProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultancyProject
        fields = [
            "id", "user_id", "title", "client_name", "client_details",
            "scope", "deliverables", "financial_terms", "total_amount",
            "start_date", "end_date", "department", "status",
            "hod_remarks", "admin_remarks", "dean_remarks", "director_remarks",
            "submitted_at", "hod_decided_at", "admin_verified_at",
            "dean_decided_at", "director_decided_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user_id", "status",
            "hod_remarks", "admin_remarks", "dean_remarks", "director_remarks",
            "submitted_at", "hod_decided_at", "admin_verified_at",
            "dean_decided_at", "director_decided_at",
            "created_at", "updated_at",
        ]


class WriteConsultancySerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultancyProject
        fields = [
            "title", "client_name", "client_details", "scope", "deliverables",
            "financial_terms", "total_amount", "start_date", "end_date",
            "department",
        ]


# ---------------------------------------------------------------------------
# Staff Appointment
# ---------------------------------------------------------------------------

class StaffAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffAppointment
        fields = [
            "id", "user_id", "project", "position_title", "stipend_amount",
            "duration_months", "department", "status",
            "admin_remarks", "dean_remarks", "director_remarks",
            "selection_remarks",
            "submitted_at", "admin_verified_at", "dean_decided_at",
            "director_decided_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user_id", "status",
            "admin_remarks", "dean_remarks", "director_remarks",
            "selection_remarks",
            "submitted_at", "admin_verified_at", "dean_decided_at",
            "director_decided_at",
            "created_at", "updated_at",
        ]


class WriteStaffAppointmentSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = StaffAppointment
        fields = [
            "project_id", "position_title", "stipend_amount",
            "duration_months", "department",
        ]


# ---------------------------------------------------------------------------
# Financial Request
# ---------------------------------------------------------------------------

class FinanceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinanceRequest
        fields = [
            "id", "user_id", "project", "category", "description", "amount",
            "purpose", "status",
            "admin_remarks", "dean_remarks", "director_remarks",
            "submitted_at", "admin_verified_at", "dean_decided_at",
            "director_decided_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user_id", "status",
            "admin_remarks", "dean_remarks", "director_remarks",
            "submitted_at", "admin_verified_at", "dean_decided_at",
            "director_decided_at",
            "created_at", "updated_at",
        ]


class WriteFinanceRequestSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = FinanceRequest
        fields = ["project_id", "category", "description", "amount", "purpose"]


# ---------------------------------------------------------------------------
# Procurement Request
# ---------------------------------------------------------------------------

class ProcurementRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementRequest
        fields = [
            "id", "user_id", "project", "item_description", "quantity",
            "estimated_cost", "justification", "status",
            "admin_remarks", "dean_remarks", "director_remarks",
            "submitted_at", "admin_verified_at", "dean_decided_at",
            "director_decided_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user_id", "status",
            "admin_remarks", "dean_remarks", "director_remarks",
            "submitted_at", "admin_verified_at", "dean_decided_at",
            "director_decided_at",
            "created_at", "updated_at",
        ]


class WriteProcurementSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = ProcurementRequest
        fields = [
            "project_id", "item_description", "quantity",
            "estimated_cost", "justification",
        ]


# ---------------------------------------------------------------------------
# Progress Report
# ---------------------------------------------------------------------------

class ProgressReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressReport
        fields = [
            "id", "user_id", "project", "reporting_period", "summary",
            "milestones_achieved", "expenditure_so_far", "status",
            "reviewer_remarks", "submitted_at", "reviewed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user_id", "status",
            "reviewer_remarks", "submitted_at", "reviewed_at",
            "created_at", "updated_at",
        ]


class WriteProgressReportSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField()

    class Meta:
        model = ProgressReport
        fields = [
            "project_id", "reporting_period", "summary",
            "milestones_achieved", "expenditure_so_far",
        ]


# ---------------------------------------------------------------------------
# Project Closure
# ---------------------------------------------------------------------------

class ProjectClosureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectClosure
        fields = [
            "id", "user_id", "project", "completion_summary",
            "financial_settlement_details", "assets_declared", "status",
            "admin_remarks", "dean_remarks",
            "submitted_at", "admin_verified_at", "dean_decided_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user_id", "status",
            "admin_remarks", "dean_remarks",
            "submitted_at", "admin_verified_at", "dean_decided_at",
            "created_at", "updated_at",
        ]


class WriteProjectClosureSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField()

    class Meta:
        model = ProjectClosure
        fields = [
            "project_id", "completion_summary",
            "financial_settlement_details", "assets_declared",
        ]
