from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import LeaveType, LeaveRequest
from .services import apply_for_leave, approve_leave, reject_leave

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_for_leave_view(request):
    user = request.user
    leave_type_id = request.data.get('leave_type')
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')

    leave_type = LeaveType.objects.get(id=leave_type_id)
    leave_request = apply_for_leave(user, leave_type, start_date, end_date)

    return Response({'status': 'Leave request applied successfully', 'leave_request_id': leave_request.id}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_leave_view(request):
    leave_request_id = request.data.get('leave_request_id')
    leave_request = approve_leave(leave_request_id)

    return Response({'status': 'Leave request approved', 'leave_request': leave_request.id}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_leave_view(request):
    leave_request_id = request.data.get('leave_request_id')
    leave_request = reject_leave(leave_request_id)

    return Response({'status': 'Leave request rejected', 'leave_request': leave_request.id}, status=status.HTTP_200_OK)