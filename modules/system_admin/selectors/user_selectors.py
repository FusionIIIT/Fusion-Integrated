"""Read selectors for UserAccount records."""
from __future__ import annotations

from django.db.models import Q

from modules.system_admin.models.user_account import UserAccount


def get_user_by_id(user_id: int) -> UserAccount | None:
    """Retrieve user account by internal user_id."""
    return UserAccount.objects.filter(user_id=user_id).first()


def get_user_by_institute_id(institute_id: str) -> UserAccount | None:
    """Retrieve user account by unique institute_id."""
    return UserAccount.objects.filter(institute_id=institute_id.strip()).first()


def list_users(
    *,
    query: str | None = None,
    user_type: str | None = None,
    status: str | None = None,
    department: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[UserAccount], int]:
    """Search and filter user accounts (AFR-SA-010, AFR-SA-058)."""
    qs = UserAccount.objects.all()

    if user_type:
        qs = qs.filter(user_type=user_type.strip().lower())
    if status:
        qs = qs.filter(status=status.strip().lower())
    if department:
        qs = qs.filter(department__iexact=department.strip())

    if query:
        q = query.strip()
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(name__icontains=q)
            | Q(institute_id__icontains=q)
            | Q(email__icontains=q)
        )

    total_count = qs.count()
    users = list(qs[offset : offset + limit])
    return users, total_count
