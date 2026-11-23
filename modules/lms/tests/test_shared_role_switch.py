import pytest

from conftest import make_session
from fusion_auth.client import IamUnavailable
from modules.lms.registry import ROLE_GRANTS

pytestmark = pytest.mark.django_db


def test_patch_returns_selected_role_permissions_then_get_agrees(world):
    client = world.actor(roles=("faculty", "student"))
    world.fake.role_sessions = {
        "student": make_session(
            user_id=1,
            kind="faculty",
            roles=("faculty", "student"),
            active_role="student",
            modules=("lms",),
            permissions=ROLE_GRANTS["student"],
        )
    }
    response = client.patch("/api/v1/me", {"active_role": "student"}, format="json")
    assert response.status_code == 200 and response.json()["active_role"] == "student"
    assert "lms.course.update" not in response.json()["permissions"]
    assert response.json()["permissions"] == sorted(ROLE_GRANTS["student"])
    assert client.get("/api/v1/me").json()["active_role"] == "student"


def test_role_switch_cannot_select_an_unheld_designation(world):
    response = world.actor().patch("/api/v1/me", {"active_role": "unheld"}, format="json")
    assert response.status_code == 422 and response.json()["error"]["code"] == "unknown_role"


@pytest.mark.parametrize("outage", [False, True])
def test_role_refresh_refuses_expired_session_or_iam_outage(world, monkeypatch, outage):
    client = world.actor(roles=("faculty", "student"))
    original = world.fake.resolve_session

    def resolve(**kwargs):
        if any(call[0] == "set_active_role" for call in world.fake.calls):
            if outage:
                raise IamUnavailable("Synthetic refresh outage")
            return None
        return original(**kwargs)

    monkeypatch.setattr(world.fake, "resolve_session", resolve)
    response = client.patch("/api/v1/me", {"active_role": "student"}, format="json")
    assert response.status_code == (503 if outage else 401)
    assert response.json().get("active_role") is None
