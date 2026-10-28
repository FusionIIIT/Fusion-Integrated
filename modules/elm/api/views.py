"""ELM API endpoints with the same two-gate authorization as Fusion modules.

The IAM integration supplies ``request.principal``. These endpoints deliberately
fail closed when that principal lacks the ELM module grant or action permission.
"""
from rest_framework import generics

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.models import LeaveApplication, LeaveCategory
from modules.elm.api.serializers import (
    LeaveApplicationSerializer,
    LeaveCategorySerializer,
)

ELM_MODULE = HasModuleGrant("elm")
P_VIEW_APPLICATIONS = "elm.application.view"
P_CREATE_APPLICATIONS = "elm.application.create"


class LeaveCategoryListView(generics.ListAPIView):
    queryset = LeaveCategory.objects.all().order_by("name")
    serializer_class = LeaveCategorySerializer
    permission_classes = [ELM_MODULE, HasPermission(P_VIEW_APPLICATIONS)]


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    serializer_class = LeaveApplicationSerializer

    def get_queryset(self):
        # Keep query construction here so employee/role scoping can be added
        # centrally once the specification's actor-scope mapping is wired to
        # the IAM Principal. Never accept a client-supplied status as authority.
        return LeaveApplication.objects.all().order_by("-created_at", "-pk")

    def get_permissions(self):
        action_permission = (
            P_CREATE_APPLICATIONS if self.request.method == "POST"
            else P_VIEW_APPLICATIONS
        )
        return [ELM_MODULE(), HasPermission(action_permission)()]


class LeaveApplicationDetailView(generics.RetrieveAPIView):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer
    permission_classes = [ELM_MODULE, HasPermission(P_VIEW_APPLICATIONS)]
