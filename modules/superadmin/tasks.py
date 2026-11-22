"""Celery tasks for Super Admin."""

from celery import shared_task

from modules.superadmin.services.roles import (
    activate_scheduled_roles as _activate_scheduled_roles,
)
from modules.superadmin.services.roles import (
    expire_time_bound_roles as _expire_time_bound_roles,
)
from modules.superadmin.services.user_archive import (
    finalize_reversibility_expiry as _finalize_reversibility_expiry,
)


@shared_task(name="superadmin.finalize_archived_user_reversibility_expiry")
def finalize_archived_user_reversibility_expiry() -> int:
    # BW-SA-08 Transition 2: sweeps expired reversible accounts.
    return _finalize_reversibility_expiry()


@shared_task(name="superadmin.activate_scheduled_roles")
def activate_scheduled_roles() -> int:
    # BW-SA-04: activates scheduled role assignments.
    return _activate_scheduled_roles()


@shared_task(name="superadmin.expire_time_bound_roles")
def expire_time_bound_roles() -> int:
    # BW-SA-03: expires elapsed time-bound roles.
    return _expire_time_bound_roles()


expire_reversibility_windows_task = finalize_archived_user_reversibility_expiry
activate_scheduled_roles_task = activate_scheduled_roles
expire_roles_task = expire_time_bound_roles
