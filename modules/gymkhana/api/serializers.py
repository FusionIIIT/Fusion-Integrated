from rest_framework import serializers

from modules.gymkhana.models import Club, MembershipApplication


class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = ["id", "code", "name", "description"]


class ApplySerializer(serializers.Serializer):
    club_id = serializers.IntegerField(min_value=1)
    achievements = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    statement = serializers.CharField(required=False, allow_blank=True, max_length=5000)


class ReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class BulkReviewItemSerializer(serializers.Serializer):
    application_id = serializers.IntegerField(min_value=1)
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class BulkReviewSerializer(serializers.Serializer):
    items = BulkReviewItemSerializer(many=True, allow_empty=False, max_length=100)


class MembershipApplicationSerializer(serializers.ModelSerializer):
    club = ClubSerializer(read_only=True)

    class Meta:
        model = MembershipApplication
        fields = [
            "id", "club", "student_id", "achievements", "statement",
            "status", "reviewed_by", "reviewed_at", "review_remarks",
            "created_at", "updated_at",
        ]
        read_only_fields = fields
