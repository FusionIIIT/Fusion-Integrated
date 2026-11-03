from rest_framework import serializers
from modules.lms.models import (
    Announcement,
    Assignment,
    Course,
    CourseMaterial,
    CourseMembership,
    Grade,
    GradeAuditLog,
    ModuleSection,
    ScheduledRelease,
    Submission,
)


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class CourseMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseMembership
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class ModuleSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleSection
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class CourseMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseMaterial
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = "__all__"
        read_only_fields = ["author_user_id", "author_role", "created_at", "updated_at"]


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = "__all__"
        read_only_fields = [
            "version",
            "submitted_at",
            "status",
            "created_at",
            "updated_at",
        ]


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = "__all__"
        read_only_fields = [
            "released_at",
            "released_by_user_id",
            "created_at",
            "updated_at",
        ]


class GradeAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeAuditLog
        fields = "__all__"
        read_only_fields = ["changed_at"]


class ScheduledReleaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledRelease
        fields = "__all__"
        read_only_fields = ["processed_at", "created_at", "updated_at"]
