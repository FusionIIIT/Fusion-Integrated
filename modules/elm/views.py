from rest_framework import generics
from .models import LeaveType, LeaveRequest
from .serializers import LeaveTypeSerializer, LeaveRequestSerializer

class LeaveTypeListCreateView(generics.ListCreateAPIView):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer

class LeaveTypeRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer

class LeaveRequestListCreateView(generics.ListCreateAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer

class LeaveRequestRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
