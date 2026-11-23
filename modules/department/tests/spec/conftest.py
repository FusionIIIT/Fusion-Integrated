import pytest
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.department.registry import ROLE_GRANTS


@pytest.fixture
def spec_client(stub_iam):
    """Factory fixture returning an APIClient configured for a given department role."""
    def as_role(role, user_id=10, department="CSE", kind=None, **attributes):
        if kind is None:
            if "student" in role:
                kind = "student"
            elif role == "faculty" or role.startswith("HOD"):
                kind = "faculty"
            elif "admin" in role:
                kind = "staff"
            else:
                kind = "faculty"

        permissions = ROLE_GRANTS.get(role, [])
        session = make_session(
            user_id=user_id,
            roles=[role],
            active_role=role,
            kind=kind,
            modules=["department"],
            permissions=permissions,
        )
        identity = UserRef(
            user_id,
            f"user_{user_id}",
            f"User {user_id}",
            kind,
            department=department,
            **attributes,
        )
        fake = stub_iam(
            session=session,
            users={
                user_id: identity,
                11: UserRef(11, "faculty_11", "Prof 11", "faculty", department="CSE"),
                12: UserRef(12, "student_12", "Student 12", "student", department="CSE", programme="BTech", batch_year=2024),
                13: UserRef(13, "hod_13", "HOD 13", "faculty", department="CSE"),
                14: UserRef(14, "admin_14", "Admin 14", "staff", department="CSE"),
            },
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token test-session")
        return client, fake

    return as_role
