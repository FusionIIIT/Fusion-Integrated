"""Course Workspace serializers."""
from __future__ import annotations

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from modules.courses.models import CourseWorkspace
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
