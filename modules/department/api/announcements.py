from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import generics, serializers
from rest_framework.exceptions import APIException

from fusion_auth.client import IamUnavailable
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.department.models import Announcement
from modules.department.permissions import VIEW_ANNOUNCEMENT
from modules.department.selectors import visible_announcements


class DepartmentAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ("id", "content", "published_at")


class IdentityUnavailable(APIException):
    status_code = 503
    default_detail = "Department membership is temporarily unavailable."
    default_code = "identity_service_unavailable"


@method_decorator(never_cache, name="dispatch")
class AnnouncementListView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("department"), HasPermission(VIEW_ANNOUNCEMENT)]
    queryset = Announcement.objects.none()
    serializer_class = DepartmentAnnouncementSerializer

    def get_queryset(self):
        try:
            return visible_announcements(self.request.principal)
        except IamUnavailable as exc:
            raise IdentityUnavailable() from exc
