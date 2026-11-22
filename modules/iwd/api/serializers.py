from rest_framework import serializers

from ..models import Complaint, Estimate, Feedback, FinalBill


class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = "__all__"
        read_only_fields = ["id", "status", "assigned_engineer_id", "fast_tracked", "created_at", "updated_at"]

    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Title must have at least 3 characters.")
        return value

    def validate_description(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Description must have at least 5 characters.")
        return value

class EstimateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estimate
        fields = "__all__"
        read_only_fields = ["id", "total_cost", "cost_band", "status", "approved_by_id", "approved_at", "created_at", "updated_at"]

class FinalBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinalBill
        fields = "__all__"
        read_only_fields = ["id", "settlement_status", "auditor_verified", "director_approved", "settled_at", "created_at"]

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = "__all__"
        read_only_fields = ["id", "created_at"]
