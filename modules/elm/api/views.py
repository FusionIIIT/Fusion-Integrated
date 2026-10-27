from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api.exceptions import ConflictError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.models import LeaveRequest, LeaveRequestEvent, LeaveStatus
from modules.elm.services import leave_requests

from .serializers import LeaveRequestSerializer

P_VIEW = 'elm.leave_request.view'
P_MANAGE = 'elm.leave_request.manage'


class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    queryset = LeaveRequest.objects.none()

    def get_permissions(self):
        code = P_VIEW if self.request.method in ('GET', 'HEAD', 'OPTIONS') else P_MANAGE
        return [HasModuleGrant('elm')(), HasPermission(code)()]

    def get_queryset(self):
        # Own rows only, so someone else's request is a 404, not a 403.
        principal = getattr(self.request, 'principal', None)
        if principal is None:
            return LeaveRequest.objects.none()
        return LeaveRequest.objects.filter(user_id=principal.user_id)

    @transaction.atomic
    def perform_create(self, serializer):
        data = serializer.validated_data
        leave_requests.ensure_no_overlap(
            user_id=self.request.principal.user_id,
            category=data["category"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            day_part=data["day_part"],
        )
        leave_request = serializer.save(user_id=self.request.principal.user_id)
        LeaveRequestEvent.objects.create(
            request=leave_request,
            event_type=LeaveRequestEvent.Type.SUBMITTED,
            to_status=LeaveStatus.PENDING,
            actor_user_id=self.request.principal.user_id,
        )

    def perform_update(self, serializer):
        raise ConflictError(
            'Submitted leave requests cannot be changed. '
            'Withdraw the pending request and submit a new one instead.')

    def perform_destroy(self, instance):
        raise ConflictError(
            'Leave requests cannot be deleted. Withdraw a pending request instead.')

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        leave_request = self.get_object()
        withdrawn = leave_requests.withdraw(
            request_id=leave_request.pk,
            user_id=request.principal.user_id,
        )
        return Response(self.get_serializer(withdrawn).data)
