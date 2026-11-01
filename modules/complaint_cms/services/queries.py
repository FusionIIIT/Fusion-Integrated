from django.db import models
from core.api.exceptions import PermissionDeniedError
from ..models import Complaint, ComplaintTask, ComplaintNotification
from ..registry import PERMISSIONS

def list_complaints(actor):
    if not actor.has_any_permission(*PERMISSIONS[:2]):
        raise PermissionDeniedError()
    return Complaint.objects.filter(user_id=actor.user_id)

def assigned_tasks(actor):
    if not actor.has_permission("complaint_cms.task.view"):
        raise PermissionDeniedError()
    return ComplaintTask.objects.filter(assigned_to_id=actor.user_id)

def list_notifications(actor):
    if not actor.has_permission("complaint_cms.configuration.manage"):
        raise PermissionDeniedError()
    return ComplaintNotification.objects.all()
