from rest_framework import permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import Http404
from django.utils import timezone
import datetime

from fusion_auth.permissions import HasModuleGrant, HasPermission

from ..models import LeaveBalance, LeaveRequest, LeaveStatus
from ..serializers import LeaveBalanceSerializer, LeaveRequestSerializer


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer
    permission_classes = [HasModuleGrant("leave_cell")]

    def get_permissions(self):
        perms = [HasModuleGrant("leave_cell")]
        perms.append(HasPermission("leave_cell.balances.view", "leave_cell.balances.view_all"))
        return [p() for p in perms]

    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        if principal is None or not principal.has_permission("leave_cell.balances.view_all"):
            if principal is None or not getattr(principal, "username", None):
                return LeaveBalance.objects.none()
            return LeaveBalance.objects.filter(employee_id=principal.username)
        return LeaveBalance.objects.all()


class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [HasModuleGrant("leave_cell")]

    http_method_names = ["get", "post"]

    def get_permissions(self):
        perms = [HasModuleGrant("leave_cell")]
        if self.action in ["list", "retrieve"]:
            perms.append(
                HasPermission(
                    "leave_cell.requests.manage",
                    "leave_cell.requests.view_all",
                )
            )
        elif self.action in ["create", "withdraw", "cancel"]:
            perms.append(HasPermission("leave_cell.requests.manage"))
        elif self.action in ["approve", "reject"]:
            perms.append(
                HasPermission(
                    "leave_cell.requests.sanction",
                    "leave_cell.requests.view_all",
                )
            )
        return [p() for p in perms]

    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        if principal is None or not principal.has_permission("leave_cell.requests.view_all"):
            if principal is None or not getattr(principal, "username", None):
                return LeaveRequest.objects.none()
            return LeaveRequest.objects.filter(employee_id=principal.username)
        return LeaveRequest.objects.all()

    def perform_create(self, serializer):
        principal = getattr(self.request, "principal", None)
        if principal is None or not getattr(principal, "username", None):
            raise permissions.PermissionDenied("Principal username missing")
        serializer.save(employee_id=principal.username)

    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        principal = getattr(request, "principal", None)
        if principal is None or not getattr(principal, "username", None):
            raise PermissionDenied("Principal username missing")

        try:
            with transaction.atomic():
                leave_request = LeaveRequest.objects.select_for_update().get(
                    pk=pk, employee_id=principal.username
                )
                if leave_request.status != LeaveStatus.PENDING:
                    raise ValidationError("Only pending requests can be withdrawn.")
                leave_request.status = LeaveStatus.WITHDRAWN
                leave_request.save(update_fields=["status", "updated_at"])
                serializer = LeaveRequestSerializer(leave_request)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except LeaveRequest.DoesNotExist:
            raise Http404

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """Cancel an approved leave before it commences (BR-EL-023)."""
        principal = getattr(request, "principal", None)
        if principal is None or not getattr(principal, "username", None):
            raise PermissionDenied("Principal username missing")

        try:
            with transaction.atomic():
                leave_request = LeaveRequest.objects.select_for_update().get(
                    pk=pk, employee_id=principal.username
                )
                if leave_request.status != LeaveStatus.APPROVED:
                    raise ValidationError("Only approved requests can be cancelled.")

                # Must be before start date
                today = timezone.localdate() if hasattr(timezone, "localdate") else datetime.date.today()
                if leave_request.start_date < today:
                    raise ValidationError("Cannot cancel leave that has already commenced.")

                # Restore balance if present
                bal = LeaveBalance.objects.select_for_update().filter(
                    employee_id=leave_request.employee_id,
                    leave_type=leave_request.leave_type,
                ).first()
                if bal:
                    bal.balance += leave_request.duration()
                    bal.save(update_fields=["balance", "last_updated"])

                leave_request.status = LeaveStatus.CANCELLED
                leave_request.save(update_fields=["status", "updated_at"])
                serializer = LeaveRequestSerializer(leave_request)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except LeaveRequest.DoesNotExist:
            raise Http404

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        """Approve a pending leave request and debit balance (BR-EL-016/017/018)."""
        principal = getattr(request, "principal", None)
        if principal is None or not getattr(principal, "username", None):
            raise PermissionDenied("Principal username missing")

        try:
            with transaction.atomic():
                leave_request = LeaveRequest.objects.select_for_update().get(pk=pk)
                if leave_request.status != LeaveStatus.PENDING:
                    raise ValidationError("Only pending requests can be approved.")

                # Debit balance
                duration = leave_request.duration()
                bal = LeaveBalance.objects.select_for_update().filter(
                    employee_id=leave_request.employee_id,
                    leave_type=leave_request.leave_type,
                ).first()
                if bal:
                    if bal.balance < duration:
                        raise ValidationError(
                            f"Insufficient balance to approve ({bal.balance} available, {duration} needed)."
                        )
                    bal.balance -= duration
                    bal.save(update_fields=["balance", "last_updated"])

                leave_request.status = LeaveStatus.APPROVED
                leave_request.save(update_fields=["status", "updated_at"])
                serializer = LeaveRequestSerializer(leave_request)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except LeaveRequest.DoesNotExist:
            raise Http404

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        """Reject a pending leave request with an optional reason."""
        principal = getattr(request, "principal", None)
        if principal is None or not getattr(principal, "username", None):
            raise PermissionDenied("Principal username missing")

        reason = request.data.get("reason", "") if request.data else ""

        try:
            with transaction.atomic():
                leave_request = LeaveRequest.objects.select_for_update().get(pk=pk)
                if leave_request.status != LeaveStatus.PENDING:
                    raise ValidationError("Only pending requests can be rejected.")

                leave_request.status = LeaveStatus.REJECTED
                leave_request.rejection_reason = reason
                leave_request.save(update_fields=["status", "rejection_reason", "updated_at"])
                serializer = LeaveRequestSerializer(leave_request)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except LeaveRequest.DoesNotExist:
            raise Http404
