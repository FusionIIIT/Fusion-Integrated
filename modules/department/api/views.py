from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.department.api.serializers import DepartmentSerializer
from modules.department.models.departments import Department
from modules.department.selectors.scoping import visible_departments
from modules.department.services.authz import require

MAX_LIMIT = 20

@extend_schema(
    summary="List all visible departments",
    responses={200: DepartmentSerializer, 403: None},
)
class DepartmentListView(ListAPIView):
    """Lists departments visible to the actor based on their role and membership."""

    serializer_class = DepartmentSerializer
    queryset = Department.objects.none()

    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.department.view"),
    ]

    def get_queryset(self) -> QuerySet[Department]:
        """Returns the queryset of departments visible to the current actor."""
        if getattr(self, "swagger_fake_view", False):
            return Department.objects.none()
        actor = self.request.principal
        require(actor, "department.department.view")
        return visible_departments(actor)
