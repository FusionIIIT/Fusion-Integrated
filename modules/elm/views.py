
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from fusion_auth.permissions import (
    HasModuleGrant,
    HasPermission,
    IsAuthenticatedPrincipal,
)

from .models import LeaveBalance, LeaveRequest, LeaveType
from .serializers import (
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
)
from .services import (
    apply_leave,
    process_leave_approval,
    process_leave_rejection,
)


# Keep these empty until the ELM permission registry defines the actual codes.
# HasPermission with no codes denies access (fail-closed).
APPROVAL_PERMISSION_CODES = ("elm.application.approve",)
REJECTION_PERMISSION_CODES = ("elm.application.reject",)


class IsLeaveOwner(BasePermission):
    """Object-level protection for employee-owned leave requests."""

    message = "You can access only your own leave requests."

    def has_object_permission(self, request, view, obj):
        principal = getattr(request, "principal", None)
        return principal is not None and obj.user_id == principal.user_id


class ELMBaseViewSet(viewsets.GenericViewSet):
    """Shared authentication and ELM module authorization."""

    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("elm"),
    ]

    # Avoid exposing unsafe PUT, PATCH, and DELETE operations by default.
    http_method_names = ["get", "post", "head", "options"]


class LeaveTypeViewSet(ELMBaseViewSet, viewsets.ReadOnlyModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer


class LeaveBalanceViewSet(ELMBaseViewSet, viewsets.ReadOnlyModelViewSet):
    serializer_class = LeaveBalanceSerializer

    def get_queryset(self):
        principal = self.request.principal
        return LeaveBalance.objects.filter(user_id=principal.user_id)


class LeaveRequestViewSet(ELMBaseViewSet, viewsets.ReadOnlyModelViewSet):
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        principal = self.request.principal

        # Approvers can access requests belonging to their assigned offices.
        if self.action in ("approve", "reject"):
            from .models import OfficeApprover

            assigned_offices = OfficeApprover.objects.filter(
                user_id=principal.user_id,
                is_active=True,
                office__is_active=True,
            ).values_list("office_id", flat=True)

            return LeaveRequest.objects.filter(
                office_id__in=assigned_offices
            )

        # Employees can access only their own leave requests.
        return LeaveRequest.objects.filter(
            user_id=principal.user_id
        )

    def get_permissions(self):
        permissions = list(self.permission_classes)

        if self.action == "approve":
            permissions.append(HasPermission(*APPROVAL_PERMISSION_CODES))
        elif self.action == "reject":
            permissions.append(HasPermission(*REJECTION_PERMISSION_CODES))

        return [permission() for permission in permissions]

    def _submit_leave(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        principal = request.principal
        validated_data = serializer.validated_data

        result = apply_leave(
            user_id=principal.user_id,
            leave_type_id=validated_data["leave_type"].pk,
            start_date_str=validated_data["start_date"],
            end_date_str=validated_data["end_date"],
            reason=validated_data.get("reason", ""),
        )

        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        leave_request = self.get_queryset().get(pk=result["id"])
        response_serializer = self.get_serializer(leave_request)

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    def create(self, request, *args, **kwargs):
        return self._submit_leave(request)

    @action(detail=False, methods=["post"])
    def request_leave(self, request):
        return self._submit_leave(request)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        leave_request = self.get_object()

        result = process_leave_approval(
            request_id=leave_request.pk,
            approver_id=request.principal.user_id,
        )

        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        leave_request = self.get_object()

        result = process_leave_rejection(
            request_id=leave_request.pk,
            approver_id=request.principal.user_id,
            reason=request.data.get("reason"),
        )

        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)
