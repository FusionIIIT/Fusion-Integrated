from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    LeaveRequestSerializer,
    LeaveRequestSubmissionSerializer,
)
from modules.elm.selectors.request_selector import LeaveRequestSelector
from modules.elm.services.leave_request_service import LeaveRequestService


MODULE = HasModuleGrant("leave")
P_SUBMIT = "leave.request.create"
P_VIEW_SELF = "leave.request.view_self"


def _actor(request):
    return request.principal


class LeaveRequestSubmitView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUBMIT)]

    def post(self, request):
        payload = LeaveRequestSubmissionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        try:
            leave_request = LeaveRequestService.submit_request(
                user_id=_actor(request).user_id,
                **payload.validated_data,
            )
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})

        return Response(
            LeaveRequestSerializer(leave_request).data,
            status=status.HTTP_201_CREATED,
        )


class MyLeaveRequestsView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        rows = LeaveRequestSelector.for_user(_actor(request).user_id)
        return Response({
            "results": LeaveRequestSerializer(rows, many=True).data,
        })
