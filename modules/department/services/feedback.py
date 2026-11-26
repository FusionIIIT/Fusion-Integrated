import django.db.transaction
from django.utils.timezone import now

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.department.domain.feedback import IllegalTransition, next_state
from modules.department.domain.roles import role_kind
from modules.department.models import Department, Feedback
from modules.department.selectors.role_assignments import current_holder
from modules.department.selectors.scoping import department_ids_for_role, member_department_codes
from modules.department.services import notifications
from modules.department.services.authz import PermissionDeniedError, require


def _dispose_fields(feedback_instance, user_id, timestamp):
    """Sets disposed_by_user_id and disposed_at fields."""
    feedback_instance.disposed_by_user_id = user_id
    feedback_instance.disposed_at = timestamp


def submit(*, actor, department_id, body):
    """Submits a new feedback entry."""
    require(actor, "department.feedback.create")

    if not department_id:
        raise NotFoundError("Department not provided")

    department = Department.objects.select_for_update().get(pk=department_id)
    if department.code not in member_department_codes(actor):
        raise NotFoundError("Department not accessible to actor")

    if not body:
        raise ConflictError("content_required")

    with django.db.transaction.atomic():
        feedback = Feedback.objects.select_for_update().create(
            department=department,
            body=body,
            submitter_user_id=actor.user_id,
            state='new'
        )

        # Notify department's current dept_admin holder
        holder = current_holder(department, "dept_admin")
        if holder:
            notifications.enqueue(
                topic="feedback.submitted",
                dedupe_key=f"feedback.submitted:{feedback.id}",
                subject=f"New feedback submitted for {department.name}",
                body="A new feedback has been submitted for your department.",
                recipient_user_id=holder.user_id,
                payload={"feedback_id": feedback.id}
            )

        return feedback


def review(*, actor, feedback_id, category, disposition=None):
    """Reviews an existing feedback entry."""
    require(actor, "department.feedback.review")

    with django.db.transaction.atomic():
        try:
            feedback = Feedback.objects.select_for_update().get(pk=feedback_id)
        except Feedback.DoesNotExist:
            raise NotFoundError("Feedback not found")

        if feedback.department_id not in department_ids_for_role(actor, "dept_admin"):
            raise NotFoundError("Department not held by actor as dept_admin")

        valid_categories = ["academic", "infrastructure", "administrative", "facilities", "other"]
        if category not in valid_categories:
            raise ConflictError("bad_category")

        # Check for illegal transition
        try:
            next_state_str = next_state(feedback.state, "review", "dept_admin")
        except IllegalTransition:
            try:
                next_state_str = next_state(feedback.state, "review", "hod")
            except IllegalTransition:
                raise ConflictError("illegal_transition")

        # Update state and review details
        feedback.state = next_state_str
        feedback.category = category
        feedback.reviewed_by_user_id = actor.user_id
        feedback.reviewed_at = now()
        feedback.save()

        # Handle disposition (resolve or close)
        if disposition in ["resolved", "closed"]:
            try:
                if disposition == "resolved":
                    next_state_str = next_state(feedback.state, "resolve", "dept_admin")
                else: # closed
                    next_state_str = next_state(feedback.state, "close", "dept_admin")
            except IllegalTransition:
                # This should ideally not happen if the initial review transition was valid,
                # but we handle it defensively.
                raise ConflictError("illegal_transition")

            feedback.state = next_state_str
            _dispose_fields(feedback, actor.user_id, now())
            feedback.save()

            # Notify submitter
            notifications.enqueue(
                topic="feedback.closed",
                dedupe_key=f"feedback.closed:{feedback.id}",
                subject=f"Feedback {feedback.id} has been {disposition}",
                body=f"Your feedback has been {disposition}d.",
                recipient_user_id=feedback.submitter_user_id,
                payload={"feedback_id": feedback.id}
            )

        feedback.save()
        return feedback


def dispose(*, actor, feedback_id, outcome):
    """Disposes of a feedback entry (resolves or closes)."""
    require(actor, "department.feedback.update")

    with django.db.transaction.atomic():
        try:
            feedback = Feedback.objects.select_for_update().get(pk=feedback_id)
        except Feedback.DoesNotExist:
            raise NotFoundError("Feedback not found")

        # Role check
        role = role_kind(actor.active_role)
        if role not in ["hod", "dept_admin"]:
            raise PermissionDeniedError("Not authorized to dispose feedback")

        # Department check
        if feedback.department_id not in department_ids_for_role(actor, role):
            raise NotFoundError("Department not held by actor with required role")

        # State check for HOD
        if role == "hod" and feedback.state == "new":
            raise NotFoundError("Cannot dispose of feedback in 'new' state by HOD")

        # Determine event and next state
        if outcome == "resolved":
            event = "resolve"
        elif outcome == "closed":
            event = "close"
        else:
            raise BadRequestError("Invalid outcome. Must be 'resolved' or 'closed'.")

        try:
            next_state_str = next_state(feedback.state, event, role)
        except IllegalTransition:
            raise ConflictError("illegal_transition")

        # Apply disposal
        _dispose_fields(feedback, actor.user_id, now())
        feedback.state = next_state_str
        feedback.save()

        # Notify submitter
        notifications.enqueue(
            topic="feedback.closed",
            dedupe_key=f"feedback.closed:{feedback.id}",
            subject=f"Feedback {feedback.id} has been {outcome}",
            body=f"Your feedback has been {outcome}d.",
            recipient_user_id=feedback.submitter_user_id,
            payload={"feedback_id": feedback.id}
        )

        return feedback
