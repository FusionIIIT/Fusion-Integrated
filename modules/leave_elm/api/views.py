from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.leave_elm.api.serializers import LeaveApplicationSerializer


@extend_schema(responses=LeaveApplicationSerializer)
class LeaveApplicationView(APIView):
    """View to list leave applications - protected by leave_elm.application.view."""

    permission_classes = [HasPermission("leave_elm.application.view")]
    serializer_class = LeaveApplicationSerializer

    def get(self, request):
        return Response({"message": "Leave applications view"})


@extend_schema(responses=LeaveApplicationSerializer)
class LeaveApplyView(APIView):
    """View to submit leave application - protected by leave_elm.application.apply."""

    permission_classes = [HasPermission("leave_elm.application.apply")]
    serializer_class = LeaveApplicationSerializer

    def post(self, request):
        return Response({"message": "Leave applied"})


@extend_schema(responses=LeaveApplicationSerializer)
class LeaveApproveView(APIView):
    """View to approve/reject leave application - protected by leave_elm.application.approve."""

    permission_classes = [HasPermission("leave_elm.application.approve")]
    serializer_class = LeaveApplicationSerializer

    def post(self, request):
        return Response({"message": "Leave approved"})
