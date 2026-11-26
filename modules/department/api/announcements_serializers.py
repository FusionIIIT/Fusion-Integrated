from rest_framework import serializers

from modules.department.models import Announcement


class DeptAnnouncementSerializer(serializers.ModelSerializer):
    """Serializes an Announcement model instance."""
    class Meta:
        model = Announcement
        fields = [
            "id",
            "department",
            "title",
            "body",
            "target_roles",
            "target_programme",
            "target_batch_year",
            "status",
            "published_by_user_id",
            "created_at",
        ]


class DeptAnnouncementWriteSerializer(serializers.Serializer):
    """Serializes data for creating or updating an Announcement."""
    department = serializers.IntegerField(required=False)
    title = serializers.CharField(max_length=255)
    body = serializers.CharField()
    target_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            ("student", "Student"),
            ("faculty", "Faculty"),
        ]),
        required=True,
    )
    target_programme = serializers.CharField(required=False, allow_blank=True)
    target_batch_year = serializers.IntegerField(required=False, allow_null=True)
