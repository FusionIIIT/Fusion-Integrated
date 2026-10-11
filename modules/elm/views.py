from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .models import LeaveRequest, LeaveBalance, LeaveType, LeavePolicy
from .serializers import LeaveRequestSerializer, LeaveBalanceSerializer, LeaveTypeSerializer, LeavePolicySerializer
from fusion_auth.permissions import HasModuleGrant, HasPermission, IsAuthenticatedPrincipal
from rest_framework import status
from datetime import timedelta
import calendar
from django.utils import timezone
from django.db.models import F


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing leave requests.
    """
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer

    def get_permissions(self):
        """
        Apply role-based access controls.
        """
        if self.action == 'create':
            return [permissions.IsAuthenticated(), HasModuleGrant("elm")(), HasPermission("elm.leave_requests.approve")()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), HasModuleGrant("elm")(), HasPermission("elm.leave_requests.approve")()]
        return [permissions.IsAuthenticated(), HasModuleGrant("elm")(), HasPermission("elm.leave_requests.view")()]

    def create(self, request, *args, **kwargs):
        """
        Handle leave request creation with validation.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Add custom validation logic here
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        Set created_at timestamp and associate with employee.
        """
        serializer.save(employee=self.request.principal.user_id)

    def update(self, request, *args, **kwargs):
        """
        Handle leave request updates with validation.
        """
        instance = self.get_object()
        if instance.status in ['APPROVED', 'CANCELLED']:
            return Response({"error": "Cannot modify approved or cancelled requests"}, status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing leave balances.
    """
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer

    def get_permissions(self):
        """
        Apply role-based access controls.
        """
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), HasModuleGrant("elm")(), HasPermission("elm.leave_balances.manage")()]
        return [permissions.IsAuthenticated(), HasModuleGrant("elm")(), HasPermission("elm.leave_balances.view")()]

    def perform_update(self, serializer):
        """
        Update leave balance with proper accounting.
        """
        instance = self.get_object()
        # Example: Deduct balance for approved leave
        if serializer.validated_data.get('approved', False):
            instance.balance = F('balance') - serializer.validated_data.get('days', 0)
            instance.save(update_fields=['balance'])


class LeaveTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing leave types.
    """
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm"), HasPermission("elm.leave_types.view"), HasPermission("elm.leave_policies.manage")]


class LeavePolicyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing leave policies.
    """
    queryset = LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm"), HasPermission("elm.leave_policies.view"), HasPermission("elm.leave_policies.manage")]

    def get_queryset(self):
        """
        Filter policies by leave type if specified.
        """
        queryset = super().get_queryset()
        type_filter = self.request.query_params.get('type')
        if type_filter:
            queryset = queryset.filter(type=type_filter)
        return queryset

# Add year-end processing and SLA reminder logic here
