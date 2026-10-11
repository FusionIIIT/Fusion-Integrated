from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from modules.employee_leave_management.models import LeaveApplication, LeaveType
from modules.employee_leave_management.services import elm_service
from directory.models import User # Reusing User model from directory module

class LeaveTypeViewSet(viewsets.ModelViewSet):
    """API endpoint that allows Leave Types to be viewed and managed."""
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer # Assumed serializer
    # Permissions logic would integrate here using fusion_auth permissions

class LeaveApplicationViewSet(viewsets.ModelViewSet):
    """API endpoint that allows Leave Applications to be created, viewed, and managed."""
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer # Assumed serializer
    # Permissions logic would integrate here using fusion_auth permissions

    def create(self, request, *args, **kwargs):
        # Custom logic for submission: require specific user context
        user = request.user 
        leave_type_id = request.data.get('leave_type_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        reason = request.data.get('reason')
        
        try:
            application = elm_service.request_leave(
                user=user,
                leave_type_id=leave_type_id,
                start_date=start_date,
                end_date=end_date,
                reason=reason
            )
            return Response(application, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        # Custom logic for approvals/rejections
        instance = self.get_object()
        
        if request.method == 'PATCH' and 'approval_action' in request.data:
            action = request.data['approval_action'] # e.g., 'APPROVE' or 'REJECT'
            approver = request.user
            comment = request.data.get('comment', '')
            
            try:
                if action == 'APPROVE':
                    updated_app = elm_service.process_approval(instance.pk, approver, True, comment)
                elif action == 'REJECT':
                    updated_app = elm_service.process_approval(instance.pk, approver, False, comment)
                else:
                    return Response({"detail": "Invalid approval action."}, status=status.HTTP_400_BAD_REQUEST)
                
                return Response(updated_app, status=status.HTTP_200_OK)

            except ValueError as e:
                return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
            except PermissionDenied as e:
                return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

        return super().update(request, *args, **kwargs)


# Placeholder for Serializers (Would need to be created alongside this)
class LeaveTypeSerializer:
    class Meta:
        model = LeaveType
        fields = '__all__'

class LeaveApplicationSerializer:
    class Meta:
        model = LeaveApplication
        fields = '__all__'
