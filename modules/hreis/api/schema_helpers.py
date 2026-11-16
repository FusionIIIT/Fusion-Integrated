"""OpenAPI response envelope for the role-filtered approval queue."""

from rest_framework import serializers

from modules.hreis.api.serializers import (
    AppraisalSerializer,
    ClaimSerializer,
    LeaveRequestSerializer,
)


class ApprovalQueueSerializer(serializers.Serializer):
    leave = LeaveRequestSerializer(many=True)
    claims = ClaimSerializer(many=True)
    appraisals = AppraisalSerializer(many=True)
