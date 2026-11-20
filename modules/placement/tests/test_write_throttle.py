"""Every write is throttled; a list page that shares the view is not."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session

pytestmark = pytest.mark.django_db

RATES = {"placement_write": "2/hour"}


def _client(stub_iam):
    stub_iam(make_session(user_id=62, kind="staff", modules=("placement",),
                          permissions=("placement.announcement.publish",)))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_writes_past_the_rate_are_429_and_reads_are_never_limited(stub_iam, monkeypatch):
    from core.api.throttling import PrincipalScopedThrottle
    monkeypatch.setattr(PrincipalScopedThrottle, "THROTTLE_RATES",
                        {**PrincipalScopedThrottle.THROTTLE_RATES, **RATES})
    c = _client(stub_iam)
    body = {"title": "Drive", "body": "Hall 2.", "topic": "drive"}
    codes = [c.post("/api/v1/placement/announcements", body, format="json").status_code
             for _ in range(3)]
    assert codes == [201, 201, 429]
    assert all(c.get("/api/v1/placement/announcements").status_code == 200 for _ in range(5))


def test_every_write_view_declares_a_throttle_scope():
    import ast
    import pathlib

    api = pathlib.Path(__file__).resolve().parents[1] / "api"
    missing = []
    for f in api.glob("*.py"):
        for c in [n for n in ast.parse(f.read_text()).body if isinstance(n, ast.ClassDef)]:
            names = {m.name for m in c.body if isinstance(m, ast.FunctionDef)}
            generic = any("Create" in ast.unparse(b) or "Update" in ast.unparse(b)
                          for b in c.bases)
            writes = bool(names & {"post", "put", "patch", "delete"}) or generic
            scoped = "throttle_scope" in ast.unparse(c)
            if writes and not scoped:
                missing.append(f"{f.name}:{c.name}")
    assert missing == []

