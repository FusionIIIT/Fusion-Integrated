from django.shortcuts import get_object_or_404
from rest_framework import generics
from .models import LeaveRequest
from .serializers import LeaveRequestSerializer

class LeaveRequestListView(generics.ListAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer

class LeaveRequestDetailView(generics.RetrieveUpdateAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
