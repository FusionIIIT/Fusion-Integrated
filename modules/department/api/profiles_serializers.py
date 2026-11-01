from rest_framework import serializers

from modules.department.models.profiles import (
    CourseRoster,
    DepartmentProfile,
    OfficialChangeProposal,
)


class DeptProfileSerializer(serializers.ModelSerializer):
    """Serializes a DepartmentProfile model instance."""
    class Meta:
        model = DepartmentProfile
        fields = [
            "id",
            "department",
            "record_kind",
            "user_id",
            "display_name",
            "email",
            "title",
            "office",
            "bio",
            "graduation_year",
            "is_active",
        ]


class DeptProfileWriteSerializer(serializers.Serializer):
    """Serializes data for creating/updating a DepartmentProfile."""
    department = serializers.IntegerField()
    record_kind = serializers.ChoiceField(choices=[
        ('faculty', 'Faculty'),
        ('student', 'Student'),
        ('alumni', 'Alumni'),
    ])
    user_id = serializers.IntegerField(required=False)
    display_name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False)
    title = serializers.CharField(max_length=255, required=False)
    office = serializers.CharField(max_length=255, required=False)
    bio = serializers.CharField(max_length=1000, required=False)
    graduation_year = serializers.IntegerField(required=False)
    extra_kwargs = {
        "user_id": {"required": False},
        "display_name": {"required": False},
        "email": {"required": False},
        "title": {"required": False},
        "office": {"required": False},
        "bio": {"required": False},
        "graduation_year": {"required": False},
    }


class DeptRosterSerializer(serializers.ModelSerializer):
    """Serializes a CourseRoster model instance."""
    class Meta:
        model = CourseRoster
        fields = [
            "id",
            "department",
            "course_code",
            "faculty_user_id",
            "student_user_id",
            "academic_year",
        ]


class DeptOfficialChangeSerializer(serializers.ModelSerializer):
    """Serializes a DepartmentOfficialChangeProposal model instance."""
    class Meta:
        model = OfficialChangeProposal
        fields = [
            "id",
            "department",
            "changes",
            "state",
            "proposed_by_user_id",
            "decided_by_user_id",
            "decided_at",
        ]


class DeptChangeDecisionSerializer(serializers.Serializer):
    """Serializes the outcome of a change decision."""
    outcome = serializers.CharField()


class DeptDetailsWriteSerializer(serializers.Serializer):
    """Serializes optional details for department profiles."""
    name = serializers.CharField(max_length=255, required=False)
    core_policies = serializers.JSONField(required=False)
    about = serializers.CharField(max_length=2000, required=False)
    contact_email = serializers.EmailField(required=False)
    location = serializers.CharField(max_length=255, required=False)
    website = serializers.URLField(required=False)
    headship = serializers.BooleanField(required=False)
