"""User selectors for System Admin module.

Enforces read-only profile access and Super Admin data isolation (BR-SA-026).
Operational content (grades, financial ledgers, complaint details, etc.) is
never exposed through these selectors.
"""
from collections.abc import Sequence
from django.db.models import Q, QuerySet

from modules.system_admin.models import BasicUser


def list_basic_users(
    *,
    user_type: str | None = None,
    status: str | None = None,
    department: str | None = None,
    batch_year: int | None = None,
    q: str | None = None,
) -> QuerySet[BasicUser]:
    """Query basic users with optional filtering.

    Excludes operational content per BR-SA-026.
    """
    qs = BasicUser.objects.all().order_by("user_id")

    if user_type:
        qs = qs.filter(user_type=user_type)
    if status:
        qs = qs.filter(status=status)
    if department:
        qs = qs.filter(department__iexact=department)
    if batch_year:
        qs = qs.filter(batch_year=batch_year)
    if q and q.strip():
        term = q.strip()
        qs = qs.filter(
            Q(institute_id__icontains=term)
            | Q(first_name__icontains=term)
            | Q(last_name__icontains=term)
            | Q(email__icontains=term)
            | Q(employee_id__icontains=term)
        )

    return qs


def get_user_by_id(user_id: int) -> BasicUser | None:
    return BasicUser.objects.filter(user_id=user_id).first()


def get_user_by_institute_id(institute_id: str) -> BasicUser | None:
    return BasicUser.objects.filter(institute_id__iexact=institute_id.strip()).first()


def get_users_by_ids(user_ids: Sequence[int]) -> dict[int, BasicUser]:
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    users = BasicUser.objects.filter(user_id__in=ids)
    return {u.user_id: u for u in users}


def check_institute_id_exists(institute_id: str) -> bool:
    return BasicUser.objects.filter(institute_id__iexact=institute_id.strip()).exists()


def check_email_exists(email: str) -> bool:
    return BasicUser.objects.filter(email__iexact=email.strip()).exists()
