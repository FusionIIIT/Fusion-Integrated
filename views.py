import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Employee, LeaveCategory, Entitlement, LeaveApplication, LeaveApplicationTransition

@csrf_exempt
def update_leave_application(request, application_id):
    if request.method == 'PUT':
        data = request.POST
        application = LeaveApplication.objects.get(id=application_id)
        application.status = data['status']
        application.save()

        transition = LeaveApplicationTransition(
            application=application,
            status=data['status'],
            transitioned_at=datetime.now()
        )
        transition.save()

        return JsonResponse({'message': 'Leave application updated successfully'}, status=200)
