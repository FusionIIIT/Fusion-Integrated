from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from core.api.exceptions import DomainError, NotFoundError, PermissionDeniedError
from modules.leave_elm.models import LeaveApplication, LeaveHistory, LeaveTask, LeaveSubstitution, LeaveExtension, LeaveResumption

def act_on_application(actor, application_id, action, data):
    try:
        leave_app = LeaveApplication.objects.get(id=application_id)
    except LeaveApplication.DoesNotExist:
        raise NotFoundError(message='Leave Application not found')

    if actor.kind != 'faculty' and actor.kind != 'staff':
        raise PermissionDeniedError(message='Only faculty/staff can perform leave-related actions')

    with transaction.atomic():
        if action == 'approve':
            if leave_app.status != 'Pending':
                raise DomainError(message='Cannot approve an already approved/rejected/cancelled application')

            leave_app.approved_by = actor
            leave_app.approved_at = timezone.now()
            leave_app.status = 'Approved'

            # Create history entry
            LeaveHistory.objects.create(
                leave_application=leave_app,
                status='Approved',
                decision=data['decision'] or 'Approved by ' + str(actor.username),
            )

            # Update balance
            update_leave_balance(leave_app.user_id, leave_app.leave_category, -leave_app.days)

        elif action == 'reject':
            if leave_app.status != 'Pending':
                raise DomainError(message='Cannot reject an already approved/rejected/cancelled application')

            leave_app.status = 'Rejected'

            # Create history entry
            LeaveHistory.objects.create(
                leave_application=leave_app,
                status='Rejected',
                decision=data['decision'] or 'Rejected by ' + str(actor.username),
            )

        elif action == 'withdraw':
            if leave_app.status not in ['Pending', 'Submitted']:
                raise DomainError(message='Only pending/submitted applications can be withdrawn')

            leave_app.status = 'Withdrawn'

            # Create history entry
            LeaveHistory.objects.create(
                leave_application=leave_app,
                status='Withdrawn',
                decision=data['decision'] or 'Withdrawn by ' + str(actor.username),
            )

        elif action == 'cancel':
            if leave_app.status not in ['Approved', 'Cancelled']:
                raise DomainError(message='Only approved/cancelled applications can be cancelled')

            leave_app.status = 'Cancelled'

            # Create history entry
            LeaveHistory.objects.create(
                leave_application=leave_app,
                status='Cancelled',
                decision=data['decision'] or 'Cancelled by ' + str(actor.username),
            )

            # Update balance
            update_leave_balance(leave_app.user_id, leave_app.leave_category, -leave_app.days)

        elif action == 'extend':
            if leave_app.status != 'Approved' or leave_app.extension_requested:
                raise DomainError(message='Cannot extend an application that is not yet approved or has already been extended')

            leave_app.extension_requested = True
            leave_app.extension_start_date = data.get('extension_start_date', leave_app.end_date + timedelta(days=1))
            leave_app.extension_end_date = data.get('extension_end_date', leave_app.end_date + timedelta(days=30))

            leave_app.save()

            # Create task for extension approval
            LeaveTask.objects.create(
                leave_application=leave_app,
                task_type='Extension Approval',
                reminder_threshold=60,
                escalation_threshold=120,
            )

        elif action == 'resume':
            if leave_app.status != 'Approved' or leave_app.resumption_start_date:
                raise DomainError(message='Cannot resume an application that is not yet approved or has already been resumed')

            leave_app.resumption_start_date = data['actual_resumption_date']

            leave_app.save()

            # Create task for resumption review
            LeaveTask.objects.create(
                leave_application=leave_app,
                task_type='Resumption Review',
                reminder_threshold=60,
                escalation_threshold=120,
            )

        elif action == 'substitute':
            if leave_app.status != 'Pending' or leave_app.substitution_requested:
                raise DomainError(message='Cannot request a substitute for an application that is not pending or has already been requested')

            substitution_user_id = data.get('substitute_user_id')

            try:
                substitute_user = User.objects.get(id=substitution_user_id)
            except User.DoesNotExist:
                raise NotFoundError(message='Substitute user not found')

            leave_app.substitution_requested = True
            leave_app.substitute_user_id = substitution_user_id

            leave_app.save()

            # Create task for substitute approval
            LeaveTask.objects.create(
                leave_application=leave_app,
                task_type='Substitute Approval',
                reminder_threshold=60,
                escalation_threshold=120,
            )

        elif action == 'recommend':
            if leave_app.status != 'Pending':
                raise DomainError(message='Cannot recommend an application that is not yet pending')

            leave_app.status = 'Recommended'

            # Create history entry
            LeaveHistory.objects.create(
                leave_application=leave_app,
                status='Recommended',
                decision=data['decision'] or 'Recommended by ' + str(actor.username),
            )

    actor.notify_leave_status(leave_app.id, leave_app.status)

    return leave_app