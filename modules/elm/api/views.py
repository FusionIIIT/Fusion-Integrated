from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from modules.elm.models import LeaveType, LeaveBalance, LeaveRequest, ActionLog
from modules.elm.services.leave_service import submit_leave_request, respond_substitute, process_approval, withdraw_leave_request
from modules.elm.api.serializers import LeaveTypeSerializer, LeaveBalanceSerializer, LeaveRequestSerializer, ActionLogSerializer

class LeaveTypeListView(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveType.objects.filter(is_active=True)
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]

class LeaveBalanceListView(viewsets.ReadOnlyModelViewSet):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return LeaveBalance.objects.filter(user=user)

class LeaveRequestListCreateView(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return LeaveRequest.objects.filter(applicant=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave_request = submit_leave_request(serializer.validated_data)
        headers = self.get_success_headers(serializer.data)
        return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_201_CREATED, headers=headers)

class LeaveRequestDetailView(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return LeaveRequest.objects.filter(applicant=user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return Response(serializer.data)

class SubstituteResponseView(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave_request = respond_substitute(serializer.validated_data)
        headers = self.get_success_headers(serializer.data)
        return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_201_CREATED, headers=headers)

class LeaveApprovalActionView(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave_request = process_approval(serializer.validated_data)
        headers = self.get_success_headers(serializer.data)
        return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_201_CREATED, headers=headers)

class LeaveWithdrawView(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave_request = withdraw_leave_request(serializer.validated_data)
        headers = self.get_success_headers(serializer.data)
        return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_201_CREATED, headers=headers)