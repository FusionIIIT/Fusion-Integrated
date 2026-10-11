"""Permission-gated leave API; ownership is applied before lookup."""
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission
from .models import Employee, LeaveRequest
from .serializers import LeaveRequestSerializer


class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        # Every operation requires both module access and the operation-specific grant.
        if self.action in ("list", "retrieve"):
            fine = HasPermission("elm.leave.view_all", "elm.leave.view_self")
        elif self.action == "create":
            fine = HasPermission("elm.leave.submit")
        elif self.action == "approve":
            fine = HasPermission("elm.leave.approve")
        elif self.action == "reject":
            fine = HasPermission("elm.leave.reject")
        elif self.action == "cancel":
            fine = HasPermission("elm.leave.cancel", "elm.leave.submit")
        else:
            fine = HasPermission("elm.leave.view_all")
        return [IsAuthenticated(), HasModuleGrant("elm"), fine]

    def get_queryset(self):
        qs = LeaveRequest.objects.select_related("employee")
        principal = getattr(self.request, "principal", None)
        if principal is None:
            return qs.none()
        if principal.has_permission("elm.leave.view_all"):
            return qs
        return qs.filter(employee__user_id=principal.user_id)

    def create(self, request, *args, **kwargs):
        principal = getattr(request, "principal", None)
        employee = Employee.objects.filter(user_id=principal.user_id).first()
        if employee is None:
            raise ValidationError({
                "employee": "No employee profile is linked to your IAM account. Contact HR."
            })
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave = serializer.save(employee=employee)
        return Response(self.get_serializer(leave).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied("Leave requests cannot be edited after submission.")

    def perform_destroy(self, instance):
        raise PermissionDenied("Leave requests cannot be deleted; use the cancel action.")

    def _transition(self, request, target_status, permission):
        principal = getattr(request, "principal", None)
        if not principal or not principal.has_permission(permission):
            raise PermissionDenied("You do not have permission to perform this action.")
        leave = self.get_object()
        if leave.status != LeaveRequest.STATUS_PENDING:
            raise ValidationError({"status": "Only pending leave requests can be decided."})
        leave.status = target_status
        leave.decision_note = str(request.data.get("note", "")).strip()
        leave.decided_by_id = getattr(getattr(request, "principal", None), "user_id", None)
        leave.save(update_fields=("status", "decision_note", "decided_by_id", "updated_at"))
        return Response(self.get_serializer(leave).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._transition(request, LeaveRequest.STATUS_APPROVED, "elm.leave.approve")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._transition(request, LeaveRequest.STATUS_REJECTED, "elm.leave.reject")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        leave = self.get_object()
        principal = getattr(request, "principal", None)
        if not principal or not (
            principal.has_permission("elm.leave.cancel")
            or (leave.employee.user_id == principal.user_id
                and leave.status == LeaveRequest.STATUS_PENDING)
        ):
            raise PermissionDenied("You cannot cancel this leave request.")
        if leave.status not in (LeaveRequest.STATUS_PENDING, LeaveRequest.STATUS_APPROVED):
            raise ValidationError({"status": "This leave request cannot be canceled."})
        leave.status = LeaveRequest.STATUS_CANCELED
        leave.save(update_fields=("status", "updated_at"))
        return Response(self.get_serializer(leave).data)
