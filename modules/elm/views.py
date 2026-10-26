# modules/elm/views.py

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .services import apply_for_leave, approve_leave_request, reject_leave_request

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_for_leave_view(request):
    user = request.user
    leave_type_id = request.data.get('leave_type')
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')

    try:
        leave_request = apply_for_leave(user, leave_type_id, start_date, end_date)
        return Response({'message': 'Leave application successful', 'leave_request': leave_request.id}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_leave_request_view(request):
    leave_request_id = request.data.get('leave_request')

    try:
        leave_request = approve_leave_request(leave_request_id)
        return Response({'message': 'Leave request approved', 'leave_request': leave_request.id}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_leave_request_view(request):
    leave_request_id = request.data.get('leave_request')

    try:
        leave_request = reject_leave_request(leave_request_id)
        return Response({'message': 'Leave request rejected', 'leave_request': leave_request.id}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

