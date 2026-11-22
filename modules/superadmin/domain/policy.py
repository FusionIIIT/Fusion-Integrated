"""Pure-Python institutional policy and rule enforcement."""

from datetime import datetime, timedelta

from modules.superadmin.domain.exceptions import PolicyConflictError


def is_user_eligible_for_archival(
    deactivation_date: datetime | None,
    current_time: datetime,
    min_interval_days: int = 30,
    has_pending_work: bool = False,
) -> tuple[bool, str]:
    # BR-SA-004: Archival eligibility requires deactivation and minimum elapsed interval.
    if has_pending_work:
        return False, "User has unresolved pending academic or administrative transactions."
    if not deactivation_date:
        return False, "User must be deactivated before archival."
    min_eligible_date = deactivation_date + timedelta(days=min_interval_days)
    if current_time < min_eligible_date:
        days_remaining = (min_eligible_date - current_time).days + 1
        return (
            False,
            (
                "Minimum interval between deactivation and archival has not elapsed "
                f"({days_remaining} days remaining)."
            ),
        )
    return True, ""


def is_archived_user_restorable(
    reversibility_expires_at: datetime | None,
    current_time: datetime,
) -> tuple[bool, str]:
    # BR-SA-005: Reversibility window check for archived user accounts.
    if not reversibility_expires_at:
        return False, "User account is not in a reversible archival window."
    if current_time > reversibility_expires_at:
        return (
            False,
            (
                "Archived user reversibility window has expired; "
                "account is permanently non-restorable."
            ),
        )
    return True, ""


def check_role_conflicts(user_type: str, role_name: str, existing_roles: list[str]) -> None:
    # BR-SA-010 & BR-SA-011: Role user-type eligibility and conflict validation.
    user_type_upper = user_type.upper()
    role_clean = role_name.strip()

    # Students cannot hold Dean, HOD, Professor, or Audit roles.
    if user_type_upper == "STUDENT":
        forbidden_student = (
            "Dean",
            "HOD",
            "Head of Department",
            "Professor",
            "Registrar",
            "Auditor",
            "Super Admin",
        )
        if any(f.lower() in role_clean.lower() for f in forbidden_student):
            raise PolicyConflictError(
                f"Students are not eligible for administrative role {role_clean!r}."
            )

    # Conflict check: cannot hold conflicting dual roles.
    if "Exam Officer" in existing_roles and "Student Welfare" in role_clean:
        raise PolicyConflictError(
            "Conflict of interest between Exam Officer and Student Welfare roles."
        )


def validate_dual_authorization(requester_id: int, authorizer_id: int) -> None:
    # BR-SA-022: Dual authorization for purge; authorizer cannot be requester.
    if requester_id == authorizer_id:
        raise PolicyConflictError(
            "Dual authorization requires a distinct second authorizer; self-approval is forbidden."
        )


def refuse_self_superadmin_modification(
    acting_user_id: int, target_user_id: int, action: str
) -> None:
    # BR-SA-028: Super Admin cannot modify or revoke their own superadmin account status.
    if acting_user_id == target_user_id and action in ("deactivate", "revoke_superadmin"):
        raise PolicyConflictError(
            "Super Admin cannot deactivate or revoke their own superadmin account."
        )


SINGULAR_ROLES = frozenset(
    {
        "Dean of Academic Affairs",
        "Head of Department (CSE)",
        "Head of Department (ECE)",
        "Head of Department (ME)",
        "Registrar",
        "Director",
    }
)


def is_role_singular(role_name: str) -> bool:
    return any(
        s.lower() in role_name.lower()
        for s in ("dean", "head of department", "hod", "director", "registrar")
    )


def check_singular_role_conflict(
    role_name: str, current_holder_user_id: int | None, new_holder_user_id: int
) -> None:
    if (
        is_role_singular(role_name)
        and current_holder_user_id is not None
        and current_holder_user_id != new_holder_user_id
    ):
        raise PolicyConflictError(
            f"Singular role {role_name!r} is already actively held by user "
            f"{current_holder_user_id}."
        )


def validate_role_compatibility(user_type: str, role_name: str) -> None:
    check_role_conflicts(user_type, role_name, [])


def check_separation_of_duties(requester_user_id: int, authorizer_user_id: int) -> None:
    validate_dual_authorization(requester_user_id, authorizer_user_id)


def calculate_reversibility_expiry(archival_date: datetime, window_days: int = 90) -> datetime:
    return archival_date + timedelta(days=window_days)


def validate_reversibility_window(
    reversibility_expires_at: datetime | None, current_time: datetime
) -> None:
    ok, reason = is_archived_user_restorable(reversibility_expires_at, current_time)
    if not ok:
        raise PolicyConflictError(reason)


def is_purge_eligible(purge_eligible_at: datetime | None, current_time: datetime) -> bool:
    if not purge_eligible_at:
        return False
    return current_time >= purge_eligible_at
