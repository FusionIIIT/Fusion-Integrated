from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from fusion_auth.permissions import HasPermission
from modules.phc.models import Notification
from modules.phc.api.serializers import NotificationSerializer

class NotificationListView(APIView):
    permission_classes = [HasPermission("phc.notification.view")]

    @extend_schema(responses={200: NotificationSerializer(many=True)})
    def get(self, request):
        qs = Notification.objects.filter(recipient_user_id=request.user.user_id).order_by("-created_at")
        serializer = NotificationSerializer(qs, many=True)
        return Response(serializer.data)
