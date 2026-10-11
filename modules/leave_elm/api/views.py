import json
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave_elm.models import LeaveRequest, LeaveAction, LeaveBalance, Holiday, VacationPeriod

class MyRequestsView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.request.view_self", "leave_elm.request.create"),
    ]
    def get(self, request):
        employee_id = request.user.user_id
        requests = LeaveRequest.objects.filter(employee_id=employee_id)
        data = [model_to_dict(request) for request in requests]
        return Response(json.loads(json.dumps(data, cls=DjangoJSONEncoder)))

    def post(self, request):
        data = request.data
        category = data['category']
        start_date = data['start_date']
        end_date = data['end_date']
        purpose = data['purpose']
        station_leave = data['station_leave']
        half_day = data['half_day']
        substitute_employee_id = data['substitute_employee_id']
        requested_days = data['requested_days']
        employee_id = request.user.user_id
        request_status = 'P'
        new_request = LeaveRequest(category=category, start_date=start_date, end_date=end_date, purpose=purpose, station_leave=station_leave, half_day=half_day, substitute_employee_id=substitute_employee_id, requested_days=requested_days, employee_id=employee_id, status=request_status)
        new_request.save()
        return Response(model_to_dict(new_request), status=status.HTTP_201_CREATED)

class RequestDetailView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.request.view_self"),
    ]
    def get(self, request, pk):
        employee_id = request.user.user_id
        try:
            request = LeaveRequest.objects.get(pk=pk, employee_id=employee_id)
            data = model_to_dict(request)
            return Response(json.loads(json.dumps(data, cls=DjangoJSONEncoder)))
        except LeaveRequest.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        employee_id = request.user.user_id
        try:
            request = LeaveRequest.objects.get(pk=pk, employee_id=employee_id)
            request.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except LeaveRequest.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class RequestActionView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.request.decide"),
    ]
    def post(self, request, pk):
        data = request.data
        action = data['action']
        comment = data.get('comment', None)
        try:
            leave_request = LeaveRequest.objects.get(pk=pk)
            old_status = leave_request.status
            if action == 'A':
                leave_request.status = 'A'
                leave_request.save()
            elif action == 'R':
                leave_request.status = 'R'
                leave_request.save()
            if comment:
                new_action = LeaveAction(request=leave_request, actor_id=request.user.user_id, action=action, from_status=old_status, to_status=leave_request.status, comment=comment)
                new_action.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except LeaveRequest.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class BalancesView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.request.view_self"),
    ]
    def get(self, request):
        employee_id = request.user.user_id
        balances = LeaveBalance.objects.filter(employee_id=employee_id)
        data = [model_to_dict(balance) for balance in balances]
        return Response(json.loads(json.dumps(data, cls=DjangoJSONEncoder)))

class CalendarView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.request.view_self"),
    ]
    def get(self, request):
        holidays = Holiday.objects.filter(published=True)
        data = [model_to_dict(holiday) for holiday in holidays]
        vacation_periods = VacationPeriod.objects.filter(published=True)
        data.extend([model_to_dict(period) for period in vacation_periods])
        return Response(json.loads(json.dumps(data, cls=DjangoJSONEncoder)))
