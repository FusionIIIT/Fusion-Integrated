from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.department.api import serializers as s
from modules.department.services import announcements as announcement_service


MODULE = HasModuleGrant("department")

P_PUBLISH = "department.announcement.publish"
P_MANAGE = "department.announcement.manage"


def _actor(request):
    return getattr(request, "principal", None)


@extend_schema(
    request=s.AnnouncementDraftSerializer,
    responses={201: s.AnnouncementSerializer},
)
class AnnouncementDraftCreateView(APIView):
    permission_classes = [MODULE, HasPermission(P_PUBLISH)]

    def post(self, request):
        payload = s.AnnouncementDraftSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        announcement = announcement_service.create_draft(
            actor=_actor(request),
            **payload.validated_data,
        )

        return Response(
            s.AnnouncementSerializer(announcement).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    request=s.AnnouncementPublishSerializer,
    responses={200: s.AnnouncementSerializer},
)
class AnnouncementPublishView(APIView):
    permission_classes = [MODULE, HasPermission(P_PUBLISH)]

    def post(self, request, pk):
        payload = s.AnnouncementPublishSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        announcement = announcement_service.publish(
            actor=_actor(request),
            announcement_id=pk,
            **payload.validated_data,
        )

        return Response(
            s.AnnouncementSerializer(announcement).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(
    request=None,
    responses={200: s.AnnouncementSerializer},
)
class AnnouncementHideView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def post(self, request, pk):
        announcement = announcement_service.hide(
            actor=_actor(request),
            announcement_id=pk,
        )

        return Response(
            s.AnnouncementSerializer(announcement).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(
    request=None,
    responses={204: None},
)
class AnnouncementDeleteView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def delete(self, request, pk):
        announcement_service.soft_delete(
            actor=_actor(request),
            announcement_id=pk,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
