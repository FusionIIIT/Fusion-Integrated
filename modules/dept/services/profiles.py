"""User profile extension services (CFR-DEPT-009)."""

from __future__ import annotations

from modules.dept.models.department import Department
from modules.dept.models.profiles import UserProfileExtension


def save_user_profile_extension(
    department_code: str,
    user_id: str,
    profile_type: str,
    office_room: str = "",
    research_interests: str = "",
    contact_phone: str = "",
    emergency_contact: str = "",
    courses_taught: list | None = None,
    batch_or_roll: str = "",
    graduation_year: int | None = None,
) -> UserProfileExtension:
    dept, _ = Department.objects.get_or_create(
        code=department_code,
        defaults={"name": f"Department of {department_code}"},
    )

    profile, _ = UserProfileExtension.objects.update_or_create(
        department=dept,
        user_id=user_id.strip(),
        defaults={
            "profile_type": profile_type.upper().strip(),
            "office_room": office_room.strip(),
            "research_interests": research_interests.strip(),
            "contact_phone": contact_phone.strip(),
            "emergency_contact": emergency_contact.strip(),
            "courses_taught": courses_taught or [],
            "batch_or_roll": batch_or_roll.strip(),
            "graduation_year": graduation_year,
        },
    )
    return profile
