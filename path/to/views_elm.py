from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.contrib.auth.models import User
from .models import LeaveApplication, SubstituteAssignment

@api_view(['POST'])
def submit_leave_application(request):
    data = request.data
    applicant = User.objects.get(username=data['applicant'])
    leave_type = data['leave_type']
    start_date = data['start_date']
    end_date = data['end_date']
    chargeable_days = data['chargeable_days']
    purpose = data['purpose']
    is_station_leave = data['is_station_leave']

    leave_app = LeaveApplication.objects.create(
        applicant=applicant,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        chargeable_days=chargeable_days,
        purpose=purpose,
        is_station_leave=is_station_leave
    )

    return Response({'message': 'Leave application submitted successfully'}, status=status.HTTP_201_CREATED)

@api_view(['PUT'])
def enforce_substitute_consent_gate(request):
    data = request.data
    application_id = data['application_id']
    substitute_id = data['substitute_id']
    status = data['status']

    application = LeaveApplication.objects.get(id=application_id)
    substitute = User.objects.get(id=substitute_id)

    if application.status == 'pending' and substitute.status == 'pending':
        substitute_assignment = SubstituteAssignment.objects.create(
            application=application,
            substitute=substitute,
            status=status
        )
        return Response({'message': 'Substitute consent gate enforced successfully'}, status=status.HTTP_200_OK)
    else:
        return Response({'message': 'Substitute consent gate enforcement failed'}, status=status.HTTP_400_BAD_REQUEST)
