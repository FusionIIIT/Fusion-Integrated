"""Serializers for Course Workspace endpoints."""
from rest_framework import serializers

from modules.lms.domain.entities import (
    CourseStatus,
    MaterialStatus,
    MaterialType,
    SectionType,
)


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


class CourseMaterialItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    material_type = serializers.CharField()
    section_type = serializers.CharField()
    section_title = serializers.CharField()
    file_name = serializers.CharField(allow_blank=True)
    file_size = serializers.IntegerField(allow_null=True)
    has_file = serializers.BooleanField()
    link_url = serializers.CharField(allow_blank=True)
    content = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    release_at = serializers.CharField(allow_null=True)
    order = serializers.IntegerField()
    created_by_user_id = serializers.IntegerField()
    created_at = serializers.CharField(allow_null=True)
    updated_at = serializers.CharField(allow_null=True)


class CourseMaterialSectionSerializer(serializers.Serializer):
    section_title = serializers.CharField()
    section_type = serializers.CharField()
    materials = CourseMaterialItemSerializer(many=True)


class CourseMaterialsResponseSerializer(serializers.Serializer):
    course_code = serializers.CharField()
    course_title = serializers.CharField()
    role = serializers.CharField()
    can_manage = serializers.BooleanField()
    sections = CourseMaterialSectionSerializer(many=True)
    total_count = serializers.IntegerField()


class CourseMaterialCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    section_title = serializers.CharField(max_length=100)
    material_type = serializers.ChoiceField(
        choices=sorted(MaterialType.ALL), default=MaterialType.FILE
    )
    section_type = serializers.ChoiceField(
        choices=sorted(SectionType.ALL), default=SectionType.MODULE
    )
    status = serializers.ChoiceField(
        choices=sorted(MaterialStatus.ALL), default=MaterialStatus.PUBLISHED
    )
    description = serializers.CharField(required=False, allow_blank=True, default="")
    link_url = serializers.CharField(required=False, allow_blank=True, default="")
    content = serializers.CharField(required=False, allow_blank=True, default="")
    file = serializers.FileField(required=False, allow_null=True, default=None)
    release_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
    order = serializers.IntegerField(required=False, default=0)


class CourseMaterialUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, max_length=200)
    section_title = serializers.CharField(required=False, max_length=100)
    material_type = serializers.ChoiceField(choices=sorted(MaterialType.ALL), required=False)
    section_type = serializers.ChoiceField(choices=sorted(SectionType.ALL), required=False)
    status = serializers.ChoiceField(choices=sorted(MaterialStatus.ALL), required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    link_url = serializers.CharField(required=False, allow_blank=True)
    content = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField(required=False, allow_null=True)
    release_at = serializers.DateTimeField(required=False, allow_null=True)
    order = serializers.IntegerField(required=False)

