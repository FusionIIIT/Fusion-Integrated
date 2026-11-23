from rest_framework import generics
from modules.leave.models import LeaveApplication
from modules.leave.serializers import LeaveApplicationSerializer

class LeaveApplicationListView(generics.ListCreateAPIView):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer

class LeaveApplicationDetailView(generics.RetrieveUpdateAPIView):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer
