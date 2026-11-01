from rest_framework import serializers

from modules.department.models.feedback import Feedback


class DeptFeedbackSerializer(serializers.ModelSerializer):
    """Serializes a Feedback model instance."""
    class Meta:
        model = Feedback
        fields = [
            "id",
            "department",
            "submitter_user_id",
            "body",
            "category",
            "state",
            "reviewed_at",
            "disposed_at",
            "created_at",
        ]


class DeptFeedbackWriteSerializer(serializers.Serializer):
    """Serializes data for creating a Feedback submission."""
    department = serializers.IntegerField()
    body = serializers.CharField()


class DeptFeedbackReviewSerializer(serializers.Serializer):
    """Serializes data for reviewing a Feedback submission."""
    category = serializers.ChoiceField(choices=[
        ('academic', 'Academic'),
        ('infrastructure', 'Infrastructure'),
        ('administrative', 'Administrative'),
        ('facilities', 'Facilities'),
        ('other', 'Other'),
    ])
    disposition = serializers.ChoiceField(
        choices=[
            ('resolved', 'Resolved'),
            ('closed', 'Closed'),
        ],
        required=False,
    )


class DeptFeedbackDisposeSerializer(serializers.Serializer):
    """Serializes data for disposing of a Feedback submission."""
    outcome = serializers.CharField()
