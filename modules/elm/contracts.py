"""Cross-module lookup boundary; all identity fields are Fusion IAM IDs."""

from collections.abc import Sequence

from modules.elm.models import EmployeeLeaveProfile


def get_employee_leave_profiles(user_ids: Sequence[int]) -> list[dict]:
    return list(
        EmployeeLeaveProfile.objects.filter(user_id__in=list(user_ids)).values(
            "user_id", "category", "unit", "designation"
        )
    )
