from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer

from modules.department.models import Announcement


@extend_schema_serializer(component_name="DepartmentAnnouncement")
class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = (
            "id",
            "title",
            "body",
            "target_roles",
            "target_programs",
            "target_academic_years",
            "published_at",
            "published_by_user_id",
            "published_by_role",
            "is_hidden",
            "deleted_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AnnouncementDraftSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, trim_whitespace=True)
    body = serializers.CharField(trim_whitespace=True)

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value.strip()

    def validate_body(self, value):
        if not value.strip():
            raise serializers.ValidationError("Announcement content cannot be empty.")
        return value.strip()


class AnnouncementPublishSerializer(serializers.Serializer):
    target_roles = serializers.ListField(
        child=serializers.CharField(max_length=60, trim_whitespace=True),
        allow_empty=False,
    )
    target_programs = serializers.ListField(
        child=serializers.CharField(max_length=100, trim_whitespace=True),
        allow_empty=False,
    )
    target_academic_years = serializers.ListField(
        child=serializers.CharField(max_length=30, trim_whitespace=True),
        allow_empty=False,
    )

    def _validate_targets(self, values, field_name):
        cleaned = []

        for value in values:
            value = value.strip()

            if not value:
                raise serializers.ValidationError(
                    f"{field_name} cannot contain empty values."
                )

            if value in cleaned:
                raise serializers.ValidationError(
                    f"{field_name} cannot contain duplicate values."
                )

            cleaned.append(value)

        return cleaned

    def validate_target_roles(self, value):
        return self._validate_targets(value, "target_roles")

    def validate_target_programs(self, value):
        return self._validate_targets(value, "target_programs")

    def validate_target_academic_years(self, value):
        return self._validate_targets(value, "target_academic_years")
