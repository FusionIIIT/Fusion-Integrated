from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import CreateAPIView
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from ..models import LeaveApplication, LeaveBalance
from .serializers import LeaveBalanceSerializer, LeaveApplicationSerializer

class LeaveApplicationListView(APIView):
    def get(self, request):
        user = request.user
        leave_balances = LeaveBalance.objects.filter(user=user)
        leave_applications = LeaveApplication.objects.filter(user=user)
        leave_balance_serializer = LeaveBalanceSerializer(leave_balances, many=True)
        leave_application_serializer = LeaveApplicationSerializer(leave_applications, many=True)
        return Response({
            'leave_balances': leave_balance_serializer.data,
            'leave_applications': leave_application_serializer.data
        })

class LeaveApplicationCreateView(CreateAPIView):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer

class LeaveTransitionView(APIView):
    def post(self, request, format=None):
        data = request.data
        action = data.get('action')
        leave_application_id = data.get('leave_application')
        user_id = data.get('user')

        if not user_id or not leave_application_id or not action:
            return Response({"error": "Missing required data"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(pk=user_id)
            leave_application = LeaveApplication.objects.get(pk=leave_application_id)
        except ObjectDoesNotExist:
            return Response({"error": "Invalid user or leave application"}, status=status.HTTP_400_BAD_REQUEST)

        if action not in ['approve', 'reject', 'withdraw']:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'approve':
            leave_application.status = 'approved'
            leave_application.save()
            leave_balance, created = LeaveBalance.objects.get_or_create(user=user, leave_type=leave_application.leave_type)
            leave_balance.balance -= (leave_application.end_date - leave_application.start_date).days + 1
            leave_balance.save()
        elif action == 'reject':
            leave_application.status = 'rejected'
            leave_application.save()
        elif action == 'withdraw':
            leave_application.status = 'withdrawn'
            leave_balance = LeaveBalance.objects.get(user=user, leave_type=leave_application.leave_type)
            leave_balance.balance += (leave_application.end_date - leave_application.start_date).days + 1
            leave_balance.save()
            leave_application.save()

        return Response({"message": f"Leave application {action}ed"}, status=status.HTTP_200_OK)