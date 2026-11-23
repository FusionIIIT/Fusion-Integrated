import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.oap import registry

BASE_URL = "/api/v1/oap"


class SpecActor:
    """Represents a signed-in actor with an IAM session."""

    def __init__(self, stub_iam, uid, roles, active, kind="student"):
        self.stub_iam = stub_iam
        self.uid = uid
        self.roles = roles
        self.active = active
        self.kind = kind
        self.perms = {c for r in roles for c in registry.ROLE_GRANTS.get(r, [])}
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Token spec-test-token")

    def _install(self):
        self.stub_iam(
            make_session(
                user_id=self.uid,
                kind=self.kind,
                modules=("oap",),
                permissions=self.perms,
                roles=tuple(self.roles),
                active_role=self.active,
            )
        )

    def get(self, path, **kwargs):
        self._install()
        return self.client.get(path, **kwargs)

    def post(self, path, data=None, **kwargs):
        self._install()
        return self.client.post(path, data, **kwargs)

    def put(self, path, data=None, **kwargs):
        self._install()
        return self.client.put(path, data, **kwargs)

    def delete(self, path, **kwargs):
        self._install()
        return self.client.delete(path, **kwargs)


@pytest.fixture
def spec_login():
    def _login(stub_iam, uid, roles, active, kind="student"):
        return SpecActor(stub_iam, uid, roles, active, kind)

    return _login


@pytest.fixture
def spec_assign(spec_login):
    def _assign(stub_iam, student_id, thesis_id, ta_id):
        da = spec_login(
            stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
        )
        r_th = da.post(
            f"{BASE_URL}/thesis-supervisor-assignments",
            {"student_user_id": student_id, "supervisor_user_id": thesis_id},
            format="json",
        )
        assert r_th.status_code == 201
        r_ta = da.post(
            f"{BASE_URL}/ta-assignments",
            {
                "student_user_id": student_id,
                "course_code": "CS101",
                "supervisor_user_id": ta_id,
            },
            format="json",
        )
        assert r_ta.status_code == 201
        return da

    return _assign


def extract_rows(resp):
    body = resp.json()
    return body["results"] if isinstance(body, dict) and "results" in body else body
