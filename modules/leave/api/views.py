from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, IsAuthenticatedPrincipal
from modules.leave.api.serializers import (
    LeaveApplicationSerializer,
    LeaveBalanceSerializer,
    LeaveReviewSerializer,
)
from modules.leave.models import LeaveApplication, LeaveBalance


class LeaveBalanceListView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]
    serializer_class = LeaveBalanceSerializer

    def get(self, request):
        user_id = request.principal.user_id
        if "leave_elm.application.view" not in request.principal.permissions:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        balances = LeaveBalance.objects.filter(user_id=user_id)
        if not balances.exists():
            defaults = [
                ("CL", 8),
                ("RH", 2),
                ("SCL", 15),
                ("EL", 30),
                ("COL", 20),
                ("VL", 60),
            ]
            for ltype, alloc in defaults:
                LeaveBalance.objects.create(
                    user_id=user_id,
                    leave_type=ltype,
                    year=2026,
                    allocated=alloc,
                    used=0,
                )
            balances = LeaveBalance.objects.filter(user_id=user_id)

        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeaveApplicationListCreateView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]
    serializer_class = LeaveApplicationSerializer

    def get(self, request):
        user_id = request.principal.user_id
        if "leave_elm.application.approve" in request.principal.permissions:
            applications = LeaveApplication.objects.all().order_by("-created_at")
        else:
            applications = LeaveApplication.objects.filter(user_id=user_id).order_by("-created_at")

        serializer = LeaveApplicationSerializer(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if "leave_elm.application.apply" not in request.principal.permissions:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        serializer = LeaveApplicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user_id=request.principal.user_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LeaveApplicationReviewView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]
    serializer_class = LeaveReviewSerializer

    def post(self, request, pk):
        if "leave_elm.application.approve" not in request.principal.permissions:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        application = LeaveApplication.objects.get(pk=pk)
        action = request.data.get("action", "APPROVE")
        application.status = "APPROVED" if action == "APPROVE" else "REJECTED"
        application.reviewed_by = request.principal.user_id
        application.review_remarks = request.data.get("remarks", "")
        application.save()

        if application.status == "APPROVED":
            balance = LeaveBalance.objects.filter(
                user_id=application.user_id, leave_type=application.leave_type
            ).first()
            if balance:
                balance.used += application.days
                balance.save()

        serializer = LeaveApplicationSerializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)
