from rest_framework import serializers

from modules.oap.models.bonafide import BonafideRequest
from modules.oap.models.branch_change import BranchChangeRequest
from modules.oap.models.leave import StudentLeaveRequest
from modules.oap.models.nodues import NoDuesDepartmentalSignoff, NoDuesRequest


class StudentLeaveRequestSerializer(serializers.ModelSerializer):
    duration_days = serializers.ReadOnlyField()

    class Meta:
        model = StudentLeaveRequest
        fields = [
            "id",
            "student_id",
            "student_name",
            "leave_type",
            "start_date",
            "end_date",
            "duration_days",
            "reason",
            "status",
            "supervisor_id",
            "supervisor_remarks",
            "hod_id",
            "hod_remarks",
            "document_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "supervisor_id",
            "supervisor_remarks",
            "hod_id",
            "hod_remarks",
            "created_at",
            "updated_at",
        ]


class BonafideRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonafideRequest
        fields = [
            "id",
            "student_id",
            "purpose",
            "details",
            "status",
            "certificate_number",
            "issued_at",
            "issued_by",
            "rejection_reason",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "certificate_number",
            "issued_at",
            "issued_by",
            "rejection_reason",
            "created_at",
        ]


class NoDuesDepartmentalSignoffSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoDuesDepartmentalSignoff
        fields = [
            "id",
            "department",
            "status",
            "dues_amount",
            "remarks",
            "signoff_by",
            "signoff_at",
        ]
        read_only_fields = ["id", "signoff_at"]


class NoDuesRequestSerializer(serializers.ModelSerializer):
    signoffs = NoDuesDepartmentalSignoffSerializer(many=True, read_only=True)

    class Meta:
        model = NoDuesRequest
        fields = [
            "id",
            "student_id",
            "reason",
            "overall_status",
            "clearance_certificate_number",
            "completed_at",
            "finalized_by",
            "created_at",
            "signoffs",
        ]
        read_only_fields = [
            "id",
            "overall_status",
            "clearance_certificate_number",
            "completed_at",
            "finalized_by",
            "created_at",
        ]


class BranchChangeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BranchChangeRequest
        fields = [
            "id",
            "student_id",
            "current_branch",
            "preferred_branch_1",
            "preferred_branch_2",
            "current_cpi",
            "credits_completed",
            "has_backlogs",
            "status",
            "allocated_branch",
            "approved_by",
            "remarks",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "allocated_branch",
            "approved_by",
            "remarks",
            "created_at",
        ]
