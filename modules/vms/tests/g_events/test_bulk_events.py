"""Service-level tests for lane G (UC-008, UC-009, CFR-009)."""
import time
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.models import (
    Alert,
    AuditLog,
    EventAttendee,
    EventBatch,
    Notification,
    VisitLog,
    VisitPass,
    VisitRequest,
)
from modules.vms.selectors import events as sel
from modules.vms.services import bulk_events as svc
from modules.vms.tests import factories as f
from modules.vms.tests.g_events.conftest import HEADER, blacklist_doc, csv_rows

pytestmark = pytest.mark.django_db


def upload(admin, event, text):
    return svc.upload_attendees(admin_actor=admin, event_id=event.pk, file=text.encode())


# --- events ----------------------------------------------------------------------------

def test_create_event_audited_and_active_window(admin, event):
    assert event.status == EventBatch.Status.DRAFT
    assert AuditLog.objects.filter(action="vms.event.created", entity_id=str(event.pk)).exists()


def test_restricted_zone_needs_explicit_listing(admin, window):
    z = f.make_zone(is_restricted=True)
    kw = {"admin_actor": admin, "name": "E", "valid_from": window[0], "valid_until": window[1],
          "zone_ids": [z.pk]}
    with pytest.raises(BadRequestError) as e:
        svc.create_event(**kw)
    assert e.value.code == "restricted_zone_not_confirmed"
    ev = svc.create_event(**kw, allow_restricted_zones=[z.pk])
    assert list(ev.zones.all()) == [z]


@pytest.mark.parametrize("delta,code", [(timedelta(days=40), "window_too_long"),
                                        (timedelta(hours=-3), "invalid_window")])
def test_window_limits(admin, window, delta, code):
    with pytest.raises(BadRequestError) as e:
        svc.create_event(admin_actor=admin, name="E", valid_from=window[0],
                         valid_until=window[0] + delta)
    assert e.value.code == code


def test_slots_must_lie_in_window(admin, window):
    bad = [{"start": window[0] - timedelta(hours=2), "end": window[0], "capacity": 5}]
    with pytest.raises(BadRequestError):
        svc.create_event(admin_actor=admin, name="E", valid_from=window[0],
                         valid_until=window[1], slots=bad)


def test_only_admin_can_manage(event, window):
    no_perm = f.make_actor("staff", permissions=(), user_id=9001)
    no_role = f.make_actor("staff", permissions=("vms.event.manage",), user_id=9002)
    for actor in (no_perm, no_role):
        with pytest.raises(PermissionDeniedError):
            svc.create_event(admin_actor=actor, name="E", valid_from=window[0],
                             valid_until=window[1])
        with pytest.raises(PermissionDeniedError):
            upload(actor, event, csv_rows(1))
        with pytest.raises(PermissionDeniedError):
            svc.approve_batch(admin_actor=actor, event_id=event.pk)


def test_update_blocked_once_passes_exist(admin, event):
    svc.update_event(admin_actor=admin, event_id=event.pk, fast_lane=False)
    upload(admin, event, csv_rows(1))
    svc.approve_batch(admin_actor=admin, event_id=event.pk)
    with pytest.raises(ConflictError):
        svc.update_event(admin_actor=admin, event_id=event.pk, zone_ids=[])
    assert svc.update_event(admin_actor=admin, event_id=event.pk,
                            walkin_rate_limit=9).walkin_rate_limit == 9


# --- upload ----------------------------------------------------------------------------

def test_upload_reports_row_errors(admin, event):
    text = HEADER + (
        "Good One,9123456780,good@example.com,passport,GOOD0001,,\n"
        ",9123456781,x@example.com,passport,NONAME01,,\n"
        "No Contact,,,passport,NOCONT01,,\n"
        "Bad Doc,9123456782,,visa,BADDOC01,,\n"
        "Bad Number,9123456783,,passport,!!,,\n"
        "Bad Phone,12,,passport,BADPHN01,,\n"
        "Bad Mail,,not-an-email,passport,BADMAIL1,,\n")
    rep = upload(admin, event, text)
    assert rep.total == 7 and len(rep.accepted) == 1
    assert {r["row"] for r in rep.rejected} == {3, 4, 5, 6, 7, 8}
    assert all(r["reason"] and r["code"] for r in rep.rejected)
    assert EventAttendee.objects.filter(batch=event).count() == 1


def test_upload_blacklisted_row_rejected(admin, event):
    blacklist_doc("BAD000001")
    rep = upload(admin, event, HEADER + (
        "Banned,9123456780,,passport,BAD000001,,\nFine,9123456781,,passport,FINE0001,,\n"))
    assert [r["code"] for r in rep.rejected] == ["blacklisted"]
    assert len(rep.accepted) == 1
    assert Alert.objects.filter(kind=Alert.Kind.BLACKLIST_HIT).count() == 1
    assert not EventAttendee.objects.filter(id_doc_number="BAD000001").exists()


def test_upload_duplicates_flagged(admin, event):
    text = HEADER + ("A,9123456780,,passport,DUPE0001,,\n"
                     "B,9123456781,,passport,dupe0001,,\nC,9123456782,,passport,OTHER001,,\n")
    rep = upload(admin, event, text)
    assert [(r["row"], r["code"]) for r in rep.rejected] == [(3, "duplicate")]
    again = upload(admin, event, text)            # across uploads
    assert len(again.accepted) == 0 and len(again.rejected) == 3


def test_unparseable_or_incomplete_list_rejected_whole(admin, event):
    with pytest.raises(BadRequestError) as e:
        upload(admin, event, "foo,bar\n1,2\n")
    assert e.value.code == "missing_columns"
    with pytest.raises(BadRequestError):
        svc.upload_attendees(admin_actor=admin, event_id=event.pk, file=b"\xff\xfe\x00bad")
    with pytest.raises(BadRequestError) as e:
        upload(admin, event, HEADER)
    assert e.value.code == "empty_list"
    assert EventAttendee.objects.count() == 0


def test_upload_over_row_limit_rejected(admin, event):
    rows = [{"name": "x"}] * (svc.MAX_ROWS + 1)
    with pytest.raises(BadRequestError) as e:
        svc.upload_attendees(admin_actor=admin, event_id=event.pk, rows=rows)
    assert e.value.code == "too_many_rows"


def test_upload_on_cancelled_event_conflicts(admin, event):
    svc.cancel_event(admin_actor=admin, event_id=event.pk, reason="called off")
    with pytest.raises(ConflictError):
        upload(admin, event, csv_rows(1))


def test_slot_assigned_from_capacity(admin, window):
    a = window[0] + timedelta(hours=1)
    slots = [{"start": a, "end": a + timedelta(hours=1), "capacity": 2},
             {"start": a + timedelta(hours=1), "end": a + timedelta(hours=2), "capacity": 1}]
    ev = svc.create_event(admin_actor=admin, name="Slots", valid_from=window[0],
                          valid_until=window[1], slots=slots)
    rep = upload(admin, ev, csv_rows(4))
    assert len(rep.accepted) == 3 and rep.rejected[0]["code"] == "slots_full"
    starts = sorted(EventAttendee.objects.values_list("slot_start", flat=True))
    assert starts[0] == starts[1] == a and starts[2] == a + timedelta(hours=1)


def test_explicit_slot_outside_event_rejected(admin, event):
    far = (timezone.now() + timedelta(days=3)).isoformat()
    rep = upload(admin, event, HEADER + f"S,9123456780,,passport,SLOT0001,{far},{far}\n")
    assert rep.rejected[0]["code"] == "slot_outside_event"


@pytest.mark.parametrize("n", [5000])
def test_5000_row_upload_within_budget(admin, event, n):
    t0 = time.monotonic()
    rep = upload(admin, event, csv_rows(n))
    assert len(rep.accepted) == n and not rep.rejected
    assert time.monotonic() - t0 < 90


# --- approval --------------------------------------------------------------------------

def test_approve_issues_one_pass_each_with_slot_and_zones(admin, gate, window):
    a = window[0] + timedelta(hours=1)
    ev = svc.create_event(
        admin_actor=admin, name="E", valid_from=window[0], valid_until=window[1],
        zone_ids=[gate.zone_id], fast_lane=True,
        slots=[{"start": a, "end": a + timedelta(hours=1), "capacity": None}])
    upload(admin, ev, csv_rows(3))
    out = svc.approve_batch(admin_actor=admin, event_id=ev.pk)
    assert out["issued"] == 3 and not out["failed"]
    ev.refresh_from_db()
    assert ev.status == EventBatch.Status.ACTIVE
    for att in EventAttendee.objects.filter(batch=ev):
        vp = att.visit_pass
        assert att.status == EventAttendee.Status.PASS_ISSUED
        assert (vp.valid_from, vp.valid_until) == (ev.valid_from, ev.valid_until)
        assert vp.event_id == ev.pk and vp.fast_lane and vp.is_active
        assert list(vp.allowed_zones.all()) == [gate.zone]
        assert att.slot_start == a
        vr = vp.visit_request
        assert (vr.source, vr.status, vr.event_id) == ("bulk", "approved", ev.pk)
    assert VisitPass.objects.filter(event=ev).count() == 3
    assert Notification.objects.filter(topic="pass.issued").count() == 6   # inapp+email each
    assert AuditLog.objects.filter(action="vms.event.batch_approved").exists()


def test_approve_is_resumable(admin, event):
    upload(admin, event, csv_rows(4))
    first = list(EventAttendee.objects.filter(batch=event).values_list("pk", flat=True))[:2]
    one = svc.approve_batch(admin_actor=admin, event_id=event.pk, attendee_ids=first)
    assert one["issued"] == 2
    rest = svc.approve_batch(admin_actor=admin, event_id=event.pk)
    assert (rest["issued"], rest["skipped"]) == (2, 2)
    assert svc.approve_batch(admin_actor=admin, event_id=event.pk)["issued"] == 0
    assert VisitPass.objects.filter(event=event).count() == 4


def test_approve_skips_attendee_blacklisted_since_upload(admin, event):
    upload(admin, event, csv_rows(2))
    blacklist_doc("A000001")
    out = svc.approve_batch(admin_actor=admin, event_id=event.pk)
    assert out["issued"] == 1 and out["failed"][0]["code"] == "blacklisted"
    assert VisitPass.objects.filter(event=event).count() == 1


def test_approve_reuses_existing_visitor_record(admin, event):
    v = f.make_visitor(id_doc_type="passport", id_doc_number="A000000")
    upload(admin, event, csv_rows(1))
    svc.approve_batch(admin_actor=admin, event_id=event.pk)
    assert VisitRequest.objects.get(event=event).visitor_id == v.pk


def test_approve_closed_event_conflicts(admin, event):
    svc.cancel_event(admin_actor=admin, event_id=event.pk, reason="x")
    with pytest.raises(ConflictError):
        svc.approve_batch(admin_actor=admin, event_id=event.pk)


def test_event_pass_not_capped_to_max_visit_hours(admin, gate):
    now = timezone.now()
    ev = svc.create_event(admin_actor=admin, name="Multi-day", valid_from=now,
                          valid_until=now + timedelta(days=3))
    upload(admin, ev, csv_rows(1))
    svc.approve_batch(admin_actor=admin, event_id=ev.pk)
    assert VisitPass.objects.get(event=ev).valid_until == ev.valid_until


def test_unknown_event_is_404(admin):
    with pytest.raises(NotFoundError):
        svc.approve_batch(admin_actor=admin, event_id=99999)


# --- revoke / cancel -------------------------------------------------------------------

def test_revoke_attendee_terminates_pass(admin, event):
    upload(admin, event, csv_rows(1))
    svc.approve_batch(admin_actor=admin, event_id=event.pk)
    att = EventAttendee.objects.get(batch=event)
    with pytest.raises(BadRequestError):
        svc.revoke_attendee(admin_actor=admin, event_id=event.pk, attendee_id=att.pk, reason=" ")
    svc.revoke_attendee(admin_actor=admin, event_id=event.pk, attendee_id=att.pk,
                        reason="Withdrew")
    att.refresh_from_db()
    vp = att.visit_pass
    assert att.status == EventAttendee.Status.CANCELLED
    assert not vp.is_active and vp.terminated_at and vp.termination_reason == "Withdrew"
    with pytest.raises(ConflictError):
        svc.revoke_attendee(admin_actor=admin, event_id=event.pk, attendee_id=att.pk,
                            reason="again")


def test_revoke_staged_attendee_without_pass(admin, event):
    upload(admin, event, csv_rows(1))
    att = EventAttendee.objects.get(batch=event)
    svc.revoke_attendee(admin_actor=admin, event_id=event.pk, attendee_id=att.pk, reason="No")
    att.refresh_from_db()
    assert att.status == "cancelled" and att.visit_pass_id is None


def test_revoke_attendee_of_other_event_is_404(admin, event):
    other = f.make_event_attendee()
    with pytest.raises(NotFoundError):
        svc.revoke_attendee(admin_actor=admin, event_id=event.pk, attendee_id=other.pk,
                            reason="x")


def test_cancel_event_terminates_every_pass(admin, event):
    upload(admin, event, csv_rows(3))
    svc.approve_batch(admin_actor=admin, event_id=event.pk)
    out = svc.cancel_event(admin_actor=admin, event_id=event.pk, reason="Storm")
    assert out["passes_terminated"] == 3
    assert not VisitPass.objects.filter(event=event, is_active=True).exists()
    assert EventBatch.objects.get(pk=event.pk).status == "cancelled"
    with pytest.raises(ConflictError):
        svc.cancel_event(admin_actor=admin, event_id=event.pk, reason="Storm")


# --- walk-in lane ----------------------------------------------------------------------

def test_walkin_allowance_counts_event_walkins(admin, event):
    upload(admin, event, csv_rows(1))
    svc.approve_batch(admin_actor=admin, event_id=event.pk)     # activates the event
    assert svc.walkin_allowance(event.pk) == {
        "event_id": event.pk, "limit": 2, "used": 0, "remaining": 2, "event_active": True,
        "allowed": True}
    for _ in range(2):
        f.make_visit_request(event=event, source="walk_in", status="approved")
    a = svc.walkin_allowance(event.pk)
    assert (a["used"], a["remaining"], a["allowed"]) == (2, 0, False)
    later = svc.walkin_allowance(event.pk, now=timezone.now() + timedelta(hours=2))
    assert later["used"] == 0


def test_walkin_allowance_inactive_event_not_allowed(admin, event):
    assert svc.walkin_allowance(event.pk)["allowed"] is False      # still a draft


# --- selectors -------------------------------------------------------------------------

def test_attendance_counts(admin, event):
    upload(admin, event, csv_rows(5))
    svc.approve_batch(admin_actor=admin, event_id=event.pk)
    passes = list(VisitPass.objects.filter(event=event).order_by("pk"))
    for vp in passes[:3]:
        f.make_visit_log(visit_pass=vp, event=VisitLog.Event.CHECK_IN)
    f.make_visit_log(visit_pass=passes[0], event=VisitLog.Event.CHECK_OUT)
    svc.revoke_attendee(admin_actor=admin, event_id=event.pk,
                        attendee_id=EventAttendee.objects.filter(
                            visit_pass=passes[4]).get().pk, reason="gone")
    a = sel.attendance(event)
    assert (a["invited"], a["passes_issued"], a["checked_in"]) == (4, 4, 3)
    assert (a["current_inside"], a["not_arrived"], a["no_show"], a["cancelled"]) == (2, 1, 0, 1)
    after = sel.attendance(event, now=event.valid_until + timedelta(minutes=1))
    assert after["no_show"] == 1


def test_throughput_buckets(admin, event):
    upload(admin, event, csv_rows(3))
    svc.approve_batch(admin_actor=admin, event_id=event.pk)
    for vp in VisitPass.objects.filter(event=event):
        f.make_visit_log(visit_pass=vp, event=VisitLog.Event.CHECK_IN)
    f.make_visit_log(visit_pass=f.make_visit_pass(), event=VisitLog.Event.CHECK_IN)  # other
    rows = sel.throughput(event, 5)
    assert sum(r["check_ins"] for r in rows) == 3
    assert all(r["bucket_start"].minute % 5 == 0 for r in rows)


def test_fast_lane_manifest_lists_active_fast_lane_passes(admin, event):
    upload(admin, event, csv_rows(2))
    svc.approve_batch(admin_actor=admin, event_id=event.pk)
    vp = VisitPass.objects.filter(event=event).first()
    assert len(sel.fast_lane_manifest(event)) == 2
    VisitPass.objects.filter(pk=vp.pk).update(is_active=False)
    tokens = [m["qr_token"] for m in sel.fast_lane_manifest(event)]
    assert len(tokens) == 1 and vp.qr_token not in tokens
