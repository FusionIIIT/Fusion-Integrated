from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.leave.api.serializers import LeaveRequestSerializer
from modules.leave.models import LeaveRequest


class MyLeaveRequestsView(APIView):
    permission_classes = []

    def get_permissions(self):
        codes = {
            "GET": ("leave.request.view_self",),
            "POST": ("leave.request.create",),
            "DELETE": ("leave.request.delete",),
        }
        code = codes.get(self.request.method, ("leave.request.view_self",))
        return [HasPermission(*code)()]

    def get(self, request):
        rows = LeaveRequest.objects.filter(employee_user_id=request.principal.user_id)
        return Response(LeaveRequestSerializer(rows, many=True).data)

    def post(self, request):
        serializer = LeaveRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        leave = serializer.save(employee_user_id=request.principal.user_id)
        return Response(LeaveRequestSerializer(leave).data, status=status.HTTP_201_CREATED)

    def delete(self, request, request_id):
        deleted, _ = LeaveRequest.objects.filter(
            pk=request_id, employee_user_id=request.principal.user_id,
            status="pending",
        ).update(status="withdrawn")
        if not deleted:
            return Response({"detail": "Pending request not found."},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeaveApprovalView(APIView):
    permission_classes = [HasPermission("leave.request.approve")]

    def get(self, request):
        # CL/RH are the only categories with a single Unit-Head final decision.
        # Higher-sanction routing needs the configured hierarchy and is not
        # represented by this first workflow slice.
        rows = LeaveRequest.objects.filter(status="pending", leave_type__in=("CL", "RH"))
        return Response(LeaveRequestSerializer(rows, many=True).data)

    def patch(self, request, request_id):
        decision = request.data.get("status")
        if decision not in ("approved", "rejected"):
            return Response({"status": "Choose approved or rejected."},
                            status=status.HTTP_400_BAD_REQUEST)
        comment = request.data.get("reviewer_comment", "")
        if not isinstance(comment, str) or len(comment) > 500:
            return Response({"reviewer_comment": "Must be text of at most 500 characters."},
                            status=status.HTTP_400_BAD_REQUEST)
        leave = LeaveRequest.objects.filter(pk=request_id, status="pending").first()
        if leave is None:
            return Response({"detail": "Pending request not found."},
                            status=status.HTTP_404_NOT_FOUND)
        if leave.leave_type not in ("CL", "RH"):
            return Response({"detail": "This category requires the higher-sanction workflow."},
                            status=status.HTTP_409_CONFLICT)
        updated = LeaveRequest.objects.filter(pk=leave.pk, status="pending").update(
            status=decision, reviewed_by_user_id=request.principal.user_id,
            reviewer_comment=comment,
        )
        if not updated:
            return Response({"detail": "Pending request not found."},
                            status=status.HTTP_404_NOT_FOUND)
        leave.refresh_from_db()
        return Response(LeaveRequestSerializer(leave).data)

