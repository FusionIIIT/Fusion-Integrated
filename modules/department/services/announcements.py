from django.db import transaction

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.department.domain import announcements as announcement_domain
from modules.department.models import (
    Announcement,
    Department,
)
from modules.department.selectors.scoping import department_ids_for_role, member_department_codes
from modules.department.services import notifications
from modules.department.services.authz import require
from modules.directory import contracts as directory


def _send_notifications(announcement: Announcement, actor, department_code: str):
    """Sends notifications to relevant students and faculty."""
    # Get all student IDs in the discipline associated with the department
    student_ids = directory.user_ids_in_discipline(department_code)

    # Get all faculty records for this department
    all_employees = directory.get_employees()
    faculty_records = [
        record for record in all_employees
        if record.kind == "faculty" and record.department == department_code
    ]

    # Notify students
    for student_id in student_ids:
        user_data = directory.get_users([student_id]).get(student_id)
        if user_data and announcement_domain.is_relevant(
            announcement.target_roles,
            announcement.target_programme,
            announcement.target_batch_year,
            user_data.kind,
            user_data.programme,
            user_data.batch_year,
        ):
            notifications.enqueue(
                topic="announcement.published",
                dedupe_key=f"{announcement.id}-{student_id}",
                subject=announcement.title,
                body=announcement.body,
                recipient_user_id=student_id,
                payload={"announcement_id": announcement.id},
            )

    # Notify faculty
    for faculty_record in faculty_records:
        user_data = directory.get_users([faculty_record.user_id]).get(faculty_record.user_id)
        if user_data and announcement_domain.is_relevant(
            announcement.target_roles,
            announcement.target_programme,
            announcement.target_batch_year,
            user_data.kind,
            user_data.programme,
            user_data.batch_year,
        ):
            notifications.enqueue(
                topic="announcement.published",
                dedupe_key=f"{announcement.id}-{user_data.user_id}",
                subject=announcement.title,
                body=announcement.body,
                recipient_user_id=user_data.user_id,
                payload={"announcement_id": announcement.id},
            )


def publish(*, actor, department_id: int, title: str, body: str, target_roles: list[str], target_programme: str = "", target_batch_year: int = None):
    """Publishes a new announcement for a department."""
    require(actor, "department.announcement.create")
    with transaction.atomic():
        department = Department.objects.get(id=department_id)

        # Actor authorization check
        if not member_department_codes(actor) and not department_ids_for_role(actor, "hod") and not department_ids_for_role(actor, "dept_admin"):
            raise PermissionDeniedError("Actor is not associated with the department.")

        # Check completion status
        if not announcement_domain.is_complete(title, body, target_roles):
            raise ConflictError(code="content_required", message="Announcement content is incomplete.")

        # Create announcement
        announcement = Announcement.objects.create(
            department=department,
            title=title,
            body=body,
            target_roles=target_roles,
            target_programme=target_programme,
            target_batch_year=target_batch_year,
            published_by_user_id=actor.user_id,
            published_role=actor.active_role,
        )

        # Send notifications
        _send_notifications(announcement, actor, department.code)
        return announcement


def edit(*, actor, announcement_id: int, title: str, body: str, target_roles: list[str], target_programme: str = "", target_batch_year: int = None):
    """Edits an existing announcement."""
    require(actor, "department.announcement.update")
    with transaction.atomic():
        announcement = Announcement.objects.select_for_update().get(pk=announcement_id)

        # Check if actor can manage this announcement
        if announcement.department.code not in member_department_codes(actor) and announcement.department.id not in department_ids_for_role(actor, "hod") and announcement.department.id not in department_ids_for_role(actor, "dept_admin"):
            raise PermissionDeniedError("Actor cannot manage this announcement.")

        # Re-check completion status
        if not announcement_domain.is_complete(title, body, target_roles):
            raise ConflictError(code="content_required", message="Announcement content is incomplete.")

        # Update and save
        announcement.title = title
        announcement.body = body
        announcement.target_roles = target_roles
        announcement.target_programme = target_programme
        announcement.target_batch_year = target_batch_year
        announcement.save()
        return announcement


def hide(*, actor, announcement_id: int):
    """Hides an announcement."""
    require(actor, "department.announcement.update")
    with transaction.atomic():
        announcement = Announcement.objects.select_for_update().get(pk=announcement_id)

        # Check if actor can manage this announcement
        if announcement.department.code not in member_department_codes(actor) and announcement.department.id not in department_ids_for_role(actor, "hod") and announcement.department.id not in department_ids_for_role(actor, "dept_admin"):
            raise PermissionDeniedError("Actor cannot manage this announcement.")

        announcement.status = 'hidden'
        announcement.save()
        return announcement


def delete(*, actor, announcement_id: int):
    """Deletes an announcement."""
    require(actor, "department.announcement.delete")
    with transaction.atomic():
        announcement = Announcement.objects.select_for_update().get(pk=announcement_id)

        # Check if actor can manage this announcement
        if announcement.department.code not in member_department_codes(actor) and announcement.department.id not in department_ids_for_role(actor, "hod") and announcement.department.id not in department_ids_for_role(actor, "dept_admin"):
            raise PermissionDeniedError("Actor cannot manage this announcement.")

        announcement.status = 'deleted'
        announcement.save()
        return announcement
