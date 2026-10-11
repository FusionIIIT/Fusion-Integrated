from rest_framework import viewsets
from elm.models import Leave
from elm.api.serializers import LeaveSerializer

class LeaveViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows leaves to be viewed or edited.
    """
    queryset = Leave.objects.all().order_by('-start_date')
    serializer_class = LeaveSerializer
