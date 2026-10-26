"""Working self-service endpoints for the first ELM vertical slice."""
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant
from ..models import LeaveApplication, LeaveCategory
from .serializers import LeaveApplicationSerializer, LeaveTypeListSerializer


ELM_MODULE = HasModuleGrant("elm_leave")


class LeaveTypeListView(APIView):
    """Expose supported leave categories without implying entitlement checks."""

    permission_classes = [ELM_MODULE]

    @extend_schema(responses=LeaveTypeListSerializer)
    def get(self, request):
        return Response({
            "results": [
                {"code": code, "label": label}
                for code, label in LeaveCategory.choices
            ],
        })


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    """Authenticated self-service list/create API; no staff-wide reads or edits."""

    permission_classes = [ELM_MODULE]
    serializer_class = LeaveApplicationSerializer
    throttle_scope = "apply"

    def get_queryset(self):
        actor = getattr(self.request, "principal", None)
        if actor is None:
            return LeaveApplication.objects.none()
        return LeaveApplication.objects.filter(user_id=actor.user_id).order_by("-id")

    def perform_create(self, serializer):
        # Never accept user_id or status from the request payload.
        serializer.save(user_id=self.request.principal.user_id)
