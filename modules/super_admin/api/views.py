from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from modules.super_admin.models import UserAccount, RoleAssignment, SystemAuditLog
from modules.super_admin.api.serializers import (
    UserAccountSerializer,
    RoleAssignmentSerializer,
    SystemAuditLogSerializer,
    UserStatusUpdateSerializer,
)
from datetime import datetime

class UserManagementView(APIView):
    def get(self, request):
        queryset = UserAccount.objects.all()
        user_type = request.query_params.get('user_type')
        status_filter = request.query_params.get('status')

        if user_type:
            queryset = queryset.filter(user_type=user_type)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        serializer = UserAccountSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = UserAccountSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            SystemAuditLog.objects.create(
                actor_username="super_admin",
                action="CREATE_USER",
                target=user.username,
                details=serializer.data
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserStatusView(APIView):
    def patch(self, request, pk):
        user = get_object_or_404(UserAccount, pk=pk)
        serializer = UserStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            
            # Update status
            user.status = validated_data['status']
            user.save()

            # Create audit log
            SystemAuditLog.objects.create(
                actor_username="super_admin",
                action="UPDATE_USER_STATUS",
                target=user.username,
                details=validated_data
            )
            
            return Response(UserAccountSerializer(user).data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RoleAssignmentView(APIView):
    def get(self, request):
        queryset = RoleAssignment.objects.filter(status='active')
        serializer = RoleAssignmentSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = RoleAssignmentSerializer(data=request.data)
        if serializer.is_valid():
            role = serializer.save()
            SystemAuditLog.objects.create(
                actor_username="super_admin",
                action="ASSIGN_ROLE",
                target=role.role_name,
                details=serializer.data
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RoleRevokeView(APIView):
    def post(self, request, pk):
        role = get_object_or_404(RoleAssignment, pk=pk)
        
        # Set status to revoked
        role.status = 'revoked'
        role.save()
        
        # Create audit log
        SystemAuditLog.objects.create(
            actor_username="super_admin",
            action="REVOKE_ROLE",
            target=role.role_name,
            details={"role_id": role.id}
        )
        
        return Response({"message": "Role revoked successfully"}, status=status.HTTP_200_OK)

class AuditLogListView(APIView):
    def get(self, request):
        logs = SystemAuditLog.objects.all().order_by('-timestamp')[:50]
        serializer = SystemAuditLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)