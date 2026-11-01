from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from fusion_auth.permissions import HasModuleGrant, HasPermission
from ..models import ComplaintCategory, RoutingRule, ComplaintUpdate, ComplaintNotification
from .serializers import (
    ComplaintCategorySerializer,
    RoutingRuleSerializer,
    ComplaintUpdateSerializer,
    ComplaintNotificationSerializer
)
from drf_spectacular.utils import extend_schema
from django.contrib.auth.decorators import login_required

class ConfigurationView(generics.ListCreateAPIView):
    queryset = ComplaintCategory.objects.all()
    serializer_class = ComplaintCategorySerializer
    permission_classes = [permissions.IsAuthenticated, HasModuleGrant("complaint_cms"), HasPermission("complaint_cms.configuration.manage")]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class RecordListView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasModuleGrant("complaint_cms"), HasPermission("complaint_cms.record.manage")]

    @extend_schema(responses={200: ComplaintUpdateSerializer(many=True)})
    def get(self, request):
        updates = ComplaintUpdate.objects.order_by('-created_at')[:10]
        notifications = ComplaintNotification.objects.order_by('-created_at')[:10]
        data = list(updates) + list(notifications)
        return Response(data)
