from rest_framework import generics
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.iwd.models import IwdRequest
from modules.iwd.serializers import IwdRequestSerializer

class RequestListCreateView(generics.ListCreateAPIView):
    serializer_class = IwdRequestSerializer
    permission_classes = [HasModuleGrant("iwd"), HasPermission("iwd.request.view_self", "iwd.request.view_all", "iwd.request.create")]
    def get_queryset(self):
        if self.request.principal.has_permission("iwd.request.view_all"):
            return IwdRequest.objects.all()
        return IwdRequest.objects.filter(creator_id=self.request.principal.user_id)
    def perform_create(self, serializer):
        serializer.save(creator_id=self.request.principal.user_id, status="pending")
