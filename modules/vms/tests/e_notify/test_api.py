"""Inbox, arrivals, visitor routes and ops outbox: auth matrix + ownership."""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.api import csrf
from modules.vms import auth
from modules.vms.models import Notification
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db

BASE = "/api/v1/vms/"
VIEW = "vms.notification.view_self"
RAW = "visitor-raw-token"


def _visitor_client(visitor=None):
    visitor = visitor or f.make_visitor()
    f.make_visitor_session(visitor=visitor, token_hash=auth.hash_token(RAW),
                           verified_at=timezone.now())
    c = APIClient()
    c.cookies[auth.COOKIE_NAME] = RAW
    c.credentials(HTTP_X_CSRF_TOKEN=csrf.token_for(RAW))
    return c, visitor


STAFF_ENDPOINTS = [
    ("get", "notify/inbox", VIEW),
    ("get", "notify/unread-count", VIEW),
    ("post", "notify/1/read", VIEW),
    ("post", "notify/read-all", VIEW),
    ("get", "notify/arrivals", VIEW),
    ("get", "notify/outbox", "vms.audit.view"),
    ("post", "notify/outbox/1/retry", "vms.audit.view"),
]


@pytest.mark.parametrize("method,path,perm", STAFF_ENDPOINTS)
def test_anonymous_is_401(api_as, method, path, perm):
    assert getattr(api_as(anonymous=True), method)(BASE + path).status_code == 401


@pytest.mark.parametrize("method,path,perm", STAFF_ENDPOINTS)
def test_wrong_permission_is_403(api_as, method, path, perm):
    assert getattr(api_as(permissions=("vms.request.decide",)), method)(
        BASE + path).status_code == 403


def test_visitor_routes_anonymous_401_and_iam_user_denied(api_as):
    assert APIClient().get(BASE + "visitor/notifications").status_code == 401
    assert api_as(permissions=(VIEW,)).get(
        BASE + "visitor/notifications").status_code in (401, 403)


def test_inbox_only_own_and_unread_count(api_as):
    mine = f.make_notification(recipient_user_id=2001)
    f.make_notification(recipient_user_id=2002)
    f.make_notification(recipient_user_id=2001, channel="email")
    c = api_as(user_id=2001, permissions=(VIEW,))
    ids = [r["id"] for r in c.get(BASE + "notify/inbox").json()["results"]]
    assert ids == [mine.pk]
    assert c.get(BASE + "notify/unread-count").json() == {"unread": 1}


def test_mark_read_and_wrong_owner_is_404(api_as):
    mine = f.make_notification(recipient_user_id=2001)
    other = f.make_notification(recipient_user_id=2002)
    c = api_as(user_id=2001, permissions=(VIEW,))
    assert c.post(BASE + f"notify/{other.pk}/read").status_code == 404
    other.refresh_from_db()
    assert other.read_at is None
    assert c.post(BASE + f"notify/{mine.pk}/read").status_code == 200
    mine.refresh_from_db()
    assert mine.read_at is not None


def test_read_all_only_touches_own(api_as):
    f.make_notification(recipient_user_id=2001)
    f.make_notification(recipient_user_id=2001)
    other = f.make_notification(recipient_user_id=2002)
    c = api_as(user_id=2001, permissions=(VIEW,))
    assert c.post(BASE + "notify/read-all").json() == {"marked": 2}
    other.refresh_from_db()
    assert other.read_at is None


def test_uc_015_arrivals_join_request_info(api_as):
    vp = f.make_visit_pass()
    log = f.make_visit_log(visit_pass=vp, event="check_in")
    req = vp.visit_request
    f.make_notification(recipient_user_id=req.host_user_id, topic="visit.checked_in",
                        dedupe_key=f"visit.checked_in:{log.pk}:inapp")
    f.make_notification(recipient_user_id=req.host_user_id, topic="visit.checked_in",
                        dedupe_key="odd-key")
    f.make_notification(recipient_user_id=req.host_user_id, topic="request.submitted")
    f.make_notification(recipient_user_id=9999, topic="visit.checked_in")
    c = api_as(user_id=req.host_user_id, permissions=(VIEW,))
    rows = c.get(BASE + "notify/arrivals").json()["results"]
    assert len(rows) == 2
    joined = [r for r in rows if r["request"]]
    assert len(joined) == 1
    assert joined[0]["request"]["id"] == req.pk
    assert joined[0]["request"]["visitor_name"] == req.visitor.full_name


def test_visitor_inbox_only_own():
    c, v = _visitor_client()
    mine = f.make_notification(recipient_user_id=None, recipient_visitor=v)
    f.make_notification(recipient_user_id=None, recipient_visitor=f.make_visitor())
    f.make_notification(recipient_user_id=2001)
    body = c.get(BASE + "visitor/notifications").json()
    assert [r["id"] for r in body["results"]] == [mine.pk] and body["unread"] == 1
    assert c.post(BASE + f"visitor/notifications/{mine.pk}/read").status_code == 200


def test_visitor_cannot_read_host_notifications():
    c, _ = _visitor_client()
    host_row = f.make_notification(recipient_user_id=2001)
    other_visitor_row = f.make_notification(recipient_user_id=None,
                                            recipient_visitor=f.make_visitor())
    for row in (host_row, other_visitor_row):
        assert c.post(BASE + f"visitor/notifications/{row.pk}/read").status_code == 404
        row.refresh_from_db()
        assert row.read_at is None


def test_visitor_post_needs_csrf():
    c, v = _visitor_client()
    c.credentials()   # drop the csrf header
    n = f.make_notification(recipient_user_id=None, recipient_visitor=v)
    assert c.post(BASE + f"visitor/notifications/{n.pk}/read").status_code == 403


def test_visitor_session_cannot_use_staff_inbox():
    c, _ = _visitor_client()
    assert c.get(BASE + "notify/inbox").status_code in (401, 403)


def test_outbox_filter_and_retry(api_as):
    bad = f.make_notification(status="failed", attempts=5, channel="email")
    f.make_notification(status="sent")
    c = api_as(permissions=("vms.audit.view",))
    rows = c.get(BASE + "notify/outbox?status=failed").json()["results"]
    assert [r["id"] for r in rows] == [bad.pk]
    assert c.post(BASE + f"notify/outbox/{bad.pk}/retry").status_code == 200
    assert Notification.objects.get(pk=bad.pk).status == "pending"
    assert c.post(BASE + f"notify/outbox/{bad.pk}/retry").status_code == 409
    assert c.post(BASE + "notify/outbox/99999/retry").status_code == 404
