from rest_framework import serializers

from modules.department.models import (
    Announcement,
    Department,
    DepartmentDetail,
    DepartmentDetailChange,
    DepartmentProfile,
    Feedback,
    InventoryItem,
    LabResource,
    StockRequest,
    Timetable,
    TimetableSlot,
)


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = [
            "id",
            "code",
            "name",
            "description",
            "head_user_id",
            "admin_user_id",
            "created_at",
            "updated_at",
        ]


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = [
            "id",
            "department",
            "title",
            "body",
            "academic_year",
            "programme",
            "role_target",
            "is_hidden",
            "created_by_user_id",
            "created_at",
        ]


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ["id", "department", "name", "quantity", "unit", "created_at", "updated_at"]


class StockRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockRequest
        fields = [
            "id",
            "department",
            "item",
            "requester_user_id",
            "quantity",
            "status",
            "approved_by_user_id",
            "issued_by_user_id",
            "created_at",
        ]


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = [
            "id",
            "department",
            "submitter_user_id",
            "subject",
            "body",
            "category",
            "status",
            "created_at",
        ]


class DepartmentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentProfile
        fields = [
            "id",
            "department",
            "user_id",
            "display_name",
            "kind",
            "programme",
            "discipline",
            "batch_year",
            "notes",
        ]


class TimetableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timetable
        fields = [
            "id",
            "department",
            "title",
            "academic_year",
            "programme",
            "uploaded_by_user_id",
            "created_at",
        ]


class TimetableSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimetableSlot
        fields = [
            "id",
            "timetable",
            "day",
            "start_time",
            "end_time",
            "subject",
            "faculty_user_id",
            "room",
        ]


class LabResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabResource
        fields = [
            "id",
            "department",
            "name",
            "description",
            "quantity",
            "updated_by_user_id",
            "created_at",
        ]


class DepartmentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentDetail
        fields = ["id", "department", "name", "core_policies", "head_user_id"]


class DepartmentDetailChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentDetailChange
        fields = [
            "id",
            "department",
            "field_name",
            "proposed_value",
            "status",
            "proposed_by_user_id",
            "decided_by_user_id",
            "created_at",
        ]
