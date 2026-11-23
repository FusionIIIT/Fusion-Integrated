from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.department import permissions as p
from modules.department import services
from modules.department.api.common import CheckedFields, DepartmentAccess
from modules.department.models import Announcement
from modules.department.roles import ADMIN_DEPARTMENTS, HOD_DEPARTMENTS
from modules.department.selectors import manageable_announcements, visible_announcements


class DepartmentAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ("id", "content", "published_at")


class DepartmentAnnouncementWriteSerializer(CheckedFields, serializers.Serializer):
    content = serializers.CharField(max_length=8000)
    target_roles = serializers.ListField(child=serializers.ChoiceField(
        choices=["student", "faculty", *HOD_DEPARTMENTS, *ADMIN_DEPARTMENTS]), max_length=20)
    target_programmes = serializers.ListField(
        child=serializers.CharField(max_length=100), max_length=20,
    )
    target_batch_years = serializers.ListField(
        child=serializers.IntegerField(min_value=1900, max_value=2200), max_length=20,
    )


@method_decorator(never_cache, name="dispatch")
class AnnouncementListView(DepartmentAccess, generics.ListCreateAPIView):
    read_permission = p.VIEW_ANNOUNCEMENT
    write_permission = p.PUBLISH_ANNOUNCEMENT
    queryset = Announcement.objects.none()
    serializer_class = DepartmentAnnouncementSerializer

    def get_queryset(self):
        return visible_announcements(self.request.principal)

    @extend_schema(request=DepartmentAnnouncementWriteSerializer,
                   responses={201: DepartmentAnnouncementSerializer})
    def post(self, request):
        payload = DepartmentAnnouncementWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = services.publish_announcement(actor=request.principal, **payload.validated_data)
        return Response(DepartmentAnnouncementSerializer(row).data, status=status.HTTP_201_CREATED)


class AnnouncementMaintenanceSerializer(CheckedFields, serializers.Serializer):
    action = serializers.ChoiceField(choices=["edit", "hide", "delete"])
    announcement = DepartmentAnnouncementWriteSerializer(required=False)

    def validate(self, attrs):
        if attrs["action"] == "edit" and "announcement" not in attrs:
            raise serializers.ValidationError("Editing requires content and all target fields.")
        return attrs


class AnnouncementMaintenanceView(DepartmentAccess, APIView):
    write_permission = p.MANAGE_ANNOUNCEMENT

    @extend_schema(request=AnnouncementMaintenanceSerializer, responses={204: None})
    def post(self, request, pk):
        payload = AnnouncementMaintenanceSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.maintain_announcement(actor=request.principal, announcement_id=pk,
                                       action=payload.validated_data["action"],
                                       changes=payload.validated_data.get("announcement"))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ManagedAnnouncementSerializer(DepartmentAnnouncementSerializer):
    class Meta(DepartmentAnnouncementSerializer.Meta):
        fields = (*DepartmentAnnouncementSerializer.Meta.fields,
                  "target_roles", "target_programmes", "target_batch_years")


@method_decorator(never_cache, name="dispatch")
class ManagedAnnouncementsView(DepartmentAccess, generics.ListAPIView):
    read_permission = p.MANAGE_ANNOUNCEMENT
    queryset = Announcement.objects.none()
    serializer_class = ManagedAnnouncementSerializer

    def get_queryset(self):
        return manageable_announcements(self.request.principal)
