"""Endpoint auth matrix and response shapes for events/* (lane G)."""
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from modules.vms.models import EventAttendee, VisitPass
from modules.vms.services import bulk_events as svc
from modules.vms.tests import factories as f
from modules.vms.tests.g_events.conftest import ADMIN_ID, csv_rows

pytestmark = pytest.mark.django_db

BASE = "/api/v1/vms/"

# (method, path, permission that opens the view, mutating)
ENDPOINTS = [
    ("get", "events", "vms.event.manage", False),
    ("post", "events", "vms.event.manage", True),
    ("get", "events/{e}", "vms.event.manage", False),
    ("patch", "events/{e}", "vms.event.manage", True),
    ("get", "events/{e}/attendees", "vms.event.manage", False),
    ("post", "events/{e}/attendees/upload", "vms.event.manage", True),
    ("delete", "events/{e}/attendees/1", "vms.event.manage", True),
    ("post", "events/{e}/approve", "vms.event.manage", True),
    ("post", "events/{e}/cancel", "vms.event.manage", True),
    ("get", "events/{e}/attendance", "vms.event.manage", False),
    ("get", "events/{e}/attendance", "vms.monitor.view", False),
    ("get", "events/{e}/throughput", "vms.monitor.view", False),
    ("get", "events/{e}/fast-lane-manifest", "vms.gate.sync", False),
]


def call(client, method, path, event, body=None):
    kw = {"format": "multipart" if "upload" in path else "json"}
    return getattr(client, method)(BASE + path.format(e=event.pk), body or {}, **kw)


@pytest.mark.parametrize("method,path,perm,mutating", ENDPOINTS)
def test_anonymous_is_401(api_as, event, method, path, perm, mutating):
    assert call(api_as(anonymous=True), method, path, event).status_code == 401


@pytest.mark.parametrize("method,path,perm,mutating", ENDPOINTS)
def test_wrong_permission_is_403(api_as, event, method, path, perm, mutating):
    c = api_as(user_id=7001, permissions=("vms.report.view",))
    assert call(c, method, path, event).status_code == 403


@pytest.mark.parametrize("method,path,perm,mutating",
                         [e for e in ENDPOINTS if e[3]])
def test_permission_without_admin_role_is_403(api_as, event, method, path, perm, mutating):
    c = api_as(user_id=7002, permissions=(perm,))
    body = {"reason": "x", "name": "N", "valid_from": event.valid_from.isoformat(),
            "valid_until": event.valid_until.isoformat(),
            "file": SimpleUploadedFile("a.csv", csv_rows(1).encode())}
    assert call(c, method, path, event, body).status_code == 403


@pytest.mark.parametrize("method,path,perm,mutating", [
    e for e in ENDPOINTS if "{e}" in e[1]])
def test_unknown_event_is_404(api_as, admin, event, method, path, perm, mutating):
    c = api_as(user_id=ADMIN_ID, permissions=(perm, "vms.pass.terminate"))
    missing = type("E", (), {"pk": 987654})()
    body = {"reason": "x", "file": SimpleUploadedFile("a.csv", b"x")}
    assert call(c, method, path, missing, body).status_code == 404


def test_organizer_cannot_call_api(api_as, event):
    """An organiser is data, not an actor: no VMS permission, no access (C-01)."""
    c = api_as(user_id=7003, permissions=(), kind="visitor")
    assert call(c, "post", "events/{e}/attendees/upload", event).status_code == 403
    assert call(c, "get", "events", event).status_code == 403


def test_event_crud(api_as, admin, gate, window):
    c = api_as(user_id=ADMIN_ID, permissions=("vms.event.manage",))
    body = {"name": "Seminar", "organizer": "ECE", "valid_from": window[0].isoformat(),
            "valid_until": window[1].isoformat(), "zone_ids": [gate.zone_id],
            "fast_lane": True, "walkin_rate_limit": 5}
    r = c.post(BASE + "events", body, format="json")
    assert r.status_code == 201 and r.data["zone_ids"] == [gate.zone_id]
    eid = r.data["id"]
    assert c.get(BASE + f"events/{eid}").data["name"] == "Seminar"
    r = c.patch(BASE + f"events/{eid}", {"walkin_rate_limit": 9}, format="json")
    assert r.status_code == 200 and r.data["walkin_rate_limit"] == 9
    assert [e["id"] for e in c.get(BASE + "events").data] == [eid]
    bad = c.post(BASE + "events", {**body, "valid_until": window[0].isoformat()},
                 format="json")
    assert bad.status_code == 400


def test_upload_approve_attendees_endpoints(api_as, admin, event):
    c = api_as(user_id=ADMIN_ID, permissions=("vms.event.manage", "vms.pass.terminate"))
    text = csv_rows(2) + "Dup,9123456789,,passport,A000000,,\n"
    r = c.post(BASE + f"events/{event.pk}/attendees/upload",
               {"file": SimpleUploadedFile("list.csv", text.encode(), "text/csv")},
               format="multipart")
    assert r.status_code == 201
    assert (r.data["accepted_count"], r.data["rejected_count"]) == (2, 1)
    assert r.data["rejected"][0]["row"] == 4
    assert len(c.get(BASE + f"events/{event.pk}/attendees").data) == 2
    r = c.post(BASE + f"events/{event.pk}/approve", {}, format="json")
    assert r.status_code == 200 and r.data["issued"] == 2
    att = EventAttendee.objects.filter(batch=event).first()
    assert c.get(BASE + f"events/{event.pk}/attendees?status=pass_issued").data[0]["pass_id"]
    assert c.delete(BASE + f"events/{event.pk}/attendees/{att.pk}", {},
                    format="json").status_code == 400            # reason required
    r = c.delete(BASE + f"events/{event.pk}/attendees/{att.pk}", {"reason": "Withdrew"},
                 format="json")
    assert r.status_code == 200 and r.data["status"] == "cancelled"
    assert c.post(BASE + f"events/{event.pk}/cancel", {"reason": "Storm"},
                  format="json").data["status"] == "cancelled"


def test_upload_without_file_is_400_and_unparseable_is_400(api_as, admin, event):
    c = api_as(user_id=ADMIN_ID, permissions=("vms.event.manage",))
    url = BASE + f"events/{event.pk}/attendees/upload"
    assert c.post(url, {}, format="multipart").status_code == 400
    r = c.post(url, {"file": SimpleUploadedFile("a.csv", b"nope\n1\n")}, format="multipart")
    assert r.status_code == 400 and r.data["error"]["code"] == "missing_columns"


def test_attendance_and_throughput_endpoints(api_as, admin, event):
    svc.upload_attendees(admin_actor=admin, event_id=event.pk, file=csv_rows(2).encode())
    svc.approve_batch(admin_actor=admin, event_id=event.pk)
    for vp in VisitPass.objects.filter(event=event):
        f.make_visit_log(visit_pass=vp)
    mon = api_as(user_id=7004, permissions=("vms.monitor.view",))
    a = mon.get(BASE + f"events/{event.pk}/attendance").data
    assert (a["invited"], a["checked_in"], a["current_inside"]) == (2, 2, 2)
    t = mon.get(BASE + f"events/{event.pk}/throughput?bucket_minutes=10")
    assert t.status_code == 200 and sum(r["check_ins"] for r in t.data) == 2
    assert mon.get(BASE + f"events/{event.pk}/throughput?bucket_minutes=0").status_code == 400


def test_fast_lane_manifest_needs_gate_sync_and_flag(api_as, admin, event):
    svc.upload_attendees(admin_actor=admin, event_id=event.pk, file=csv_rows(2).encode())
    svc.approve_batch(admin_actor=admin, event_id=event.pk)
    c = api_as(user_id=7005, permissions=("vms.gate.sync",))
    r = c.get(BASE + f"events/{event.pk}/fast-lane-manifest")
    assert r.status_code == 200 and len(r.data["passes"]) == 2
    assert {p["qr_token"] for p in r.data["passes"]} == set(
        VisitPass.objects.filter(event=event).values_list("qr_token", flat=True))
    svc.update_event(admin_actor=admin, event_id=event.pk, fast_lane=False)
    assert c.get(BASE + f"events/{event.pk}/fast-lane-manifest").status_code == 409


def test_event_window_in_past_not_creatable_via_api(api_as, admin):
    c = api_as(user_id=ADMIN_ID, permissions=("vms.event.manage",))
    now = timezone.now()
    r = c.post(BASE + "events", {"name": "Old", "valid_from": (now - timedelta(days=2)).isoformat(),
                                 "valid_until": (now - timedelta(days=1)).isoformat()},
               format="json")
    assert r.status_code == 400 and r.data["error"]["code"] == "window_in_past"
