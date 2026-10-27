"""Cross-module lookup boundary; all identity fields are Fusion IAM IDs."""

from modules.elm.models import EmployeeLeaveProfile


def get_employee_leave_profiles(user_ids: list[int]):
    return list(
        EmployeeLeaveProfile.objects.filter(user_id__in=user_ids).values(
            "user_id", "category", "unit", "designation"
        )
    )
