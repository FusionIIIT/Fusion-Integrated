from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from modules.elm.api.permissions import ScopedCollection
from modules.elm.api.serializers import LeaveRequestSerializer, LeaveDecisionSerializer
from modules.elm.services import submit_leave_request, withdraw_leave_request, get_balance

class LeaveRequestListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, ScopedCollection("elm.leave.apply")]
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        return self.request.principal.leave_requests.filter(user=self.request.principal.user_id)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class LeaveRequestDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, ScopedCollection("elm.leave.view_self")]
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        return self.request.principal.leave_requests.filter(user=self.request.principal.user_id)

class LeaveRequestWithdrawView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, ScopedCollection("elm.leave.withdraw")]
    serializer_class = LeaveDecisionSerializer

    def get_queryset(self):
        return self.request.principal.leave_requests.filter(user=self.request.principal.user_id)

    def create(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class BalanceView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LeaveDecisionSerializer  # Corrected the serializer class

    def get(self, request, *args, **kwargs):
        year = request.query_params.get('year')
        if not year.isdigit():
            return Response({"error": "Invalid year"}, status=status.HTTP_400_BAD_REQUEST)
        balance = get_balance(user_id=request.principal.user_id, year=int(year))
        return Response(balance)
