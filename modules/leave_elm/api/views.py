
from rest_framework.views import APIView
from rest_framework.response import Response
from modules.leave_elm.services.queries import list_applications, own_balances, assigned_tasks
from modules.leave_elm.services.applications import submit_application
from modules.leave_elm.services.actions import act_on_application
from .serializers import LeaveApplicationSerializer, LeaveBalanceSerializer, LeaveTaskSerializer
from fusion_auth.permissions import IsAuthenticatedPrincipal, HasModuleGrant, HasPermission
import datetime

class ApplicationListView(APIView):
    def get(self, request):
        if not isinstance(request.principal, IsAuthenticatedPrincipal):
            return Response({'error': 'Authentication is required.'}, status=401)
        applications = list_applications(request.principal)
        serializer = LeaveApplicationSerializer(applications, many=True)
        return Response(serializer.data)

class BalanceListView(APIView):
    def get(self, request):
        if not isinstance(request.principal, IsAuthenticatedPrincipal):
            return Response({'error': 'Authentication is required.'}, status=401)
        balances = own_balances(request.principal)
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)

class TaskListView(APIView):
    def get(self, request):
        if not isinstance(request.principal, IsAuthenticatedPrincipal):
            return Response({'error': 'Authentication is required.'}, status=401)
        tasks = assigned_tasks(request.principal)
        serializer = LeaveTaskSerializer(tasks, many=True)
        return Response(serializer.data)

class ApplicationActionView(APIView):
    permission_classes = [HasModuleGrant('leave_elm'), HasPermission('leave_elm.application.create')]

    def post(self, request, pk=None):
        if not isinstance(request.principal, IsAuthenticatedPrincipal):
            return Response({'error': 'Authentication is required.'}, status=401)
        data = request.data.copy()
        application_id = int(pk)  # Assuming the URL parameter is a string representation of an integer
        try:
            leave_application = submit_application(request.principal, data)
            serializer = LeaveApplicationSerializer(leave_application)
            return Response(serializer.data, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
