"""Serializers for Hostel Management API."""

from rest_framework import serializers

from modules.hostel.models import (
    AccommodationRequest,
    Hostel,
    HostelComplaint,
    HostelFine,
    HostelNotice,
    LeaveRequest,
    StudentAttendance,
)


class HostelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hostel
        fields = ["id", "name", "code", "description", "is_active", "created_at"]


class AccommodationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccommodationRequest
        fields = [
            "id",
            "user_id",
            "preferred_hostel",
            "academic_year",
            "status",
            "remarks",
            "created_at",
        ]
        read_only_fields = ["user_id", "status", "created_at"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "hostel",
            "start_date",
            "end_date",
            "reason",
            "status",
            "action_remarks",
            "created_at",
        ]
        read_only_fields = ["user_id", "status", "created_at"]


class HostelComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelComplaint
        fields = [
            "id",
            "user_id",
            "hostel",
            "category",
            "title",
            "description",
            "status",
            "resolution_remarks",
            "created_at",
        ]
        read_only_fields = ["user_id", "status", "created_at"]


class StudentAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAttendance
        fields = ["id", "user_id", "hostel", "date", "status", "marked_by_user_id"]
        read_only_fields = ["marked_by_user_id"]


class HostelFineSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelFine
        fields = [
            "id",
            "user_id",
            "hostel",
            "amount",
            "reason",
            "status",
            "imposed_by_user_id",
            "created_at",
        ]
        read_only_fields = ["imposed_by_user_id", "created_at"]


class HostelNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelNotice
        fields = [
            "id",
            "hostel",
            "title",
            "body",
            "topic",
            "published_by_user_id",
            "published_by_role",
            "created_at",
        ]
        read_only_fields = ["published_by_user_id", "published_by_role", "created_at"]
