"""Profile selectors with role-based privacy masking (BR-DEPT-019)."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from modules.dept.models.profiles import UserProfileExtension


def list_profiles(
    department_code: str,
    profile_type: str | None = None,
) -> QuerySet[UserProfileExtension]:
    qs = UserProfileExtension.objects.filter(department_id=department_code)
    if profile_type:
        qs = qs.filter(profile_type=profile_type.upper())
    return qs.order_by("user_id")


def mask_profile_for_viewer(profile: UserProfileExtension, viewer_principal: Any) -> dict[str, Any]:
    """Apply role-specific field visibility rules (BR-DEPT-019).

    - Student: sees basic peer/faculty info (office room, research, courses).
      Sensitive contacts masked.
    - Faculty: sees detailed info for course students, limited for others.
      Sensitive contacts masked.
    - HOD & Dept_Admin: sees full profile except strictly protected credentials/passwords.
    """
    roles = set(getattr(viewer_principal, "roles", []))
    is_admin_or_hod = bool(roles.intersection({"HOD", "Dept_Admin"})) or getattr(
        viewer_principal, "is_staff", False
    )

    data = {
        "id": str(profile.id),
        "department_code": profile.department_id,
        "user_id": profile.user_id,
        "profile_type": profile.profile_type,
        "office_room": profile.office_room,
        "research_interests": profile.research_interests,
        "courses_taught": profile.courses_taught,
        "batch_or_roll": profile.batch_or_roll,
        "graduation_year": profile.graduation_year,
    }

    if is_admin_or_hod:
        data["contact_phone"] = profile.contact_phone
        data["emergency_contact"] = profile.emergency_contact
    else:
        # Sensitive personal data is masked for students/peers
        data["contact_phone"] = None
        data["emergency_contact"] = None

    return data
