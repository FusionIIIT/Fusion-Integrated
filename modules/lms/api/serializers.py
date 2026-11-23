from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from modules.lms.models import (
    Announcement,
    Assignment,
    CoursePolicyVersion,
    Grade,
    Material,
    MaterialSection,
    StoredFile,
    Submission,
)


class StaffSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    display_name = serializers.CharField()
    email = serializers.CharField()
    course_role = serializers.CharField()


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialSection
        fields = ("id", "workspace_id", "kind", "label", "order")
        read_only_fields = fields


class CourseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    external_offering_key = serializers.CharField()
    course_code = serializers.CharField()
    course_name = serializers.CharField()
    working_year = serializers.CharField(allow_null=True)
    session = serializers.CharField(allow_null=True)
    syllabus = serializers.CharField()
    schedule = serializers.CharField()
    details_published_at = serializers.DateTimeField(allow_null=True)
    acting_course_role = serializers.ChoiceField(choices=("STUDENT", "FACULTY", "TA", "OBSERVER"))
    can_post_announcements = serializers.BooleanField()
    staff = StaffSerializer(many=True)
    sections = SectionSerializer(many=True)


class CourseInput(serializers.Serializer):
    syllabus = serializers.CharField(required=False, allow_blank=True)
    schedule = serializers.CharField(required=False, allow_blank=True)


class PolicySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, allow_null=True)
    effective_from = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = CoursePolicyVersion
        fields = (
            "id",
            "workspace_id",
            "version",
            "effective_from",
            "can_ta_post_announcements",
            "decision_version",
            "author_user_id",
        )
        read_only_fields = fields


class PolicyInput(serializers.Serializer):
    can_ta_post_announcements = serializers.BooleanField()


class SectionInput(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("MODULE", "WEEK"))
    label = serializers.CharField(max_length=200)
    order = serializers.IntegerField(min_value=0, max_value=2_147_483_647, required=False)


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoredFile
        fields = ("name", "mime_type", "size", "sha256")
        read_only_fields = fields


class MaterialSerializer(serializers.ModelSerializer):
    kind = serializers.ChoiceField(choices=("FILE", "NOTE", "LINK"), read_only=True)
    state = serializers.ChoiceField(choices=("DRAFT", "SCHEDULED", "PUBLISHED"), read_only=True)
    file = FileSerializer(source="stored_file", read_only=True, allow_null=True)

    class Meta:
        model = Material
        fields = (
            "id",
            "workspace_id",
            "section_id",
            "title",
            "kind",
            "text",
            "url",
            "file",
            "order",
            "state",
            "release_at",
            "published_at",
            "author_user_id",
        )
        read_only_fields = fields


class MaterialInput(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    kind = serializers.ChoiceField(choices=("FILE", "NOTE", "LINK"))
    text = serializers.CharField(required=False, allow_blank=True)
    url = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    file = serializers.FileField(required=False)
    section_id = serializers.IntegerField(required=False, allow_null=True)
    order = serializers.IntegerField(min_value=0, max_value=2_147_483_647, required=False)


class ReleaseInput(serializers.Serializer):
    release_at = serializers.DateTimeField(required=False, allow_null=True)


@extend_schema_serializer(component_name="LmsAnnouncement")
class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ("id", "workspace_id", "content", "author_user_id", "created_at")
        read_only_fields = fields


class AnnouncementInput(serializers.Serializer):
    content = serializers.CharField()


class AssignmentSerializer(serializers.ModelSerializer):
    submission_type = serializers.ChoiceField(choices=("FILE", "TEXT", "LINK"), read_only=True)
    state = serializers.ChoiceField(choices=("DRAFT", "SCHEDULED", "AVAILABLE"), read_only=True)

    class Meta:
        model = Assignment
        fields = (
            "id",
            "workspace_id",
            "title",
            "instructions",
            "due_at",
            "submission_type",
            "points_possible",
            "state",
            "release_at",
            "published_at",
            "author_user_id",
        )
        read_only_fields = fields


class AssignmentInput(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    instructions = serializers.CharField(allow_blank=True)
    due_at = serializers.DateTimeField()
    submission_type = serializers.ChoiceField(choices=("FILE", "TEXT", "LINK"))
    points_possible = serializers.DecimalField(max_digits=10, decimal_places=2)


class GradeSerializer(serializers.ModelSerializer):
    state = serializers.ChoiceField(choices=("DRAFT", "RELEASED"), read_only=True)
    assignment_id = serializers.IntegerField(source="submission.assignment_id", read_only=True)
    user_id = serializers.IntegerField(source="submission.user_id", read_only=True)

    class Meta:
        model = Grade
        fields = (
            "id",
            "submission_id",
            "assignment_id",
            "user_id",
            "points",
            "feedback",
            "state",
            "grader_user_id",
            "graded_at",
            "released_by_user_id",
            "released_at",
        )
        read_only_fields = fields


class SubmissionSerializer(serializers.ModelSerializer):
    kind = serializers.ChoiceField(choices=("FILE", "TEXT", "LINK"), read_only=True)
    file = FileSerializer(source="stored_file", read_only=True, allow_null=True)

    class Meta:
        model = Submission
        fields = (
            "id",
            "assignment_id",
            "user_id",
            "kind",
            "text",
            "url",
            "file",
            "submitted_at",
            "policy_version",
        )
        read_only_fields = fields


class SubmissionInput(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("FILE", "TEXT", "LINK"))
    text = serializers.CharField(required=False, allow_blank=True)
    url = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    file = serializers.FileField(required=False)


class GradeInput(serializers.Serializer):
    points = serializers.DecimalField(max_digits=10, decimal_places=2)
    feedback = serializers.CharField(required=False, allow_blank=True)


class EmptyInput(serializers.Serializer):
    pass
