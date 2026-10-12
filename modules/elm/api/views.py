from rest_framework import viewsets

from core.api.exceptions import ConflictError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.models import LeaveRequest, LeaveStatus

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

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.principal.user_id)

    def perform_update(self, serializer):
        if serializer.instance.status != LeaveStatus.PENDING:
            raise ConflictError('Only a pending leave request can be changed.')
        serializer.save()
