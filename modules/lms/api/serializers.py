"""DRF serializers for LMS (Course Management)."""
from rest_framework import serializers

from ..models import (
    Assignment,
    CourseAnnouncement,
    CourseMaterial,
    CourseMembership,
    CourseWorkspace,
    Grade,
    GradeChangeLog,
    StudentSubmission,
)


class CourseWorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseWorkspace
        fields = [
            "id",
            "course_code",
            "title",
            "syllabus",
            "schedule",
            "instructor_user_id",
            "is_active",
            "created_at",
            "updated_at",
        ]


class CourseMembershipSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.course_code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = CourseMembership
        fields = [
            "id",
            "course",
            "course_code",
            "course_title",
            "user_id",
            "role",
            "can_post_announcements",
            "created_at",
        ]


class CourseMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseMaterial
        fields = [
            "id",
            "course",
            "title",
            "description",
            "section_or_week",
            "material_type",
            "file_url",
            "content",
            "status",
            "scheduled_release_at",
            "published_at",
            "uploaded_by_user_id",
            "created_at",
        ]


class CourseAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseAnnouncement
        fields = [
            "id",
            "course",
            "title",
            "content",
            "posted_by_user_id",
            "is_ta_announcement",
            "posted_at",
        ]


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = [
            "id",
            "course",
            "title",
            "instructions",
            "points_possible",
            "submission_type",
            "due_date",
            "status",
            "scheduled_release_at",
            "published_at",
            "created_by_user_id",
            "created_at",
        ]


class AssignmentCreateSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    title = serializers.CharField(max_length=200)
    instructions = serializers.CharField()
    points_possible = serializers.DecimalField(max_digits=5, decimal_places=2)
    submission_type = serializers.ChoiceField(choices=["file", "text", "link"])
    due_date = serializers.DateTimeField()


class AssignmentPublishSerializer(serializers.Serializer):
    is_scheduled = serializers.BooleanField(default=False)
    release_date = serializers.DateTimeField(required=False, allow_null=True)


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = [
            "id",
            "submission",
            "points",
            "feedback",
            "status",
            "graded_by_user_id",
            "graded_at",
            "released_at",
            "released_by_user_id",
        ]


class StudentSubmissionSerializer(serializers.ModelSerializer):
    grade = GradeSerializer(read_only=True)
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    due_date = serializers.DateTimeField(source="assignment.due_date", read_only=True)

    class Meta:
        model = StudentSubmission
        fields = [
            "id",
            "assignment",
            "assignment_title",
            "due_date",
            "student_user_id",
            "submission_type",
            "submission_content",
            "submitted_at",
            "status",
            "grade",
        ]


class StudentSubmissionCreateSerializer(serializers.Serializer):
    assignment_id = serializers.IntegerField()
    submission_type = serializers.ChoiceField(choices=["file", "text", "link"])
    submission_content = serializers.CharField()


class GradeEvaluationSerializer(serializers.Serializer):
    submission_id = serializers.IntegerField()
    points = serializers.DecimalField(max_digits=5, decimal_places=2)
    feedback = serializers.CharField(required=False, allow_blank=True)


class GradeModificationSerializer(serializers.Serializer):
    new_points = serializers.DecimalField(max_digits=5, decimal_places=2)
    reason = serializers.CharField(max_length=500)


class GradeChangeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeChangeLog
        fields = [
            "id",
            "grade",
            "old_points",
            "new_points",
            "reason",
            "changed_by_user_id",
            "changed_at",
        ]
