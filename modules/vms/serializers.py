from rest_framework import serializers

from .models import VisitRequest, VisitorPass, VisitLog


class VisitRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = VisitRequest
        fields = "__all__"
        read_only_fields = [
            "status",
            "decision_at",
            "decision_by",
            "decision_note",
            "submitted_at",
            "created_at",
            "updated_at",
        ]


class VisitorPassSerializer(serializers.ModelSerializer):

    class Meta:
        model = VisitorPass
        fields = "__all__"


class VisitLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = VisitLog
        fields = "__all__"