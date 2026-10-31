from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from core.api.exceptions import BadRequestError, DomainError, NotFoundError, PermissionDeniedError
from modules.leave_elm.domain.policy import LEAVE_POLICY_DEFAULTS
from modules.leave_elm.models import (
    LeaveApplication,
    LeaveBalance,
    LeaveExtension,
    LeaveHistory,
    LeaveNotification,
    LeaveResumption,
    LeaveSubstitution,
    LeaveTask,
)


def _adjust_balance(user_id: int, leave_category, delta_days: Decimal) -> None:
    bal, _ = LeaveBalance.objects.select_for_update().get_or_create(
        user_id=user_id,
        leave_category=leave_category,
        defaults={'balance': Decimal(str(LEAVE_POLICY_DEFAULTS.get(leave_category.name, 8)))},
    )
    new_val = bal.balance + Decimal(str(delta_days))
    if delta_days < 0 and new_val < 0:
        raise DomainError('Insufficient leave balance.')
    bal.balance = new_val
    bal.save(update_fields=['balance', 'updated_at'])


@transaction.atomic
def act_on_application(actor, application_id: int, action: str, data=None):
    data = dict(data or {})
    if isinstance(data.get('data'), dict):
        data = {**data['data'], **data}
    try:
        leave_app = (
            LeaveApplication.objects.select_for_update()
            .select_related('leave_type', 'leave_type__leave_category')
            .get(id=application_id)
        )
    except LeaveApplication.DoesNotExist as exc:
        raise NotFoundError('Leave Application not found') from exc

    decision_text = str(data.get('decision') or data.get('remarks') or f'{action} by {actor.username}')

    if action in ('substitute_accept', 'substitute_reject'):
        if not actor.has_permission('leave_elm.substitute.respond'):
            raise PermissionDeniedError()
        subs = LeaveSubstitution.objects.filter(
            leave_application=leave_app, substitute_user_id=actor.user_id
        )
        sub_status = 'Accepted' if action == 'substitute_accept' else 'Rejected'
        if not subs.exists():
            if (
                leave_app.academic_substitute_user_id != actor.user_id
                and leave_app.admin_substitute_user_id != actor.user_id
            ):
                raise PermissionDeniedError()
            LeaveSubstitution.objects.create(
                user_id=leave_app.user_id,
                leave_application=leave_app,
                substitute_user_id=actor.user_id,
                status=sub_status,
                responded_at=timezone.now(),
            )
        else:
            subs.update(status=sub_status, responded_at=timezone.now())
        LeaveTask.objects.filter(
            leave_application=leave_app, user_id=actor.user_id, role='substitute', status='Pending'
        ).update(status='Completed')
        if action == 'substitute_reject':
            leave_app.status = 'Returned for Clarification'
        elif not LeaveSubstitution.objects.filter(leave_application=leave_app, status='Pending').exists():
            leave_app.status = 'Pending'
            LeaveTask.objects.create(
                user_id=leave_app.user_id,
                leave_application=leave_app,
                task_type='Application Review',
                status='Pending',
                role='reviewer',
            )
    elif action in ('recommend', 'forward'):
        if not actor.has_permission('leave_elm.application.review') or actor.user_id == leave_app.user_id:
            raise PermissionDeniedError()
        if leave_app.status not in ('Pending', 'Under Review'):
            raise DomainError('Application cannot be recommended in its current status.')
        leave_app.status = 'Awaiting Sanctioning Authority'
        leave_app.reviewed_by_id = actor.user_id
        leave_app.reviewed_at = timezone.now()
        LeaveTask.objects.filter(leave_application=leave_app, role='reviewer', status='Pending').update(
            status='Completed'
        )
        LeaveTask.objects.create(
            user_id=actor.user_id,
            leave_application=leave_app,
            task_type='Sanction Decision',
            status='Pending',
            role='authority',
        )
    elif action == 'return_clarification':
        if (
            not (
                actor.has_permission('leave_elm.application.review')
                or actor.has_permission('leave_elm.application.approve')
            )
            or actor.user_id == leave_app.user_id
        ):
            raise PermissionDeniedError()
        if leave_app.status not in ('Pending', 'Under Review', 'Awaiting Sanctioning Authority'):
            raise DomainError('Invalid status for clarification.')
        leave_app.status = 'Returned for Clarification'
    elif action == 'approve':
        if not actor.has_permission('leave_elm.application.approve') or actor.user_id == leave_app.user_id:
            raise PermissionDeniedError()
        if leave_app.status not in ('Pending', 'Under Review', 'Awaiting Sanctioning Authority'):
            raise DomainError('Application cannot be approved in its current status.')
        if not leave_app.balance_deducted:
            _adjust_balance(leave_app.user_id, leave_app.leave_type.leave_category, -leave_app.working_days)
            leave_app.balance_deducted = True
        leave_app.status = 'Approved'
        leave_app.approved_by_id = actor.user_id
        leave_app.approved_at = timezone.now()
        LeaveTask.objects.filter(leave_application=leave_app, status='Pending').update(status='Completed')
    elif action == 'reject':
        if (
            not (
                actor.has_permission('leave_elm.application.review')
                or actor.has_permission('leave_elm.application.approve')
            )
            or actor.user_id == leave_app.user_id
        ):
            raise PermissionDeniedError()
        if leave_app.status not in ('Pending', 'Under Review', 'Awaiting Sanctioning Authority', 'Substitute Pending'):
            raise DomainError('Application cannot be rejected in its current status.')
        leave_app.status = 'Rejected'
        LeaveTask.objects.filter(leave_application=leave_app, status='Pending').update(status='Completed')
    elif action == 'withdraw':
        if actor.user_id != leave_app.user_id:
            raise PermissionDeniedError()
        if leave_app.status not in (
            'Draft',
            'Pending',
            'Substitute Pending',
            'Under Review',
            'Returned for Clarification',
        ):
            raise DomainError('Only pending applications can be withdrawn.')
        leave_app.status = 'Cancelled'
        leave_app.cancelled_by_id = actor.user_id
        leave_app.cancelled_at = timezone.now()
        LeaveTask.objects.filter(leave_application=leave_app, status='Pending').update(status='Completed')
    elif action == 'cancel':
        if actor.user_id != leave_app.user_id and not actor.has_permission('leave_elm.application.approve'):
            raise PermissionDeniedError()
        if leave_app.status != 'Approved':
            raise DomainError('Only approved applications can be cancelled.')
        if leave_app.balance_deducted:
            _adjust_balance(leave_app.user_id, leave_app.leave_type.leave_category, leave_app.working_days)
            leave_app.balance_deducted = False
        leave_app.status = 'Cancelled'
        leave_app.cancelled_by_id = actor.user_id
        leave_app.cancelled_at = timezone.now()
    elif action == 'extend':
        if actor.user_id != leave_app.user_id:
            raise PermissionDeniedError()
        if leave_app.status != 'Approved' or leave_app.extension_requested:
            raise DomainError('Cannot extend application.')
        ext_start = leave_app.end_date + timedelta(days=1)
        ext_end = leave_app.end_date + timedelta(days=int(data.get('extension_days', 2) or 2))
        leave_app.extension_requested = True
        leave_app.extension_start_date = ext_start
        leave_app.extension_end_date = ext_end
        LeaveExtension.objects.create(
            user_id=actor.user_id,
            leave_application=leave_app,
            extension_start_date=ext_start,
            extension_end_date=ext_end,
            reason=decision_text,
            status='Pending',
        )
        LeaveTask.objects.create(
            user_id=actor.user_id,
            leave_application=leave_app,
            task_type='Extension Approval',
            status='Pending',
            role='authority',
        )
    elif action == 'resume':
        if actor.user_id != leave_app.user_id:
            raise PermissionDeniedError()
        if leave_app.status != 'Approved' or leave_app.resumed_at is not None:
            raise DomainError('Cannot resume application.')
        leave_app.resumed_at = timezone.now()
        leave_app.status = 'Completed'
        LeaveResumption.objects.create(
            user_id=actor.user_id,
            leave_application=leave_app,
            actual_resumption_date=leave_app.end_date + timedelta(days=1),
            remarks=decision_text,
            status='Submitted',
        )
    else:
        raise BadRequestError(f'Unsupported action: {action}')

    leave_app.save()
    LeaveHistory.objects.create(
        user_id=actor.user_id,
        leave_application=leave_app,
        action=action,
        status=leave_app.status,
        decision=decision_text,
    )
    LeaveNotification.objects.create(
        user_id=leave_app.user_id,
        leave_application=leave_app,
        message=f'Application #{leave_app.id} {action}: {leave_app.status}',
        channel='in_app',
    )
    return leave_app
