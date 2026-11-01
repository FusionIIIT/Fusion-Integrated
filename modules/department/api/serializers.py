"""DRF Serializers for Department module."""
from __future__ import annotations

from rest_framework import serializers
from modules.department.models.seminar import (
    SeminarSchedulingRequest,
    GraduateSeminar,
    SeminarSchedulingHistory,
)
from modules.department.models.allocation import (
    ThesisSupervisorAllocation,
    TAAllocation,
)
from modules.department.models.announcement import DepartmentAnnouncement


class SeminarSchedulingHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SeminarSchedulingHistory
        fields = [
            "id",
            "seminar_id",
            "action",
            "details",
            "recorded_by_id",
            "recorded_by_name",
            "created_at",
        ]
        read_only_fields = fields


class GraduateSeminarSerializer(serializers.ModelSerializer):
    history_logs = SeminarSchedulingHistorySerializer(many=True, read_only=True)

    class Meta:
        model = GraduateSeminar
        fields = [
            "id",
            "request_id",
            "title",
            "speaker_id",
            "speaker_name",
            "scheduled_date",
            "start_time",
            "end_time",
            "venue",
            "session_chair",
            "remarks",
            "scheduled_by_id",
            "scheduled_by_name",
            "created_at",
            "history_logs",
        ]
        read_only_fields = fields


class SeminarRequestSerializer(serializers.ModelSerializer):
    seminar = GraduateSeminarSerializer(read_only=True)

    class Meta:
        model = SeminarSchedulingRequest
        fields = [
            "id",
            "student_id",
            "student_name",
            "programme",
            "department",
            "topic",
            "abstract",
            "preferred_date",
            "faculty_advisor_id",
            "faculty_advisor_name",
            "status",
            "rejection_reason",
            "seminar",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SeminarRequestCreateSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=255)
    abstract = serializers.CharField()
    programme = serializers.CharField(max_length=60, default="M.Tech")
    department = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    preferred_date = serializers.DateField(required=False, allow_null=True, default=None)
    faculty_advisor_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    faculty_advisor_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")


class GraduateSeminarScheduleSerializer(serializers.Serializer):
    scheduled_date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    venue = serializers.CharField(max_length=100)
    session_chair = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SeminarRejectSerializer(serializers.Serializer):
    reason = serializers.CharField()


class ThesisSupervisorAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThesisSupervisorAllocation
        fields = [
            "id",
            "student_id",
            "student_name",
            "programme",
            "department",
            "supervisor_id",
            "supervisor_name",
            "co_supervisor_name",
            "thesis_topic",
            "academic_year",
            "status",
            "created_at",
        ]


class ThesisSupervisorAllocationCreateSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_name = serializers.CharField(max_length=150)
    programme = serializers.CharField(max_length=60, default="M.Tech")
    department = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    supervisor_id = serializers.IntegerField()
    supervisor_name = serializers.CharField(max_length=150)
    co_supervisor_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    thesis_topic = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    academic_year = serializers.CharField(max_length=20, default="2026-27")


class TAAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TAAllocation
        fields = [
            "id",
            "student_id",
            "student_name",
            "programme",
            "department",
            "course_code",
            "course_name",
            "faculty_id",
            "faculty_name",
            "semester",
            "academic_year",
            "hours_per_week",
            "created_at",
        ]


class TAAllocationCreateSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_name = serializers.CharField(max_length=150)
    course_code = serializers.CharField(max_length=20)
    course_name = serializers.CharField(max_length=150)
    faculty_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    faculty_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    programme = serializers.CharField(max_length=60, default="M.Tech")
    semester = serializers.CharField(max_length=20, default="Monsoon")
    academic_year = serializers.CharField(max_length=20, default="2026-27")
    hours_per_week = serializers.IntegerField(default=8)
    department = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")


class DepartmentAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentAnnouncement
        fields = [
            "id",
            "title",
            "content",
            "department",
            "target_audience",
            "posted_by_id",
            "posted_by_name",
            "is_pinned",
            "created_at",
        ]


class DepartmentAnnouncementCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    content = serializers.CharField()
    department = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    target_audience = serializers.CharField(max_length=50, default="ALL")
    is_pinned = serializers.BooleanField(default=False)
