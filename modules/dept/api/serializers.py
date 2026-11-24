"""Serializers for Department module."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from modules.dept.models.announcements import Announcement
from modules.dept.models.department import Department
from modules.dept.models.feedback import Feedback
from modules.dept.models.inventory import InventoryItem, StockTransaction
from modules.dept.models.labs import LabResource
from modules.dept.models.official_changes import OfficialDetailChangeRequest
from modules.dept.models.profiles import UserProfileExtension
from modules.dept.models.roles import DepartmentRoleAssignment
from modules.dept.models.stock_requests import StockRequest
from modules.dept.models.timetable import TimetableEntry


class DepartmentSerializer(serializers.ModelSerializer):
    head_of_department_id = serializers.CharField(required=False, allow_null=True)
    department_admin_id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Department
        fields = [
            "code",
            "name",
            "description",
            "core_policies",
            "head_of_department_id",
            "department_admin_id",
            "created_at",
            "updated_at",
        ]


@extend_schema_serializer(component_name="DepartmentAnnouncement")
class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = [
            "id",
            "department",
            "title",
            "content",
            "author_id",
            "author_role",
            "target_role",
            "target_program",
            "target_academic_year",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "author_id", "author_role", "created_at", "updated_at"]


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "department",
            "item_code",
            "name",
            "category",
            "quantity",
            "unit",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StockTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransaction
        fields = [
            "id",
            "inventory_item",
            "transaction_type",
            "quantity_delta",
            "balance_after",
            "performed_by_id",
            "related_request_id",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class StockRequestSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="inventory_item.name", read_only=True)
    item_code = serializers.CharField(source="inventory_item.item_code", read_only=True)

    class Meta:
        model = StockRequest
        fields = [
            "id",
            "department",
            "inventory_item",
            "item_name",
            "item_code",
            "requested_by_id",
            "requested_quantity",
            "purpose",
            "status",
            "hod_decision_by_id",
            "hod_decision_at",
            "hod_remarks",
            "issued_by_id",
            "issued_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "requested_by_id",
            "status",
            "hod_decision_by_id",
            "hod_decision_at",
            "issued_by_id",
            "issued_at",
            "created_at",
            "updated_at",
        ]


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = [
            "id",
            "department",
            "submitted_by_id",
            "submitter_role",
            "category",
            "title",
            "description",
            "status",
            "admin_remarks",
            "reviewed_by_admin_id",
            "reviewed_at",
            "terminal_by_id",
            "terminal_by_role",
            "terminal_remarks",
            "terminal_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "submitted_by_id",
            "submitter_role",
            "status",
            "admin_remarks",
            "reviewed_by_admin_id",
            "reviewed_at",
            "terminal_by_id",
            "terminal_by_role",
            "terminal_remarks",
            "terminal_at",
            "created_at",
            "updated_at",
        ]


class TimetableEntrySerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source="get_day_of_week_display", read_only=True)

    class Meta:
        model = TimetableEntry
        fields = [
            "id",
            "department",
            "program",
            "academic_year",
            "semester",
            "day_of_week",
            "day_name",
            "start_time",
            "end_time",
            "course_code",
            "course_name",
            "instructor_id",
            "room_or_lab",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LabResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabResource
        fields = [
            "id",
            "department",
            "lab_name",
            "location",
            "description",
            "equipment_details",
            "in_charge_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OfficialDetailChangeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficialDetailChangeRequest
        fields = [
            "id",
            "department",
            "proposed_by_id",
            "field_name",
            "old_value",
            "new_value",
            "justification",
            "status",
            "reviewed_by_id",
            "review_reason",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "proposed_by_id",
            "old_value",
            "status",
            "reviewed_by_id",
            "review_reason",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]


class DepartmentRoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentRoleAssignment
        fields = [
            "id",
            "department",
            "role_name",
            "user_id",
            "start_date",
            "end_date",
            "status",
            "assigned_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "assigned_by_id", "created_at", "updated_at"]


class UserProfileExtensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfileExtension
        fields = [
            "id",
            "department",
            "user_id",
            "profile_type",
            "office_room",
            "research_interests",
            "contact_phone",
            "emergency_contact",
            "courses_taught",
            "batch_or_roll",
            "graduation_year",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
