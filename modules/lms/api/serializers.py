"""Serializers for the LMS module."""
from rest_framework import serializers

from modules.lms.models import (
    Announcement,
    Assignment,
    CourseMaterial,
    Grade,
    GradeAudit,
    Submission,
)


class CourseMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseMaterial
        fields = ["id", "course_id", "title", "material_type", "content",
                  "section", "status", "release_at", "user_id", "created_at"]
        read_only_fields = ["course_id", "user_id", "created_at"]


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ["id", "course_id", "user_id", "content", "is_pinned", "created_at"]
        read_only_fields = ["course_id", "user_id", "created_at"]
        ref_name = "LmsAnnouncement"


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ["id", "course_id", "title", "instructions", "due_at",
                  "submission_type", "points_possible", "status", "release_at",
                  "max_attempts", "user_id", "created_at"]
        read_only_fields = ["course_id", "user_id", "created_at"]


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ["id", "assignment", "user_id", "submission_type", "content",
                  "file", "submitted_at", "status", "is_late", "attempt_number"]
        read_only_fields = ["user_id", "submitted_at", "status", "is_late", "attempt_number"]


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = ["id", "submission", "points", "feedback", "status",
                  "graded_by", "graded_at", "released_by", "released_at"]
        read_only_fields = ["graded_by", "graded_at", "released_by", "released_at", "status"]


class GradeAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeAudit
        fields = ["id", "grade", "changed_by", "changed_at", "old_points",
                  "new_points", "old_feedback", "new_feedback", "reason"]
