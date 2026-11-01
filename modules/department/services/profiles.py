import django.db.transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.department.models import CourseRoster, Department, DepartmentProfile
from modules.department.selectors.scoping import department_ids_for_role
from modules.department.services.authz import require


def _held(actor, department_id: int) -> Department:
    """Locks and returns the Department if actor has dept_admin role for it."""
    if department_id not in department_ids_for_role(actor, "dept_admin"):
        raise NotFoundError("Department not held by actor as dept_admin")

    with django.db.transaction.atomic():
        department = Department.objects.select_for_update().filter(pk=department_id).first()
        if not department:
            raise NotFoundError("Department not found")
        return department

def create_profile(*, actor, department_id, data: dict):
    """Creates a new DepartmentProfile."""
    require(actor, "department.profile.update")

    with django.db.transaction.atomic():
        try:
            department = _held(actor, department_id)
        except NotFoundError as e:
            raise e

        profile = DepartmentProfile.objects.create(
            department=department,
            **data
        )
        return profile

def update_profile(*, actor, profile: 'DepartmentProfile', data: dict):
    """Updates an existing DepartmentProfile."""
    require(actor, "department.profile.update")

    with django.db.transaction.atomic():
        try:
            # 1. Find the profile and lock the department context
            department = _held(actor, profile.department_id)
            profile.department = department
        except NotFoundError as e:
            raise e

        # 2. Apply updates
        for key, value in data.items():
            setattr(profile, key, value)
        profile.save()
        return profile

def deactivate_profile(*, actor, profile_id: int):
    """Deactivates an existing DepartmentProfile."""
    require(actor, "department.profile.update")

    with django.db.transaction.atomic():
        try:
            # 1. Find the profile and lock the department context
            profile = DepartmentProfile.objects.select_for_update().get(pk=profile_id)
            department = _held(actor, profile.department_id)
        except DepartmentProfile.DoesNotExist:
            raise NotFoundError("Profile not found")
        except NotFoundError as e:
            raise e

        # 2. Deactivate
        profile.is_active = False
        profile.save()
        return profile

def add_roster(*, actor, department_id, data: dict):
    """Adds a new CourseRoster entry."""
    require(actor, "department.roster.update")

    with django.db.transaction.atomic():
        try:
            department = _held(actor, department_id)
        except NotFoundError as e:
            raise e

        try:
            roster = CourseRoster.objects.create(
                department=department,
                **data
            )
            return roster
        except django.db.utils.IntegrityError:
            raise ConflictError("Roster entry already exists.", code="duplicate_roster")
