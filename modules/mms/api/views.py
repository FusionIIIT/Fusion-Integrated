from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import RegistrationRequest, DeregistrationRequest, RebateRequest, SpecialFoodRequest, MenuItem

class RegistrationView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        req = RegistrationRequest.objects.create(
            student=request.user,
            window_id=request.data.get('window_id')
        )
        return Response({"id": req.id, "status": req.status}, status=status.HTTP_201_CREATED)

class RebateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        rebate = RebateRequest.objects.create(
            student=request.user,
            reason=request.data.get('reason'),
            explanation=request.data.get('explanation', ''),
            start_date=request.data.get('start_date'),
            end_date=request.data.get('end_date')
        )
        return Response({"id": rebate.id, "status": rebate.status}, status=status.HTTP_201_CREATED)

class SpecialFoodView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        sf = SpecialFoodRequest.objects.create(
            student=request.user,
            reason=request.data.get('reason'),
            requested_date=request.data.get('requested_date')
        )
        return Response({"id": sf.id, "status": sf.status}, status=status.HTTP_201_CREATED)

class MenuView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        return Response(list(MenuItem.objects.values()))