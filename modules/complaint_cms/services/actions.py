from django.db import models, transaction
from core.api.exceptions import AuthenticationFailedError, BadRequestError as DomainValidationError, BadRequestError as ValidationError, DomainError, NotFoundError as ResourceNotFoundError, PermissionDeniedError
from ..models import Complaint, ComplaintCategory, ComplaintNotification as Notification, ComplaintTask, ComplaintUpdate, RoutingRule, UserScopedModel
from ..domain.policy import SEVERITY_SLA_HOURS
from ..registry import MODULE, PERMISSIONS
import datetime

def get_user_role(user):
    # Placeholder function to determine user role based on user ID
    return "student/faculty/staff"  # Example role

def can_perform_action(user, complaint, action):
    if not user.is_authenticated:
        raise AuthenticationFailedError()

    required_permission = f"{MODULE['code']}.{action}"
    if required_permission not in PERMISSIONS:
        raise PermissionDeniedError(f"Action '{action}' is not allowed.")

    if action == 'assign':
        assigned_to_id = data.get('assigned_to_id')
        if assigned_to_id != user.id:
            raise PermissionDeniedError("Only the assignee can perform this action.")
    
    elif action == 'feedback' and complaint.status != 'Resolved':
        raise PermissionDeniedError("Feedback can be provided only for resolved complaints.")

def act_on_complaint(actor, complaint_id, action, data=None):
    try:
        with transaction.atomic():
            complaint = Complaint.objects.select_for_update().get(id=complaint_id)
            
            if complaint.user_id != actor.id:
                raise PermissionDeniedError("You do not have permission to perform this action.")
                
            can_perform_action(actor, complaint, action)

            if action == 'acknowledge':
                complaint.status = 'In Progress'
                complaint.escalation_level = 1
                complaint.sla_due_at = datetime.datetime.now() + datetime.timedelta(hours=SEVERITY_SLA_HOURS[complaint.severity])
                complaint.save()
                update_entry = ComplaintUpdate(
                    complaint=complaint,
                    actor_id=actor.id,
                    update_type='StatusChange',
                    visibility=True,
                    comment=f"Complaint acknowledged by {actor.username}.",
                    old_status='Submitted',
                    new_status='In Progress'
                )
                update_entry.save()

            elif action == 'start_progress':
                complaint.status = 'In Progress'
                complaint.escalation_level = 1
                complaint.sla_due_at = datetime.datetime.now() + datetime.timedelta(hours=SEVERITY_SLA_HOURS[complaint.severity])
                complaint.save()
                update_entry = ComplaintUpdate(
                    complaint=complaint,
                    actor_id=actor.id,
                    update_type='StatusChange',
                    visibility=True,
                    comment=f"Complaint started in progress by {actor.username}.",
                    old_status='Submitted',
                    new_status='In Progress'
                )
                update_entry.save()

            elif action == 'resolve':
                complaint.status = 'Resolved'
                complaint.resolved_at = datetime.datetime.now()
                complaint.resolution_summary = data.get('resolution_summary', '')
                complaint.feedback_rating = data.get('feedback_rating')
                complaint.feedback_comment = data.get('feedback_comment')
                complaint.save()
                
                if complaint.category.is_active:
                    routing_rule = RoutingRule.objects.filter(category=complaint.category).first()
                    target_section = routing_rule.target_section
                    
                    # Create or update a task for the assigned section
                    task, created = ComplaintTask.objects.update_or_create(
                        complaint=complaint,
                        defaults={
                            'assigned_to_id': complaint.user_id,
                            'role_name': get_user_role(actor),
                            'task_type': 'Resolution',
                            'status': 'Pending',
                            'due_at': datetime.datetime.now() + datetime.timedelta(hours=SEVERITY_SLA_HOURS[complaint.severity]),
                        }
                    )

                    if not created and task.assigned_to_id != complaint.user_id:
                        raise PermissionDeniedError("Only the assignee can perform this action.")

                    update_entry = ComplaintUpdate(
                        complaint=complaint,
                        actor_id=actor.id,
                        update_type='StatusChange',
                        visibility=True,
                        comment=f"Complaint resolved by {actor.username}.",
                        old_status='In Progress',
                        new_status='Resolved'
                    )
                    update_entry.save()

            elif action == 'close':
                complaint.status = 'Closed'
                complaint.closed_at = datetime.datetime.now()
                complaint.resolution_summary = data.get('resolution_summary', '')
                complaint.feedback_rating = data.get('feedback_rating')
                complaint.feedback_comment = data.get('feedback_comment')
                complaint.save()

                update_entry = ComplaintUpdate(
                    complaint=complaint,
                    actor_id=actor.id,
                    update_type='StatusChange',
                    visibility=True,
                    comment=f"Complaint closed by {actor.username}.",
                    old_status='Resolved',
                    new_status='Closed'
                )
                update_entry.save()

            elif action == 'reopen':
                complaint.status = 'Submitted'
                complaint.reopen_count += 1
                complaint.sla_due_at = None
                complaint.resolved_at = None
                complaint.feedback_rating = None
                complaint.feedback_comment = None
                complaint.save()

                update_entry = ComplaintUpdate(
                    complaint=complaint,
                    actor_id=actor.id,
                    update_type='StatusChange',
                    visibility=True,
                    comment=f"Complaint reopened by {actor.username}.",
                    old_status='Closed',
                    new_status='Submitted'
                )
                update_entry.save()

            elif action == 'escalate':
                if complaint.escalation_level >= 3:
                    raise PermissionDeniedError("Maximum escalation level reached.")

                routing_rule = RoutingRule.objects.filter(category=complaint.category).first()
                target_section = routing_rule.target_section
                
                # Create or update a task for the assigned section
                task, created = ComplaintTask.objects.update_or_create(
                    complaint=complaint,
                    defaults={
                        'assigned_to_id': complaint.user_id,
                        'role_name': get_user_role(actor),
                        'task_type': 'Escalation',
                        'status': 'Pending',
                        'due_at': datetime.datetime.now() + datetime.timedelta(hours=SEVERITY_SLA_HOURS[complaint.severity]),
                    }
                )

                if not created and task.assigned_to_id != complaint.user_id:
                    raise PermissionDeniedError("Only the assignee can perform this action.")

                complaint.status = 'In Progress'
                complaint.sla_due_at = datetime.datetime.now() + datetime.timedelta(hours=SEVERITY_SLA_HOURS[complaint.severity])
                complaint.escalation_level += 1
                complaint.save()

                update_entry = ComplaintUpdate(
                    complaint=complaint,
                    actor_id=actor.id,
                    update_type='StatusChange',
                    visibility=True,
                    comment=f"Complaint escalated by {actor.username}.",
                    old_status='Resolved',
                    new_status='In Progress'
                )
                update_entry.save()

            elif action == 'assign':
                assigned_to_id = data.get('assigned_to_id')
                if assigned_to_id is None or assigned_to_id <= 0:
                    raise ValidationError({"assigned_to_id": "Invalid user ID."})
                
                try:
                    assigned_user = UserScopedModel.objects.select_for_update().get(id=assigned_to_id)
                except UserScopedModel.DoesNotExist:
                    raise ResourceNotFoundError(f"User with ID {assigned_to_id} does not exist.")
                    
                complaint.assigned_to_id = assigned_to_id
                complaint.assigned_role = get_user_role(assigned_user)
                complaint.save()
                
                task, created = ComplaintTask.objects.update_or_create(
                    complaint=complaint,
                    defaults={
                        'assigned_to_id': assigned_to_id,
                        'role_name': get_user_role(assigned_user),
                        'task_type': 'Assignment',
                        'status': 'Pending',
                        'due_at': datetime.datetime.now() + datetime.timedelta(hours=SEVERITY_SLA_HOURS[complaint.severity]),
                    }
                )

                update_entry = ComplaintUpdate(
                    complaint=complaint,
                    actor_id=actor.id,
                    update_type='StatusChange',
                    visibility=True,
                    comment=f"Complaint assigned to {assigned_user.username} by {actor.username}.",
                    old_status='In Progress',
                    new_status='In Progress'
                )
                update_entry.save()

            elif action == 'feedback':
                if complaint.status != 'Resolved':
                    raise PermissionDeniedError("Feedback can be provided only for resolved complaints.")

                feedback_rating = data.get('feedback_rating')
                feedback_comment = data.get('feedback_comment')

                complaint.feedback_rating = feedback_rating
                complaint.feedback_comment = feedback_comment
                complaint.save()

                update_entry = ComplaintUpdate(
                    complaint=complaint,
                    actor_id=actor.id,
                    update_type='Comment',
                    visibility=True,
                    comment=f"Feedback submitted by {actor.username}: Rating - {feedback_rating}, Comment - '{feedback_comment}'.",
                    old_status=None,
                    new_status=None
                )
                update_entry.save()
                
                # Create a notification for the complainant
                Notification.objects.create(
                    recipient_id=complaint.user_id,
                    title="Feedback Submitted",
                    message=f"You have received feedback on your complaint. Please review it.",
                    is_read=False
                )

        return complaint

    except DomainValidationError as e:
        raise ValidationError(e)
    
    except ResourceNotFoundError as e:
        raise ResourceNotFoundError(e)

    except Exception as e:
        raise DomainError(str(e))
