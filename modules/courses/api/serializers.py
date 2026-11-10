"""Course Workspace serializers."""
from __future__ import annotations

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from modules.courses.models import CourseAnnouncement, CourseAssignment, CourseMaterial, CourseMaterialSection, CourseWorkspace
from modules.courses.selectors import scoping
from modules.directory.contracts import get_users


class CoursePersonSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    department = serializers.CharField(allow_blank=True)


class WorkspaceSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseWorkspace
        fields = [
            "id", "code", "title", "semester", "academic_year",
            "credits", "is_published",
        ]


class WorkspaceDetailSerializer(serializers.ModelSerializer):
    instructors = serializers.SerializerMethodField()
    tas = serializers.SerializerMethodField()
    viewer_role = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = CourseWorkspace
        fields = [
            "id", "code", "title", "description", "semester",
            "academic_year", "credits", "syllabus", "schedule",
            "is_published", "allow_ta_announcements",
            "instructors", "tas", "viewer_role", "can_manage",
        ]

    def _get_personnel_map(self, obj):
        if not hasattr(self, "_personnel_cache"):
            self._personnel_cache = {}
        if obj.id not in self._personnel_cache:
            inst_ids, ta_ids = scoping.get_workspace_personnel_ids(obj)
            all_ids = list(set(inst_ids + ta_ids))
            users = get_users(all_ids)
            self._personnel_cache[obj.id] = (inst_ids, ta_ids, users)
        return self._personnel_cache[obj.id]

    @extend_schema_field(CoursePersonSerializer(many=True))
    def get_instructors(self, obj):
        inst_ids, _, users = self._get_personnel_map(obj)
        results = []
        for uid in inst_ids:
            u = users.get(uid)
            results.append({
                "user_id": uid,
                "name": u.display_name if u else f"User {uid}",
                "email": u.email if u else "",
                "department": u.department if u else "",
            })
        return results

    @extend_schema_field(CoursePersonSerializer(many=True))
    def get_tas(self, obj):
        _, ta_ids, users = self._get_personnel_map(obj)
        results = []
        for uid in ta_ids:
            u = users.get(uid)
            results.append({
                "user_id": uid,
                "name": u.display_name if u else f"User {uid}",
                "email": u.email if u else "",
                "department": u.department if u else "",
            })
        return results

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_viewer_role(self, obj):
        request = self.context.get("request")
        p = getattr(request, "principal", None)
        mem = scoping.get_workspace_membership(obj, p)
        return mem.role if mem else None

    @extend_schema_field(serializers.BooleanField())
    def get_can_manage(self, obj):
        request = self.context.get("request")
        p = getattr(request, "principal", None)
        return scoping.is_course_instructor(obj, p)


class WorkspaceUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    syllabus = serializers.CharField(required=False, allow_blank=True)
    schedule = serializers.CharField(required=False, allow_blank=True)
    is_published = serializers.BooleanField(required=False)
    allow_ta_announcements = serializers.BooleanField(required=False)


class CourseMaterialSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseMaterialSection
        fields = [
            "id",
            "workspace_id",
            "title",
            "description",
            "sort_order",
            "created_at",
            "updated_at",
        ]


class CourseMaterialSectionCreateUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    sort_order = serializers.IntegerField(required=False, default=0)


class CourseMaterialSerializer(serializers.ModelSerializer):
    section_title = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    is_available = serializers.BooleanField(read_only=True)
    is_scheduled = serializers.BooleanField(read_only=True)

    class Meta:
        model = CourseMaterial
        fields = [
            "id",
            "workspace_id",
            "section",
            "section_title",
            "title",
            "description",
            "material_type",
            "file_url",
            "filename",
            "file_size",
            "mime_type",
            "link_url",
            "content",
            "is_published",
            "release_at",
            "is_available",
            "is_scheduled",
            "created_by_id",
            "sort_order",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_section_title(self, obj) -> str | None:
        return obj.section.title if obj.section else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_file_url(self, obj) -> str | None:
        if obj.material_type == "file" and obj.file:
            return f"/api/v1/courses/workspaces/{obj.workspace_id}/materials/{obj.id}/download"
        return None


class CourseMaterialCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    material_type = serializers.ChoiceField(choices=["file", "link", "note"])
    section_id = serializers.IntegerField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    link_url = serializers.CharField(required=False, allow_blank=True, default="")
    content = serializers.CharField(required=False, allow_blank=True, default="")
    file = serializers.FileField(required=False, allow_null=True)
    is_published = serializers.BooleanField(required=False, default=True)
    release_at = serializers.DateTimeField(required=False, allow_null=True)
    sort_order = serializers.IntegerField(required=False, default=0)


class CourseMaterialUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    section_id = serializers.IntegerField(required=False, allow_null=True)
    clear_section = serializers.BooleanField(required=False, default=False)
    description = serializers.CharField(required=False, allow_blank=True)
    link_url = serializers.CharField(required=False, allow_blank=True)
    content = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField(required=False, allow_null=True)
    is_published = serializers.BooleanField(required=False)
    release_at = serializers.DateTimeField(required=False, allow_null=True)
    clear_release_at = serializers.BooleanField(required=False, default=False)
    sort_order = serializers.IntegerField(required=False)


class CourseAnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = CourseAnnouncement
        fields = [
            "id",
            "workspace_id",
            "title",
            "body",
            "is_published",
            "published_at",
            "created_by_id",
            "author_name",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_author_name(self, obj) -> str:
        if not obj.created_by_id:
            return "Instructor"
        users = get_users([obj.created_by_id])
        user = users.get(obj.created_by_id)
        return user.display_name if user else f"User {obj.created_by_id}"


class CourseAnnouncementCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()
    is_published = serializers.BooleanField(required=False, default=True)


class CourseAnnouncementUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    body = serializers.CharField(required=False)
    is_published = serializers.BooleanField(required=False)


class CourseAssignmentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    has_passed = serializers.BooleanField(read_only=True)

    class Meta:
        model = CourseAssignment
        fields = [
            "id",
            "workspace_id",
            "title",
            "description",
            "instructions",
            "due_at",
            "has_passed",
            "is_published",
            "published_at",
            "created_by_id",
            "author_name",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_author_name(self, obj) -> str:
        if not obj.created_by_id:
            return "Instructor"
        users = get_users([obj.created_by_id])
        user = users.get(obj.created_by_id)
        return user.display_name if user else f"User {obj.created_by_id}"


class CourseAssignmentCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    instructions = serializers.CharField(required=False, allow_blank=True, default="")
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    is_published = serializers.BooleanField(required=False, default=False)


class CourseAssignmentUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    instructions = serializers.CharField(required=False, allow_blank=True)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    clear_due_at = serializers.BooleanField(required=False, default=False)
    is_published = serializers.BooleanField(required=False)



