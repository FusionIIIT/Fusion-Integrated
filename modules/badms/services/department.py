"""Department resolution and HoD scoping service."""
from __future__ import annotations

from typing import TYPE_CHECKING
from modules.directory import contracts as directory
from modules.badms.domain import permissions as p

if TYPE_CHECKING:
    from fusion_auth.principal import Principal


def get_user_department(user_id: int) -> str:
    """Retrieve the department for a given user from the directory projection."""
    if not user_id:
        return ""
    users = directory.get_users([user_id])
    user_dto = users.get(user_id)
    if not user_dto:
        return ""
    return (user_dto.department or user_dto.discipline or "").strip().upper()


def is_hod_of_department(principal: Principal, target_department: str) -> bool:
    """Check whether the principal is the designated HoD for the target department.

    Separation of duties:
    - User must hold the HoD review permission (badms.archive.review or badms.storage.review).
    - User's own registered department must match the target department.
    """
    if not principal:
        return False

    has_hod_role = (
        principal.has_permission(p.ARCHIVE_REVIEW)
        or principal.has_permission(p.STORAGE_REVIEW)
        or (principal.active_role or "").upper() == "HOD"
    )
    if not has_hod_role:
        return False

    target = (target_department or "").strip().upper()
    if not target:
        return False

    hod_dept = get_user_department(principal.user_id)
    return hod_dept == target


def can_review_department_request(principal: Principal, target_department: str) -> bool:
    """Verify if the caller is authorized to review or action department-scoped requests.

    - HoD of the respective department: ALLOWED.
    - HoD of another department: DENIED (prevents cross-department access).
    - SysAdmin / Super Admin: ALLOWED for global oversight.
    """
    if not principal:
        return False

    # Super Admin and SysAdmin hold archive classification and global administration
    if principal.has_permission(p.ARCHIVE_CLASSIFY) or (principal.active_role or "") in (
        "Super Admin",
        "sysadmin",
        "SysAdmin",
        "admin",
    ):
        return True

    return is_hod_of_department(principal, target_department)
