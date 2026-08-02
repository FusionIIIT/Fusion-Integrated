"""Ownership is enforced by the selector, so a foreign id is a 404 not a 403."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.placement.models import Application, Company, JobPosting

pytestmark = pytest.mark.django_db


@pytest.fixture
def posting():
    c = Company.objects.create(name="Acme", slug="acme", status="active")
    return JobPosting.objects.create(
        company=c, title="SDE-1", placement_year="2026-27", status="draft",
        created_by_user_id=1)


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_student_sees_only_their_own_applications(stub_iam, posting, user_ref):
    Application.objects.create(posting=posting, user_id=1001, status="submitted")
    Application.objects.create(posting=posting, user_id=2002, status="submitted")

    stub_iam(make_session(user_id=1001, modules=("placement_cell",),
                          permissions=("placement_cell.application.view_self",)),
             users={1001: user_ref(1001)})
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    rows = c.get("/api/v1/placement/applications").json()["results"]
    assert [r["user_id"] for r in rows] == [1001]


def test_coordinator_sees_everyone(stub_iam, posting, user_ref):
    Application.objects.create(posting=posting, user_id=1001, status="submitted")
    Application.objects.create(posting=posting, user_id=2002, status="submitted")

    stub_iam(make_session(user_id=9, kind="staff", modules=("placement_cell",),
                          permissions=("placement_cell.application.view",)),
             users={1001: user_ref(1001), 2002: user_ref(2002, "Bo Li")})
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    rows = c.get("/api/v1/placement/applications").json()["results"]
    assert sorted(r["user_id"] for r in rows) == [1001, 2002]


def test_applicant_names_cost_one_batched_directory_call(stub_iam, posting, user_ref):
    for uid in range(3001, 3011):
        Application.objects.create(posting=posting, user_id=uid, status="submitted")
    fake = stub_iam(
        make_session(user_id=9, modules=("placement_cell",),
                     permissions=("placement_cell.application.view",)),
        users={uid: user_ref(uid) for uid in range(3001, 3011)})
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    c.get("/api/v1/placement/applications")

    calls = [x for x in fake.calls if x[0] == "get_users"]
    assert len(calls) == 1, "directory must be hit once per page, not once per row"


def test_illegal_transition_is_409_not_500(stub_iam, posting):
    """Regression: InvalidTransition is a pure-domain exception. If the service
    does not translate it, it escapes the DRF handler as a 500."""
    app = Application.objects.create(posting=posting, user_id=1001,
                                     status="submitted")
    c = _client(stub_iam, user_id=9, modules=("placement_cell",),
                permissions=("placement_cell.application.review",))
    r = c.post(f"/api/v1/placement/applications/{app.id}/transition",
               {"to_status": "offer_accepted"}, format="json")
    assert r.status_code == 409
    body = r.json()["error"]
    assert body["code"] == "invalid_transition"
    assert "under_review" in body["details"][0]["allowed"]


def test_reject_without_a_reason_is_refused(stub_iam, posting):
    app = Application.objects.create(posting=posting, user_id=1001,
                                     status="submitted")
    c = _client(stub_iam, user_id=9, modules=("placement_cell",),
                permissions=("placement_cell.application.review",))
    r = c.post(f"/api/v1/placement/applications/{app.id}/transition",
               {"to_status": "rejected"}, format="json")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "reason_required"


def test_someone_elses_application_is_404_not_403(stub_iam, posting):
    """The distinction this module cares about. A 403 would confirm that
    application 17 exists — for placement data that is itself a disclosure, so
    a foreign row must be indistinguishable from a nonexistent one."""
    app = Application.objects.create(posting=posting, user_id=1001,
                                     status="submitted")
    c = _client(stub_iam, user_id=9, modules=("placement_cell",),
                permissions=("placement_cell.application.view_self",))
    r = c.post(f"/api/v1/placement/applications/{app.id}/transition",
               {"to_status": "under_review"}, format="json")
    assert r.status_code == 404

    missing = c.post("/api/v1/placement/applications/99999/transition",
                     {"to_status": "under_review"}, format="json")
    assert missing.status_code == 404
    assert r.json()["error"]["code"] == missing.json()["error"]["code"]


def test_a_student_cannot_drive_a_staff_transition_on_their_own_application(
        stub_iam, posting):
    """In scope, so it resolves — and is then refused on the actor lane."""
    app = Application.objects.create(posting=posting, user_id=1001,
                                     status="submitted")
    c = _client(stub_iam, user_id=1001, modules=("placement_cell",),
                permissions=("placement_cell.application.view_self",))
    r = c.post(f"/api/v1/placement/applications/{app.id}/transition",
               {"to_status": "under_review"}, format="json")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "actor_not_allowed"


def test_a_student_coordinator_cannot_shortlist_their_own_application(
        stub_iam, posting):
    """Conflict of interest. A student placement coordinator legitimately
    reviews other people's applications, but must not self-approve — acting on
    their own row drops them back into the student lane."""
    own = Application.objects.create(posting=posting, user_id=77,
                                     status="submitted")
    other = Application.objects.create(posting=posting, user_id=1001,
                                       status="submitted")
    c = _client(stub_iam, user_id=77, kind="student",
                modules=("placement_cell",),
                permissions=("placement_cell.application.review",))

    mine = c.post(f"/api/v1/placement/applications/{own.id}/transition",
                  {"to_status": "under_review"}, format="json")
    assert mine.status_code == 403
    assert mine.json()["error"]["code"] == "actor_not_allowed"

    theirs = c.post(f"/api/v1/placement/applications/{other.id}/transition",
                    {"to_status": "under_review"}, format="json")
    assert theirs.status_code == 200


def test_every_transition_is_audited(stub_iam, posting):
    from modules.placement.models import ApplicationTransition
    app = Application.objects.create(posting=posting, user_id=1001,
                                     status="submitted")
    c = _client(stub_iam, user_id=9, modules=("placement_cell",),
                permissions=("placement_cell.application.review",))
    c.post(f"/api/v1/placement/applications/{app.id}/transition",
           {"to_status": "under_review"}, format="json")
    t = ApplicationTransition.objects.get(application=app)
    assert (t.from_status, t.to_status, t.actor_user_id) == ("submitted",
                                                             "under_review", 9)
