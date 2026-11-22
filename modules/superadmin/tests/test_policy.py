"""Policy tests for Super Admin governance rules."""

import pytest

from modules.superadmin.domain.exceptions import (
    DualAuthorizationRequiredError,
    PolicyViolationError,
    SingularRoleConflictError,
)
from modules.superadmin.domain.policy import (
    check_separation_of_duties,
    check_singular_role_conflict,
    validate_role_compatibility,
)


def test_separation_of_duties_enforcement():
    # Requester cannot approve their own purge request
    admin_id = 1001
    with pytest.raises(DualAuthorizationRequiredError):
        check_separation_of_duties(requester_user_id=admin_id, authorizer_user_id=admin_id)

    # Different user can approve
    check_separation_of_duties(requester_user_id=1001, authorizer_user_id=2002)


def test_singular_role_occupancy_policy():
    # Assigning an already occupied singular role to another user fails
    with pytest.raises(SingularRoleConflictError):
        check_singular_role_conflict(
            "Dean of Academic Affairs", current_holder_user_id=50, new_holder_user_id=51
        )

    # Re-assigning to the existing occupant succeeds
    check_singular_role_conflict(
        "Dean of Academic Affairs", current_holder_user_id=50, new_holder_user_id=50
    )


def test_user_type_role_eligibility():
    # Students cannot be assigned administrative/faculty governance roles
    for role in ["Dean of Academic Affairs", "Head of Department (CSE)", "Registrar"]:
        with pytest.raises(PolicyViolationError):
            validate_role_compatibility("STUDENT", role)

    # Faculty can be assigned these roles
    for role in ["Dean of Academic Affairs", "Head of Department (CSE)"]:
        validate_role_compatibility("FACULTY", role)
