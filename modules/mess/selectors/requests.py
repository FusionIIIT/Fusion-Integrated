from modules.mess.models import RegistrationRequest, DeregistrationRequest, RebateRequest, SpecialFoodRequest, RequestTransition

def list_requests_for_user(user_id):
    requests = {
        'RegistrationRequest': RegistrationRequest.objects.filter(user=user_id).order_by('-created_at'),
        'DeregistrationRequest': DeregistrationRequest.objects.filter(user=user_id).order_by('-created_at'),
        'RebateRequest': RebateRequest.objects.filter(user=user_id).order_by('-created_at'),
        'SpecialFoodRequest': SpecialFoodRequest.objects.filter(user=user_id).order_by('-created_at'),
    }
    return requests

def get_status_history(request_type, request_id, user_id):
    try:
        request = request_type.objects.get(id=request_id)
        if request.user.id != user_id:
            return None
        return RequestTransition.objects.filter(request=request_id).order_by('at')
    except request_type.DoesNotExist:
        return None

def list_pending_for_caretaker():
    requests = {
        'RegistrationRequest': RegistrationRequest.objects.filter(status='PENDING'),
        'DeregistrationRequest': DeregistrationRequest.objects.filter(status='PENDING'),
        'RebateRequest': RebateRequest.objects.filter(status='PENDING'),
        'SpecialFoodRequest': SpecialFoodRequest.objects.filter(status='PENDING'),
    }
    return requests

def list_all_requests_for_warden():
    requests = {
        'RegistrationRequest': RegistrationRequest.objects.all(),
        'DeregistrationRequest': DeregistrationRequest.objects.all(),
        'RebateRequest': RebateRequest.objects.all(),
        'SpecialFoodRequest': SpecialFoodRequest.objects.all(),
    }
    return requests
