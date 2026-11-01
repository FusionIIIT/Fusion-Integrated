"""Serializers for Course Workspace endpoints."""
from rest_framework import serializers

from modules.lms.domain.entities import CourseStatus


class CourseSummarySerializer(serializers.Serializer):
    code = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    schedule = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    role = serializers.CharField()


class CourseStaffSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    display_name = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    department = serializers.CharField(allow_blank=True)


class CourseWorkspaceDetailSerializer(serializers.Serializer):
    code = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    syllabus = serializers.CharField(allow_blank=True)
    schedule = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    role = serializers.CharField()
    can_edit = serializers.BooleanField()
    instructors = CourseStaffSerializer(many=True)
    teaching_assistants = CourseStaffSerializer(many=True)


class CourseWorkspaceUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    syllabus = serializers.CharField(required=False, allow_blank=True)
    schedule = serializers.CharField(required=False, allow_blank=True, max_length=200)
    status = serializers.ChoiceField(
        choices=[CourseStatus.DRAFT, CourseStatus.PUBLISHED], required=False
    )
