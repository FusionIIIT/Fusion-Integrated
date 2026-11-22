"""Course Workspace serializers."""
from __future__ import annotations

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from modules.courses.models import (
    CourseAnnouncement,
    CourseAssignment,
    CourseGrade,
    CourseGradeAudit,
    CourseMaterial,
    CourseMaterialSection,
    CourseSubmission,
    CourseWorkspace,
)
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
            "max_points",
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
    max_points = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=100.00)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    is_published = serializers.BooleanField(required=False, default=False)


class CourseAssignmentUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    instructions = serializers.CharField(required=False, allow_blank=True)
    max_points = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    clear_due_at = serializers.BooleanField(required=False, default=False)
    is_published = serializers.BooleanField(required=False)


class CourseGradeSerializer(serializers.ModelSerializer):
    grader_name = serializers.SerializerMethodField()

    class Meta:
        model = CourseGrade
        fields = [
            "id",
            "submission_id",
            "assignment_id",
            "workspace_id",
            "student_id",
            "grader_id",
            "grader_name",
            "score",
            "feedback",
            "status",
            "graded_at",
            "released_at",
            "released_by_id",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_grader_name(self, obj) -> str:
        if not obj.grader_id:
            return "Grader"
        users = get_users([obj.grader_id])
        user = users.get(obj.grader_id)
        return user.display_name if user else f"User {obj.grader_id}"


class CourseSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_username = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()

    class Meta:
        model = CourseSubmission
        fields = [
            "id",
            "assignment_id",
            "workspace_id",
            "student_id",
            "student_name",
            "student_username",
            "submission_type",
            "filename",
            "file_size",
            "file_url",
            "link_url",
            "content",
            "submitted_at",
            "is_late",
            "attempt_number",
            "status",
            "grade",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_student_name(self, obj) -> str:
        if not obj.student_id:
            return "Unknown Student"
        users = get_users([obj.student_id])
        user = users.get(obj.student_id)
        return user.display_name if user else f"Student {obj.student_id}"

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_student_username(self, obj) -> str:
        if not obj.student_id:
            return ""
        users = get_users([obj.student_id])
        user = users.get(obj.student_id)
        return user.username if user else ""

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_file_url(self, obj) -> str | None:
        if obj.submission_type == "file" and obj.file:
            return (
                f"/api/v1/courses/workspaces/{obj.workspace_id}/assignments/"
                f"{obj.assignment_id}/submissions/{obj.id}/download"
            )
        return None

    @extend_schema_field(CourseGradeSerializer(allow_null=True))
    def get_grade(self, obj) -> dict | None:
        try:
            grade = obj.grade
        except (CourseGrade.DoesNotExist, AttributeError):
            return None
        if not grade:
            return None

        viewer_role = self.context.get("viewer_role")
        request = self.context.get("request")
        principal = getattr(request, "principal", None) if request else None
        actor_id = getattr(principal, "user_id", None) if principal else (
            getattr(request.user, "id", None) if request and hasattr(request, "user") else None
        )

        if viewer_role == "observer":
            return None
        if viewer_role in ("instructor", "ta"):
            return CourseGradeSerializer(grade, context=self.context).data
        if viewer_role == "student" and obj.student_id == actor_id and grade.status == "released":
            return CourseGradeSerializer(grade, context=self.context).data
        return None


class CourseSubmissionCreateSerializer(serializers.Serializer):
    submission_type = serializers.ChoiceField(
        choices=["file", "text", "link"],
        default="file",
        required=False,
    )
    file = serializers.FileField(required=False, allow_null=True)
    content = serializers.CharField(required=False, allow_blank=True, default="")
    link_url = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_file(self, value):
        if value and value.size > 25 * 1024 * 1024:
            raise serializers.ValidationError("File size exceeds 25 MB limit.")
        return value


class CourseGradeInputSerializer(serializers.Serializer):
    score = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=0)
    feedback = serializers.CharField(required=False, allow_blank=True, default="")


class CourseGradeReleaseSerializer(serializers.Serializer):
    submission_id = serializers.IntegerField(required=False, allow_null=True)


class CourseGradeReleaseResponseSerializer(serializers.Serializer):
    released_count = serializers.IntegerField()
    results = CourseGradeSerializer(many=True)


class CourseGradeAuditSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = CourseGradeAudit
        fields = [
            "id",
            "grade_id",
            "actor_id",
            "actor_name",
            "action",
            "score_before",
            "score_after",
            "feedback_before",
            "feedback_after",
            "status_before",
            "status_after",
            "created_at",
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_actor_name(self, obj) -> str:
        if not obj.actor_id:
            return "System"
        users = get_users([obj.actor_id])
        user = users.get(obj.actor_id)
        return user.display_name if user else f"User {obj.actor_id}"





