

from django.db import transaction
from modules.leave_elm.models import LeaveApplication, LeaveHistory, LeaveTask
from fusion_auth.principal import Principal
from core.api.exceptions import BadRequestError, ConflictError, DomainError, NotFoundError, PermissionDeniedError
import datetime

@transaction.atomic
def submit_application(actor, data):
    if not actor.has_permission('leave_elm.application.create'):
        raise PermissionDeniedError()

    try:
        # Create a new leave application
        leave_application = LeaveApplication(
            user_id=actor.user_id,
            leave_type=data['leave_type'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            purpose=data['purpose'],
        )
        leave_application.save()

        # Record history for submission
        leave_history = LeaveHistory(
            leave_application=leave_application,
            status='Submitted',
        )
        leave_history.save()

        # Record task for submission
        leave_task = LeaveTask(
            leave_application=leave_application,
            task_type='Submission',
            status='Pending',
        )
        leave_task.save()

        return leave_application

    except Exception as e:
        raise DomainError(str(e))
