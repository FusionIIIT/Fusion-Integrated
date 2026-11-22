"""DRF Serializers for LMS API endpoints."""

from __future__ import annotations

from rest_framework import serializers

from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    CourseAnnouncement,
    CourseMaterial,
    CourseWorkspace,
    GradeChangeAudit,
    SubmissionGrade,
)


class CourseWorkspaceSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    course_id = serializers.IntegerField()
    course_code = serializers.CharField()
    title = serializers.CharField()
    role = serializers.CharField()


class CourseWorkspaceDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    course_id = serializers.IntegerField()
    course_code = serializers.CharField()
    title = serializers.CharField()
    syllabus = serializers.CharField(allow_blank=True, default="")
    schedule_info = serializers.CharField(allow_blank=True, default="")
    instructors = serializers.ListField(child=serializers.IntegerField(), default=list)
    teaching_assistants = serializers.ListField(child=serializers.IntegerField(), default=list)


class CourseWorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseWorkspace
        fields = [
            "id",
            "course_id",
            "course_code",
            "title",
            "syllabus",
            "schedule_info",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "course_id", "course_code", "title", "created_at", "updated_at"]


class CourseWorkspaceUpdateSerializer(serializers.Serializer):
    syllabus = serializers.CharField(required=False, allow_blank=True, default="")
    schedule_info = serializers.CharField(required=False, allow_blank=True, default="")


class CourseMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseMaterial
        fields = [
            "id",
            "course_id",
            "title",
            "description",
            "material_type",
            "content_text",
            "external_url",
            "file_attachment",
            "section_name",
            "sort_order",
            "status",
            "release_date",
            "uploaded_by",
            "created_at",
        ]
        read_only_fields = ["id", "status", "uploaded_by", "created_at"]


class CourseAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseAnnouncement
        fields = [
            "id",
            "course_id",
            "title",
            "content",
            "author_id",
            "author_role",
            "created_at",
        ]
        read_only_fields = ["id", "author_id", "author_role", "created_at"]


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = [
            "id",
            "course_id",
            "title",
            "instructions",
            "points_possible",
            "submission_type",
            "due_date",
            "release_date",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_by", "created_at", "updated_at"]


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentSubmission
        fields = [
            "id",
            "assignment",
            "student_id",
            "submission_type",
            "content_text",
            "content_link",
            "file_attachment",
            "submitted_at",
            "attempt_number",
            "status",
        ]
        read_only_fields = ["id", "student_id", "submitted_at", "attempt_number", "status"]


class SubmissionGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionGrade
        fields = [
            "id",
            "submission",
            "points_awarded",
            "feedback_text",
            "status",
            "graded_by",
            "graded_at",
            "published_at",
            "published_by",
        ]
        read_only_fields = [
            "id",
            "submission",
            "status",
            "graded_by",
            "graded_at",
            "published_at",
            "published_by",
        ]


class GradeChangeAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeChangeAudit
        fields = [
            "id",
            "grade",
            "submission_id",
            "old_points",
            "new_points",
            "old_feedback",
            "new_feedback",
            "changed_by",
            "changed_at",
            "reason",
        ]
        read_only_fields = fields


class PublishGradesRequestSerializer(serializers.Serializer):
    submission_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True, default=list
    )


class PublishGradesResponseSerializer(serializers.Serializer):
    published_count = serializers.IntegerField()
