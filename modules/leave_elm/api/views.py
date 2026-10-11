from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from modules.leave_elm.models import LeaveType, LeaveBalance, LeaveApplication, LeaveAction
from modules.leave_elm.api.serializers import (
    LeaveTypeSerializer,
    LeaveBalanceSerializer,
    LeaveApplicationSerializer,
    LeaveActionSerializer,
)

class LeaveTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer

class LeaveBalanceViewSet(viewsets.ModelViewSet):
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer

class LeaveApplicationViewSet(viewsets.ModelViewSet):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        app = self.get_object()
        app.status = 'WITHDRAWN'
        app.save()
        return Response({'status': 'withdrawn'})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        app = self.get_object()
        app.status = 'APPROVED'
        app.save()
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        app = self.get_object()
        app.status = 'REJECTED'
        app.save()
        return Response({'status': 'rejected'})
