from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import VisitRequest, VisitorPass
from .serializers import VisitRequestSerializer, VisitorPassSerializer


class VisitRequestListCreateView(APIView):
    """
    List visitor requests or create a new visitor request.
    """

    def get(self, request):
        visit_requests = VisitRequest.objects.all().order_by("-created_at")
        serializer = VisitRequestSerializer(visit_requests, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = VisitRequestSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class VisitRequestDetailView(APIView):
    """
    Retrieve a visitor request.
    """

    def get(self, request, pk):
        try:
            visit_request = VisitRequest.objects.get(pk=pk)
        except VisitRequest.DoesNotExist:
            return Response(
                {"error": "Visit request not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = VisitRequestSerializer(visit_request)
        return Response(serializer.data)


class VisitorPassListView(APIView):
    """
    List visitor passes.
    """

    def get(self, request):
        passes = VisitorPass.objects.all().order_by("-id")
        serializer = VisitorPassSerializer(passes, many=True)
        return Response(serializer.data)