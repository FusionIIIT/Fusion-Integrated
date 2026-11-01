"""User Selectors for System Admin Control Plane."""
from django.db.models import Q
from modules.systemadmin.models.user_mgmt import BasicUserProfile, UserStatusHistory


def get_user_by_id(user_id: int) -> BasicUserProfile | None:
    return BasicUserProfile.objects.filter(id=user_id).first()


def get_user_by_institute_id(institute_id: str) -> BasicUserProfile | None:
    return BasicUserProfile.objects.filter(institute_id=institute_id).first()


def list_users(
    search: str | None = None,
    user_type: str | None = None,
    status: str | None = None,
    department: str | None = None,
    programme: str | None = None,
    batch_year: int | None = None,
):
    qs = BasicUserProfile.objects.all().order_by("institute_id")
    if search:
        qs = qs.filter(
            Q(institute_id__icontains=search) |
            Q(full_name__icontains=search) |
            Q(institute_email__icontains=search) |
            Q(employee_id__icontains=search)
        )
    if user_type:
        qs = qs.filter(user_type=user_type)
    if status:
        qs = qs.filter(status=status)
    if department:
        qs = qs.filter(department__icontains=department)
    if programme:
        qs = qs.filter(programme__icontains=programme)
    if batch_year:
        qs = qs.filter(batch_year=batch_year)
    return qs


def get_user_status_history(user_id: int):
    return UserStatusHistory.objects.filter(user_id=user_id).order_by("-changed_at")
