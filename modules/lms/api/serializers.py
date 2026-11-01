from rest_framework import serializers

from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    CourseAnnouncement,
    CourseMaterial,
    CourseSection,
    SubmissionGrade,
)


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseSection
        fields = ("id", "kind", "title", "sort_order")
        read_only_fields = ("id",)


class SectionWriteSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("module", "week"))
    title = serializers.CharField(max_length=160)
    sort_order = serializers.IntegerField(min_value=0, max_value=32767, default=0)


class CourseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    source_course_id = serializers.CharField()
    code = serializers.CharField()
    title = serializers.CharField()
    role = serializers.CharField()
    instructors = serializers.ListField(child=serializers.DictField())
    teaching_assistants = serializers.ListField(child=serializers.DictField())
    may_announce = serializers.BooleanField()
    may_grade = serializers.BooleanField()
    syllabus = serializers.CharField()
    schedule = serializers.CharField()


class CourseDetailsWriteSerializer(serializers.Serializer):
    syllabus = serializers.CharField(allow_blank=True)
    schedule = serializers.CharField(allow_blank=True)


class MaterialSerializer(serializers.ModelSerializer):
    section_id = serializers.IntegerField(read_only=True)
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = CourseMaterial
        fields = ("id", "section_id", "kind", "title", "note", "link",
                  "file_name", "release_at", "status", "published_at",
                  "created_at")
        read_only_fields = fields

    def get_file_name(self, obj) -> str:
        return obj.file.name.rsplit("/", 1)[-1] if obj.file else ""


class MaterialWriteSerializer(serializers.Serializer):
    section = serializers.PrimaryKeyRelatedField(
        queryset=CourseSection.objects.all(), required=False, allow_null=True)
    kind = serializers.ChoiceField(choices=("file", "link", "note"))
    title = serializers.CharField(max_length=200)
    note = serializers.CharField(required=False, allow_blank=True, default="")
    link = serializers.URLField(max_length=500, required=False, allow_blank=True,
                                default="")
    file = serializers.FileField(required=False)
    release_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, data):
        kind = data["kind"]
        if kind == "file" and not (data.get("file") or (self.instance and self.instance.file)):
            raise serializers.ValidationError({"file": "A file is required."})
        if kind == "link" and not data.get("link"):
            raise serializers.ValidationError({"link": "A link is required."})
        if kind == "note" and not data.get("note"):
            raise serializers.ValidationError({"note": "A note is required."})
        return data


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseAnnouncement
        ref_name = "LMSAnnouncement"
        fields = ("id", "title", "content", "posted_by_user_id", "published_at")
        read_only_fields = fields


class AnnouncementWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    content = serializers.CharField()


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ("id", "title", "due_at", "instructions", "submission_type",
                  "points_possible", "release_at", "status", "published_at")
        read_only_fields = fields


class AssignmentWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    due_at = serializers.DateTimeField()
    instructions = serializers.CharField()
    submission_type = serializers.ChoiceField(choices=Assignment.SUBMISSION_TYPES)
    points_possible = serializers.DecimalField(max_digits=8, decimal_places=2,
                                               min_value=0)
    release_at = serializers.DateTimeField(required=False, allow_null=True)


class SubmissionSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    has_grade = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = AssignmentSubmission
        fields = ("id", "assignment", "assignment_title", "user_id", "content_type",
                  "text", "link", "file_name", "download_url", "submitted_at",
                  "has_grade")
        read_only_fields = fields

    def get_has_grade(self, obj) -> bool:
        return hasattr(obj, "grade")

    def get_file_name(self, obj) -> str:
        return obj.file.name.rsplit("/", 1)[-1] if obj.file else ""

    def get_download_url(self, obj) -> str:
        if not obj.file:
            return ""
        return (f"/api/v1/lms/courses/{obj.assignment.course.source_course_id}"
                f"/submissions/{obj.pk}/download")


class SubmissionWriteSerializer(serializers.Serializer):
    content_type = serializers.ChoiceField(choices=Assignment.SUBMISSION_TYPES)
    text = serializers.CharField(required=False, allow_blank=True, default="")
    link = serializers.URLField(max_length=500, required=False, allow_blank=True,
                                default="")
    file = serializers.FileField(required=False)

    def validate(self, data):
        kind = data["content_type"]
        if kind == "file" and not data.get("file"):
            raise serializers.ValidationError({"file": "A file is required."})
        if kind == "text" and not data.get("text"):
            raise serializers.ValidationError({"text": "Submission text is required."})
        if kind == "link" and not data.get("link"):
            raise serializers.ValidationError({"link": "A link is required."})
        return data


class GradeSerializer(serializers.ModelSerializer):
    submission_id = serializers.IntegerField(read_only=True)
    assignment_title = serializers.CharField(
        source="submission.assignment.title", read_only=True)

    class Meta:
        model = SubmissionGrade
        fields = ("id", "submission_id", "assignment_title", "points", "feedback",
                  "status", "graded_by_user_id", "graded_at", "released_by_user_id",
                  "released_at")
        read_only_fields = fields


class GradeWriteSerializer(serializers.Serializer):
    points = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0)
    feedback = serializers.CharField(required=False, allow_blank=True, default="")


class GradeReleaseSerializer(serializers.Serializer):
    grade_ids = serializers.ListField(child=serializers.IntegerField(min_value=1),
                                      allow_empty=False)
