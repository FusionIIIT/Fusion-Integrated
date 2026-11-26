from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.department.api.announcements_serializers import (
    DeptAnnouncementSerializer,
    DeptAnnouncementWriteSerializer,
)
from modules.department.models import Announcement
from modules.department.selectors.announcements import visible_announcements
from modules.department.services import announcements as announcement_service


@extend_schema(
    summary="List and create department announcements",
    responses={
        200: DeptAnnouncementSerializer,
        201: DeptAnnouncementSerializer,
        400: None,
        403: None,
    },
    tags=["Announcements"],
)
class AnnouncementListView(ListCreateAPIView):
    """Lists and creates department announcements."""

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DeptAnnouncementWriteSerializer
        return DeptAnnouncementSerializer

    queryset = Announcement.objects.none()
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.announcement.view"),
    ]

    def get_queryset(self) -> QuerySet[Announcement]:
        """Returns the queryset of visible announcements."""
        if getattr(self, "swagger_fake_view", False):
            return Announcement.objects.none()
        return visible_announcements(self.request.principal)

    def create(self, request, *args, **kwargs):
        """Creates a new department announcement."""
        # Permission classes are set on the class level, not reassigned here
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        if not data.get('department'):
            raise BadRequestError("Department value is required for announcement creation.")

        announcement = announcement_service.publish(
            actor=request.principal,
            department_id=data['department'],
            title=data['title'],
            body=data['body'],
            target_roles=data['target_roles'],
            target_programme=data.get('target_programme', ''),
            target_batch_year=data.get('target_batch_year'),
        )
        return Response(DeptAnnouncementSerializer(announcement).data, status=201)


@extend_schema(
    summary="Retrieve a specific department announcement",
    responses={
        200: DeptAnnouncementSerializer,
        404: None,
        403: None,
    },
    tags=["Announcements"],
)
class AnnouncementDetailView(APIView):
    """Retrieves a specific department announcement."""
    serializer_class = DeptAnnouncementSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.announcement.view"),
    ]

    def get(self, request, pk):
        """Retrieves the announcement."""
        # Service handles lookup and NotFoundError
        announcement = announcement_service.get(
            actor=request.principal,
            announcement_id=pk,
        )
        serializer = self.serializer_class(announcement)
        return Response(serializer.data)

    def patch(self, request, pk):
        """Updates an existing announcement."""
        # Validate with DeptAnnouncementWriteSerializer
        serializer = DeptAnnouncementWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Call announcement_service.edit
        updated_announcement = announcement_service.edit(
            actor=request.principal,
            announcement_id=pk,
            title=serializer.validated_data['title'],
            body=serializer.validated_data['body'],
            target_roles=serializer.validated_data['target_roles'],
            target_programme=serializer.validated_data.get('target_programme', ''),
            target_batch_year=serializer.validated_data.get('target_batch_year'),
        )
        # Respond with DeptAnnouncementSerializer of the result
        return Response(DeptAnnouncementSerializer(updated_announcement).data)

    def delete(self, request, pk):
        """Deletes an announcement."""
        # Call announcement_service.delete, respond 204
        announcement_service.delete(
            actor=request.principal,
            announcement_id=pk,
        )
        return Response(status=204)


@extend_schema(
    summary="Hide a department announcement",
    responses={
        200: DeptAnnouncementSerializer,
        404: None,
        403: None,
    },
    tags=["Announcements"],
)
class AnnouncementHideView(APIView):
    """Hides a specific announcement."""
    serializer_class = DeptAnnouncementSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.announcement.update"),
    ]

    def post(self, request, pk):
        """Hides the announcement."""
        # Call announcement_service.hide, respond with the read serializer
        announcement = announcement_service.hide(
            actor=request.principal,
            announcement_id=pk,
        )
        serializer = self.serializer_class(announcement)
        return Response(serializer.data)
