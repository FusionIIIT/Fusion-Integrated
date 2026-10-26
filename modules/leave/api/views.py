from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.leave.api.serializers import LeaveRequestSerializer
from modules.leave.models import LeaveRequest


class MyLeaveRequestsView(APIView):
    permission_classes = []

    def get_permissions(self):
        code = "leave.request.create" if self.request.method == "POST" else "leave.request.view_self"
        return [HasPermission(code)()]

    def get(self, request):
        rows = LeaveRequest.objects.filter(employee_user_id=request.principal.user_id)
        return Response(LeaveRequestSerializer(rows, many=True).data)

    def post(self, request):
        serializer = LeaveRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        leave = serializer.save(employee_user_id=request.principal.user_id)
        return Response(LeaveRequestSerializer(leave).data, status=status.HTTP_201_CREATED)


class LeaveApprovalView(APIView):
    permission_classes = [HasPermission("leave.request.approve")]

    def get(self, request):
        rows = LeaveRequest.objects.filter(status="pending")
        return Response(LeaveRequestSerializer(rows, many=True).data)

    def patch(self, request, request_id):
        decision = request.data.get("status")
        if decision not in ("approved", "rejected"):
            return Response({"status": "Choose approved or rejected."},
                            status=status.HTTP_400_BAD_REQUEST)
        updated = LeaveRequest.objects.filter(pk=request_id, status="pending").update(
            status=decision, reviewed_by_user_id=request.principal.user_id,
            reviewer_comment=request.data.get("reviewer_comment", ""),
        )
        if not updated:
            return Response({"detail": "Pending request not found."},
                            status=status.HTTP_404_NOT_FOUND)
        leave = LeaveRequest.objects.get(pk=request_id)
        return Response(LeaveRequestSerializer(leave).data)

