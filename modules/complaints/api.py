from rest_framework import serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.complaints.services import submit


class ComplaintSubmitSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=120, allow_blank=False)
    description = serializers.CharField(allow_blank=False)
    attachments = serializers.ListField(
        child=serializers.FileField(), required=False, allow_empty=True,
    )


class ComplaintSerializer(serializers.Serializer):
    complaint_id = serializers.UUIDField()
    category = serializers.CharField()
    description = serializers.CharField()
    submitted_at = serializers.DateTimeField()
    confirmation = serializers.CharField(default="Complaint submitted successfully.")


class ComplaintSubmitView(APIView):
    permission_classes = [IsAuthenticated, HasModuleGrant("complaints"),
                          HasPermission("complaints.complaint.create")]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        serializer = ComplaintSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complaint = submit(user_id=request.principal.user_id,
                           recipient_email=request.principal.email,
                           **serializer.validated_data)
        return Response(ComplaintSerializer(complaint).data, status=201)
