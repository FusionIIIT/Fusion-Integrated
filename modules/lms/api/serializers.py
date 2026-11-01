from rest_framework import serializers

from modules.lms.models import Announcement, Assignment, Material, Submission


class FileMixin:
    def get_download_url(self, obj) -> str | None:
        kind = {"Material": "material", "Assignment": "assignment", "Submission": "submission"}[
            type(obj).__name__
        ]
        workspace_id = obj.assignment.workspace_id if kind == "submission" else obj.workspace_id
        if kind != "assignment" and not obj.file:
            return None
        return f"/api/v1/lms/courses/{workspace_id}/download/{kind}/{obj.pk}/"


class MaterialSerializer(FileMixin, serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Material
        fields = (
            "id",
            "title",
            "section",
            "kind",
            "text",
            "link",
            "release_at",
            "state",
            "download_url",
        )


class AssignmentSerializer(FileMixin, serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = (
            "id",
            "title",
            "instructions",
            "submission_type",
            "points_possible",
            "due_at",
            "release_at",
            "state",
            "download_url",
        )


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ("id", "title", "body", "author_id", "created_at")


class SubmissionSerializer(FileMixin, serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    points = serializers.SerializerMethodField()
    feedback = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = (
            "id",
            "assignment_id",
            "student_id",
            "text",
            "link",
            "submitted_at",
            "points",
            "feedback",
            "released",
            "revision",
            "download_url",
        )

    def get_points(self, obj) -> str | None:
        return (
            str(obj.points)
            if obj.points is not None and (obj.released or self.context.get("reviewer"))
            else None
        )

    def get_feedback(self, obj) -> str:
        return obj.feedback if obj.released or self.context.get("reviewer") else ""


class RevisionSerializer(serializers.Serializer):
    revision = serializers.IntegerField(min_value=1)
