from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListCreateAPIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.department.api.role_assignments_serializers import (
    RoleAssignmentCreateSerializer,
    RoleAssignmentSerializer,
)
from modules.department.models import DepartmentRoleAssignment

# Import specific gate classes
from modules.department.services.role_assignments import record_assignment


@extend_schema(
    summary="List and create department role assignments",
    responses={
        200: RoleAssignmentSerializer,
        201: RoleAssignmentSerializer,
        400: None,  # For validation errors or bad request (e.g., invalid department ID)
        403: None,  # For permission errors
    },
)
class RoleAssignmentListView(ListCreateAPIView):
    """Lists and creates role assignments for departments."""

    def get_serializer_class(self):
        """Returns the appropriate serializer class based on the request method."""
        if self.request.method == 'POST':
            return RoleAssignmentCreateSerializer
        return RoleAssignmentSerializer

    queryset = DepartmentRoleAssignment.objects.none()
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.role_assignment.view"),
    ]

    def get_queryset(self) -> QuerySet[DepartmentRoleAssignment]:
        """Returns the queryset of role assignments, optionally filtered by department_id."""
        if getattr(self, "swagger_fake_view", False):
            return DepartmentRoleAssignment.objects.none()

        department_id = self.request.query_params.get("department")
        if department_id:
            try:
                return DepartmentRoleAssignment.objects.filter(department_id=int(department_id))
            except ValueError:
                raise BadRequestError("Invalid department ID provided.")
        return DepartmentRoleAssignment.objects.all()

    def perform_create(self, serializer):
        """Validates input and records the assignment."""
        if self.request.method == 'POST':
            self.permission_classes = [
                HasModuleGrant("department"),
                HasPermission("department.role_assignment.assign"),
            ]
        try:
            data = serializer.validated_data
            department_id = data['department']

            # Record the assignment using validated values
            record_assignment(
                department_id=department_id,
                role=data['role'],
                user_id=data['user_id'],
                valid_from=data['valid_from'],
                valid_to=data['valid_to'],
                actor=self.request.principal,
            )
        except Exception as e:
            # Catch potential errors during service call and raise BadRequestError if appropriate
            # For simplicity here, we rely on service layer to handle specific errors,
            # but we wrap it to ensure BadRequestError is raised for input/logic issues.
            raise BadRequestError(f"Failed to record role assignment: {e}")
