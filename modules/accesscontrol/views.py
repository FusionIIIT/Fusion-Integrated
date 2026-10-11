from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .models import LeaveType, LeaveBalance, LeaveApplication, SubstituteNominee
from .serializers import LeaveTypeSerializer, LeaveBalanceSerializer, LeaveApplicationSerializer, SubstituteNomineeSerializer
from directory.models import UserRef
from directory.services import get_user_ref

class LeaveTypeListView(generics.ListAPIView):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

class LeaveBalanceListView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_ref = get_user_ref(self.request.user)
        return LeaveBalance.objects.filter(user=user_ref)

class LeaveApplicationListView(generics.ListCreateAPIView):
    serializer_class = LeaveApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_ref = get_user_ref(self.request.user)
        return LeaveApplication.objects.filter(user=user_ref)

    def perform_create(self, serializer):
        user_ref = get_user_ref(self.request.user)
        serializer.save(user=user_ref)

class SubstituteNomineeListView(generics.ListCreateAPIView):
    serializer_class = SubstituteNomineeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_ref = get_user_ref(self.request.user)
        return SubstituteNominee.objects.filter(application__user=user_ref)

    def perform_create(self, serializer):
        user_ref = get_user_ref(self.request.user)
        application = LeaveApplication.objects.get(user=user_ref, id=self.request.data['leave_application'])
        serializer.save(application=application)
