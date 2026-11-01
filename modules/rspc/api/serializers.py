"""RSPC DRF Serializers."""

from rest_framework import serializers

from modules.rspc.models import (
    ConsultancyMilestoneSettlement,
    ConsultancyProject,
    ExternalAgencyTracking,
    FinancialRequest,
    ProcurementRequest,
    ProgressReport,
    ProjectClosureRecord,
    ResearchProposal,
    RSPCAuditTrail,
    RSPCNotification,
    RSPCProject,
    RSPCRoleSynchronizationLog,
    StaffAppointmentRequest,
)


class ResearchProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchProposal
        fields = "__all__"
        read_only_fields = ("id", "status", "created_at", "updated_at")


class ResearchProposalCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchProposal
        fields = (
            "title",
            "department_id",
            "objectives",
            "funding_agency",
            "duration_months",
            "budget_amount",
            "resource_requirements",
            "is_strategic",
            "start_date",
            "end_date",
        )


class ConsultancyProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultancyProject
        fields = "__all__"
        read_only_fields = ("id", "status", "created_at", "updated_at")


class ConsultancyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultancyProject
        fields = (
            "title",
            "department_id",
            "client_name",
            "client_details",
            "scope",
            "deliverables",
            "duration_months",
            "budget_amount",
            "financial_terms",
            "requires_hod_review",
            "is_strategic",
            "start_date",
            "end_date",
        )


class ConsultancySettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultancyMilestoneSettlement
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class RSPCProjectSerializer(serializers.ModelSerializer):
    available_budget = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = RSPCProject
        fields = "__all__"
        read_only_fields = ("id", "project_code", "created_at", "updated_at", "archived_at")


class ProjectUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RSPCProject
        fields = ("milestones", "progress_info")


class StaffAppointmentRequestSerializer(serializers.ModelSerializer):
    project_code = serializers.CharField(source="project.project_code", read_only=True)

    class Meta:
        model = StaffAppointmentRequest
        fields = "__all__"
        read_only_fields = ("id", "status", "created_at", "updated_at")


class StaffAppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffAppointmentRequest
        fields = (
            "project",
            "position_title",
            "stipend_amount",
            "duration_months",
            "advertisement_details",
        )


class FinancialRequestSerializer(serializers.ModelSerializer):
    project_code = serializers.CharField(source="project.project_code", read_only=True)

    class Meta:
        model = FinancialRequest
        fields = "__all__"
        read_only_fields = ("id", "status", "created_at", "updated_at")


class FinancialRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialRequest
        fields = ("project", "request_type", "amount", "budget_head", "description")


class ProcurementRequestSerializer(serializers.ModelSerializer):
    project_code = serializers.CharField(source="project.project_code", read_only=True)

    class Meta:
        model = ProcurementRequest
        fields = "__all__"
        read_only_fields = ("id", "status", "created_at", "updated_at", "budget_validation_passed")


class ProcurementRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementRequest
        fields = (
            "project",
            "item_type",
            "item_name",
            "quantity",
            "estimated_cost",
            "specifications",
        )


class ProgressReportSerializer(serializers.ModelSerializer):
    project_code = serializers.CharField(source="project.project_code", read_only=True)

    class Meta:
        model = ProgressReport
        fields = "__all__"
        read_only_fields = ("id", "status", "created_at", "updated_at")


class ProgressReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressReport
        fields = (
            "project",
            "report_type",
            "period_start",
            "period_end",
            "summary",
            "expenditure_reported",
        )


class ProjectClosureRecordSerializer(serializers.ModelSerializer):
    project_code = serializers.CharField(source="project.project_code", read_only=True)

    class Meta:
        model = ProjectClosureRecord
        fields = "__all__"
        read_only_fields = (
            "id",
            "status",
            "settlement_verified",
            "assets_verified",
            "created_at",
            "updated_at",
        )


class ProjectClosureCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectClosureRecord
        fields = (
            "project",
            "completion_report",
            "financial_settlement_record",
            "asset_declaration_record",
        )


class TransitionActionSerializer(serializers.Serializer):
    to_status = serializers.CharField(max_length=64)
    remarks = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    is_eligible = serializers.BooleanField(required=False, default=True)
    recommendation = serializers.CharField(
        max_length=1000, required=False, allow_blank=True, default=""
    )
    recommended_candidate_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    settlement_verified = serializers.BooleanField(required=False, default=True)
    assets_verified = serializers.BooleanField(required=False, default=True)


class RSPCAuditTrailSerializer(serializers.ModelSerializer):
    class Meta:
        model = RSPCAuditTrail
        fields = "__all__"
        read_only_fields = ("id", "timestamp")


class RSPCNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RSPCNotification
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ExternalAgencyTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalAgencyTracking
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class RSPCRoleSyncSerializer(serializers.ModelSerializer):
    class Meta:
        model = RSPCRoleSynchronizationLog
        fields = "__all__"
        read_only_fields = ("id", "synchronized_at")


class IntegrationExchangeSerializer(serializers.Serializer):
    source_module = serializers.CharField(max_length=64, default="external")
    payload = serializers.DictField(default=dict)
