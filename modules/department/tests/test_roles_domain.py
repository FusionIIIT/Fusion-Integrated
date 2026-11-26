# modules/department/tests/test_roles_domain.py
import pytest

from modules.department.domain.roles import role_kind
from modules.department.registry import PERMISSIONS, ROLE_GRANTS


@pytest.mark.parametrize(
    "active_role, expected_kind",
    [
        ("student", "student"),
        ("faculty", "faculty"),
        ("acadadmin", "institute_admin"),
        ("HOD (CSE)", "hod"),
        ("HOD (Design)", "hod"),
        ("HOD (ECE)", "hod"),
        ("HOD (Liberal Arts)", "hod"),
        ("HOD (ME)", "hod"),
        ("HOD (NS)", "hod"),
        ("dept_admin", "dept_admin"),
        ("deptadmin_cse", "dept_admin"),
        ("deptadmin_design", "dept_admin"),
        ("deptadmin_ece", "dept_admin"),
        ("deptadmin_liberalarts", "dept_admin"),
        ("deptadmin_me", "dept_admin"),
        ("deptadmin_ns", "dept_admin"),
        ("deptadmin_sm", "dept_admin"),
        ("unknown_role", None),
        ("dept_admin_x", None),
    ],
)
def test_role_kind_mapping(active_role, expected_kind):
    """Tests role_kind mapping for all defined and unknown roles."""
    assert role_kind(active_role) == expected_kind

def test_all_role_grants_permissions_exist():
    """Ensures every role grant maps to a permission defined in registry."""
    permission_codes = {code for code, _ in PERMISSIONS}
    for role, permissions in ROLE_GRANTS.items():
        for perm_code in permissions:
            assert perm_code in permission_codes, f"Permission {perm_code} used by role {role} is not defined in PERMISSIONS."

def test_acadadmin_is_a_role_grant_key():
    """Ensures 'acadadmin' is present in ROLE_GRANTS keys."""
    assert "acadadmin" in ROLE_GRANTS

def test_institute_admin_is_not_a_role_grant_key():
    """Ensures 'institute_admin' is not present in ROLE_GRANTS keys."""
    assert "institute_admin" not in ROLE_GRANTS
