from rest_framework import generics, status
from rest_framework.response import Response

from modules.elm.models import LeaveRequest
from modules.elm.api.serializers import LeaveRequestSerializer


class LeaveRequestListView(generics.ListCreateAPIView):
    """List and create leave requests."""
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class LeaveRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific leave request."""
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
