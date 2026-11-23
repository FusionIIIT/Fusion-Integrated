
from rest_framework import generics
from modules.leave_elm.models import LeavePolicy, LeaveCalendar, LeaveType, LeaveHistory, LeaveNotification
from modules.leave_elm.api.serializers import LeavePolicySerializer, LeaveCalendarSerializer
from .record_serializers import LeaveHistorySerializer, LeaveNotificationSerializer
from fusion_auth.permissions import HasModuleGrant, HasPermission
import json
from rest_framework.response import Response

class ConfigurationView(generics.ListCreateAPIView):
    permission_classes = [HasModuleGrant("leave_elm"), HasPermission("leave_elm.configuration.manage")]
    queryset = LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.principal.user_id)

def save_configuration(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        policy_serializer = LeavePolicySerializer(data=data['policy'])
        calendar_serializer = LeaveCalendarSerializer(data=data['calendar'])

        if policy_serializer.is_valid() and calendar_serializer.is_valid():
            policy_serializer.save(user=request.principal.user_id)
            calendar_serializer.save(user=request.principal.user_id)

            response_data = {
                'policy': policy_serializer.data,
                'calendar': calendar_serializer.data
            }

            return Response(response_data, status=201)
        else:
            return Response(policy_serializer.errors or calendar_serializer.errors, status=400)

class RecordListView(generics.ListAPIView):
    permission_classes = [HasModuleGrant("leave_elm"), HasPermission("leave_elm.record.manage")]
    queryset = LeaveHistory.objects.all()
    serializer_class = LeaveHistorySerializer

    def get_queryset(self):
        return self.queryset.filter(leave_application__user=self.request.principal.user_id)

def record_view(request):
    history_query = LeaveHistory.objects.filter(leave_application__user=request.principal.user_id)
    notifications_query = LeaveNotification.objects.filter(leave_application__user=request.principal.user_id)

    history_serializer = LeaveHistorySerializer(history_query, many=True)
    notifications_serializer = LeaveNotificationSerializer(notifications_query, many=True)

    return Response({'history': history_serializer.data, 'notifications': notifications_serializer.data})