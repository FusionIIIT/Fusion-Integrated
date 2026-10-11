from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import LeaveRequest

def has_leave_request_permission(user):
    content_type = ContentType.objects.get_for_model(LeaveRequest)
    permission = Permission.objects.get(codename='can_manage_leave_requests', content_type=content_type)
    return user.has_perm(permission)
