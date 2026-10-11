from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasPermission
from modules.elm.models import LeaveType, LeaveBalance, LeaveApplication
from modules.elm.api.serializers import LeaveTypeSerializer, LeaveBalanceSerializer, LeaveApplicationSerializer


class LeaveTypeListView(APIView):
    permission_classes = [HasPermission("elm.leave_type.view")]

    def get(self, request):
        leave_types = LeaveType.objects.filter(is_active=True)
        serializer = LeaveTypeSerializer(leave_types, many=True)
        return Response(serializer.data)


class LeaveBalanceListView(APIView):
    permission_classes = [HasPermission("elm.balance.view")]

    def get(self, request):
        user_id = request.user.user_id
        balances = LeaveBalance.objects.filter(employee_id=user_id)
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)


class LeaveApplicationListView(APIView):
    permission_classes = [HasPermission("elm.application.view")]

    def get(self, request):
        user_id = request.user.user_id
        applications = LeaveApplication.objects.filter(applicant_id=user_id)
        serializer = LeaveApplicationSerializer(applications, many=True)
        return Response(serializer.data)


class LeaveApplicationCreateView(APIView):
    permission_classes = [HasPermission("elm.application.create")]

    def post(self, request):
        user_id = request.user.user_id
        data = request.data.copy()
        data["applicant_id"] = user_id
        data["status"] = "PENDING"
        serializer = LeaveApplicationSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        raise BadRequestError("Invalid data", code="invalid_data")


class LeaveApplicationWithdrawView(APIView):
    permission_classes = [HasPermission("elm.application.delete")]

    def post(self, request, pk):
        user_id = request.user.user_id
        try:
            application = LeaveApplication.objects.get(pk=pk, applicant_id=user_id, status="PENDING")
        except LeaveApplication.DoesNotExist:
            raise BadRequestError("Application not found or not pending", code="application_not_found_or_pending")

        application.status = "WITHDRAWN"
        application.save()
        return Response(LeaveApplicationSerializer(application).data)
