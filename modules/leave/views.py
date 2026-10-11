from rest_framework import viewsets
from .models import LeaveApplication
from .serializers import LeaveApplicationSerializer

class LeaveApplicationViewSet(viewsets.ModelViewSet):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer
