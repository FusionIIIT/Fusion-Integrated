"""BW-VMS-21 / CW-VMS-07: upload -> approve -> gate entry inside and outside the event window."""
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from freezegun import freeze_time

from modules.vms.models import EventAttendee, VisitLog, VisitPass
from modules.vms.services import bulk_events as svc
from modules.vms.services import gate as gate_svc
from modules.vms.tests.g_events.conftest import ADMIN_ID, SEC_ID, csv_rows

pytestmark = pytest.mark.django_db

BASE = "/api/v1/vms/"


def test_bw_vms_21_bulk_event_entry(api_as, admin, sec, gate, event):
    c = api_as(user_id=ADMIN_ID, permissions=("vms.event.manage",))
    # R1 Event Visitor List Draft -> Event Passes Active (BR-211)
    r = c.post(BASE + f"events/{event.pk}/attendees/upload",
               {"file": SimpleUploadedFile("l.csv", csv_rows(3).encode())}, format="multipart")
    assert r.data["accepted_count"] == 3
    assert c.post(BASE + f"events/{event.pk}/approve", {}, format="json").data["issued"] == 3
    # R2 fast-lane controls visible to security
    guard = api_as(user_id=SEC_ID, permissions=("vms.gate.operate", "vms.gate.sync"))
    tokens = [p["qr_token"] for p in
              guard.get(BASE + f"events/{event.pk}/fast-lane-manifest").data["passes"]]
    assert len(tokens) == 3
    # R3 validation inside the window (BR-077, BR-190) through the public gate endpoint
    ok = guard.post(BASE + "gate/validate", {"qr_token": tokens[0], "gate_id": gate.pk},
                    format="json")
    assert ok.status_code == 200
    # R4 check-out (BR-105)
    out = guard.post(BASE + "visit/check-out", {"credential": tokens[0]}, format="json")
    assert out.status_code == 200
    att = api_as(user_id=ADMIN_ID, permissions=("vms.event.manage",)).get(
        BASE + f"events/{event.pk}/attendance")
    assert att.status_code == 200 and att.data["checked_in"] == 1 and att.data["current_inside"] == 0
    # outside the window: the event is over
    guard = api_as(user_id=SEC_ID, permissions=("vms.gate.operate", "vms.gate.sync"))
    with freeze_time(event.valid_until + timedelta(hours=1)):
        late = guard.post(BASE + "gate/validate", {"qr_token": tokens[1], "gate_id": gate.pk},
                          format="json")
    assert late.status_code == 403
    assert "outside_validity" in {x["code"] for x in late.data["failures"]}
    # before the window opens
    with freeze_time(event.valid_from - timedelta(hours=1)):
        early = guard.post(BASE + "gate/validate", {"qr_token": tokens[2], "gate_id": gate.pk},
                           format="json")
    assert early.status_code == 403


def test_event_pass_valid_only_in_event_window(admin, sec, gate):
    now = timezone.now()
    ev = svc.create_event(admin_actor=admin, name="Later", valid_from=now + timedelta(hours=2),
                          valid_until=now + timedelta(hours=5))
    svc.upload_attendees(admin_actor=admin, event_id=ev.pk, file=csv_rows(1).encode())
    svc.approve_batch(admin_actor=admin, event_id=ev.pk)
    token = VisitPass.objects.get(event=ev).qr_token
    res = gate_svc.validate_and_check_in(security_actor=sec, credential={"qr_token": token},
                                         gate_id=gate.pk)
    assert res.outcome == gate_svc.DENIED
    assert [x.code for x in res.failures] == ["outside_validity"]
    with freeze_time(now + timedelta(hours=3)):
        res = gate_svc.validate_and_check_in(
            security_actor=sec, credential={"qr_token": token}, gate_id=gate.pk)
    assert res.outcome == gate_svc.CHECKED_IN


def test_assigned_slot_enforced_at_gate(admin, sec, gate, window):
    a = window[0] + timedelta(hours=3)
    ev = svc.create_event(admin_actor=admin, name="Slotted", valid_from=window[0],
                          valid_until=window[1],
                          slots=[{"start": a, "end": a + timedelta(hours=1), "capacity": 5}])
    svc.upload_attendees(admin_actor=admin, event_id=ev.pk, file=csv_rows(1).encode())
    svc.approve_batch(admin_actor=admin, event_id=ev.pk)
    token = VisitPass.objects.get(event=ev).qr_token
    res = gate_svc.validate_and_check_in(security_actor=sec, credential={"qr_token": token},
                                         gate_id=gate.pk)
    assert [x.code for x in res.failures] == ["outside_slot"]
    with freeze_time(a + timedelta(minutes=10)):
        res = gate_svc.validate_and_check_in(
            security_actor=sec, credential={"qr_token": token}, gate_id=gate.pk)
    assert res.outcome == gate_svc.CHECKED_IN


def test_revoked_attendee_denied_at_gate(admin, sec, gate, event):
    svc.upload_attendees(admin_actor=admin, event_id=event.pk, file=csv_rows(1).encode())
    svc.approve_batch(admin_actor=admin, event_id=event.pk)
    att = EventAttendee.objects.get(batch=event)
    svc.revoke_attendee(admin_actor=admin, event_id=event.pk, attendee_id=att.pk, reason="No")
    res = gate_svc.validate_and_check_in(
        security_actor=sec, credential={"qr_token": att.visit_pass.qr_token}, gate_id=gate.pk)
    assert res.outcome == gate_svc.DENIED


def test_1000_row_upload_approve_and_gate(admin, sec, gate, event):
    rep = svc.upload_attendees(admin_actor=admin, event_id=event.pk,
                               file=csv_rows(1000).encode())
    assert len(rep.accepted) == 1000 and not rep.rejected
    out = svc.approve_batch(admin_actor=admin, event_id=event.pk)
    assert out["issued"] == 1000 and not out["failed"]
    tokens = list(VisitPass.objects.filter(event=event).order_by("pk")
                  .values_list("qr_token", flat=True))
    assert len(set(tokens)) == 1000
    for token in tokens[::100] + tokens[-1:]:        # sampled gate walk-through
        res = gate_svc.validate_and_check_in(
            security_actor=sec, credential={"qr_token": token}, gate_id=gate.pk)
        assert res.outcome == gate_svc.CHECKED_IN
    with freeze_time(event.valid_until + timedelta(minutes=5)):
        res = gate_svc.validate_and_check_in(
            security_actor=sec, credential={"qr_token": tokens[5]}, gate_id=gate.pk)
    assert res.outcome == gate_svc.DENIED
    assert VisitLog.objects.filter(event="check_in", visit_pass__event=event).count() == 11
