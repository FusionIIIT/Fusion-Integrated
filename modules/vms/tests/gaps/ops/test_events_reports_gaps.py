"""Ops gaps: bulk events and reports."""
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from modules.vms.models import (
    AuditLog,
    EventAttendee,
    EventBatch,
    Notification,
    VisitPass,
    VisitRequest,
)
from modules.vms.services import bulk_events as svc
from modules.vms.services import reports
from modules.vms.tests import factories as f
from modules.vms.tests.gaps.ops.conftest import ADMIN, SEC, csv_rows

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("policy")]

BASE = "/api/v1/vms/"
VIEW, EXPORT, PII = "vms.report.view", "vms.report.export", "vms.report.view_pii"


def _walkin(event, n=1):
    for _ in range(n):
        f.make_visit_request(event=event, source="walk_in", status="awaiting_admin")


def test_uc_009_event_overflow_control_blocks_after_capacity(event):
    """VMS-UC-009: the hourly walk-in cap closes the overflow lane, then the hour rolls."""
    EventBatch.objects.filter(pk=event.pk).update(status="active")
    assert svc.walkin_allowance(event.pk)["allowed"] is True
    _walkin(event, 2)
    a = svc.walkin_allowance(event.pk)
    assert (a["used"], a["remaining"], a["allowed"]) == (2, 0, False)
    VisitRequest.objects.filter(event=event).update(
        created_at=timezone.now() - timedelta(hours=2))
    assert svc.walkin_allowance(event.pk)["allowed"] is True


def test_uc_009_event_fast_lane_flag_toggle_audited(ev_admin, event):
    """VMS-UC-009: toggling fast_lane is audited with the changed field."""
    svc.update_event(admin_actor=ev_admin, event_id=event.pk, fast_lane=False)
    event.refresh_from_db()
    assert event.fast_lane is False
    log = AuditLog.objects.filter(action="vms.event.updated", entity_id=str(event.pk)).get()
    assert "fast_lane" in log.detail["changed"] and log.actor_user_id == ADMIN


def test_uc_008_bulk_upload_non_admin_forbidden_and_audit(api_as, event):
    """VMS-UC-008: a guard cannot upload; nothing is staged or audited."""
    c = api_as(user_id=SEC, permissions=("vms.gate.operate",))
    r = c.post(BASE + f"events/{event.pk}/attendees/upload",
               {"file": SimpleUploadedFile("l.csv", csv_rows(2).encode())}, format="multipart")
    assert r.status_code == 403
    assert not EventAttendee.objects.filter(batch=event).exists()
    assert not AuditLog.objects.filter(action="vms.event.attendees_uploaded").exists()
    with pytest.raises(PermissionDeniedError):
        svc.upload_attendees(admin_actor=f.make_actor(permissions=("vms.event.manage",),
                                                      user_id=SEC),
                             event_id=event.pk, rows=[{"name": "x"}])


def test_uc_008_bulk_approve_notifies_attendees(ev_admin, event):
    """VMS-UC-008: each approved attendee gets a pass.issued notice."""
    rep = svc.upload_attendees(admin_actor=ev_admin, event_id=event.pk,
                               file=csv_rows(3).encode())
    assert len(rep.accepted) == 3
    out = svc.approve_batch(admin_actor=ev_admin, event_id=event.pk)
    assert out["issued"] == 3
    rows = Notification.objects.filter(topic="pass.issued")
    assert len({r.recipient_visitor_id for r in rows}) == 3 and None not in {
        r.recipient_visitor_id for r in rows}
    total = rows.count()
    again = svc.approve_batch(admin_actor=ev_admin, event_id=event.pk)
    assert (again["issued"], again["skipped"]) == (0, 3)
    assert Notification.objects.filter(topic="pass.issued").count() == total


def test_bw_21_event_attendee_checkout_completed(api_as, ev_admin, guard, gate, event):
    """BW-VMS-21: check-out of an event attendee completes the visit request (transition 4)."""
    svc.upload_attendees(admin_actor=ev_admin, event_id=event.pk, file=csv_rows(1).encode())
    svc.approve_batch(admin_actor=ev_admin, event_id=event.pk)
    vp = VisitPass.objects.get(event=event)
    g = api_as(user_id=SEC, permissions=("vms.gate.operate", "vms.gate.sync"))
    assert g.post(BASE + "gate/validate", {"qr_token": vp.qr_token, "gate_id": gate.pk},
                  format="json").status_code == 200
    g = api_as(user_id=SEC, permissions=("vms.gate.operate", "vms.gate.sync"))
    assert g.post(BASE + "visit/check-out", {"credential": vp.qr_token},
                  format="json").status_code == 200
    vp.visit_request.refresh_from_db()
    assert vp.visit_request.status == "completed"
    again = api_as(user_id=SEC, permissions=("vms.gate.operate",)).post(
        BASE + "visit/check-out", {"credential": vp.qr_token}, format="json")
    assert again.status_code == 400


def test_cw_07_walkin_allowance_then_cancel_event_terminates_all(ev_admin, event):
    """CW-VMS-07: walk-in lane within cap, then cancelling terminates every event pass."""
    svc.upload_attendees(admin_actor=ev_admin, event_id=event.pk, file=csv_rows(3).encode())
    svc.approve_batch(admin_actor=ev_admin, event_id=event.pk)
    EventBatch.objects.filter(pk=event.pk).update(status="active")
    _walkin(event, 1)
    a = svc.walkin_allowance(event.pk)
    assert (a["event_active"], a["remaining"], a["allowed"]) == (True, 1, True)
    out = svc.cancel_event(admin_actor=ev_admin, event_id=event.pk, reason="Storm")
    assert out["passes_terminated"] == 3 and out["status"] == "cancelled"
    assert not VisitPass.objects.filter(event=event, is_active=True).exists()
    assert VisitPass.objects.filter(event=event, terminated_at__isnull=False).count() == 3
    assert EventAttendee.objects.filter(batch=event, status="cancelled").count() == 3
    assert svc.walkin_allowance(event.pk)["allowed"] is False
    with pytest.raises(Exception) as e:
        svc.cancel_event(admin_actor=ev_admin, event_id=event.pk, reason="again")
    assert e.value.code == "already_cancelled"
    assert EventBatch.objects.get(pk=event.pk).status == "cancelled"


def test_cw_07_upload_approve_gate_zone_checkout(api_as, ev_admin, guard, gate, event):
    """CW-VMS-07: upload -> approve -> gate entry -> exit through the HTTP endpoints."""
    admin_c = api_as(user_id=ADMIN, permissions=("vms.event.manage",))
    r = admin_c.post(BASE + f"events/{event.pk}/attendees/upload",
                     {"file": SimpleUploadedFile("l.csv", csv_rows(2).encode())},
                     format="multipart")
    assert r.data["accepted_count"] == 2
    admin_c = api_as(user_id=ADMIN, permissions=("vms.event.manage",))
    assert admin_c.post(BASE + f"events/{event.pk}/approve", {}, format="json").data["issued"] == 2
    vps = list(VisitPass.objects.filter(event=event))
    assert all(vp.fast_lane and vp.valid_until == event.valid_until for vp in vps)
    assert {z.pk for z in vps[0].visit_request.requested_zones.all()} == {gate.zone_id}
    g = api_as(user_id=SEC, permissions=("vms.gate.operate", "vms.gate.sync"))
    assert g.post(BASE + "gate/validate", {"qr_token": vps[0].qr_token, "gate_id": gate.pk},
                  format="json").status_code == 200
    g = api_as(user_id=SEC, permissions=("vms.gate.operate",))
    assert g.post(BASE + "visit/check-out", {"credential": vps[0].qr_token},
                  format="json").status_code == 200
    att = api_as(user_id=ADMIN, permissions=("vms.event.manage",)).get(
        BASE + f"events/{event.pk}/attendance").data
    assert att["checked_in"] == 1 and att["current_inside"] == 0


# --- reports ---------------------------------------------------------------------------

@pytest.fixture
def reporter():
    return f.make_actor(permissions=[VIEW, EXPORT], user_id=4000)


def test_uc_007_report_pdf_export_supported_or_explicitly_rejected_per_srs(reporter):
    """VMS-UC-007: pdf is explicitly rejected (501) and nothing is audited; bad fmt is 400."""
    with pytest.raises(reports.NotImplementedFormat) as e:
        reports.export(reporter, "daily_summary", {}, fmt="pdf")
    assert e.value.code == "pdf_backend_unavailable" and e.value.status_code == 501
    with pytest.raises(BadRequestError):
        reports.export(reporter, "daily_summary", {}, fmt="xlsx")
    assert not AuditLog.objects.filter(action=reports.ACT_EXPORT).exists()


def test_uc_007_report_audit_row_written_per_pii_run():
    """VMS-UC-007: an un-masked run is audited per run; a masked run is not."""
    actor = f.make_actor(permissions=[VIEW, EXPORT, PII], user_id=4002)
    reports.run(actor, "audit_trail", {"anonymize": "false"})
    reports.run(actor, "audit_trail", {"anonymize": "false"})
    reports.run(actor, "audit_trail", {})
    assert AuditLog.objects.filter(action=reports.ACT_PII_VIEW).count() == 2
    reports.export(actor, "audit_trail", {"anonymize": "false"})
    assert AuditLog.objects.filter(action=reports.ACT_EXPORT).count() == 1
    assert AuditLog.objects.filter(action=reports.ACT_PII_VIEW).count() == 3


def test_uc_007_masked_actor_cannot_run_unmasked(reporter):
    """VMS-UC-007: view_pii is required to switch masking off, and nothing is audited."""
    from core.api.exceptions import PermissionDeniedError
    with pytest.raises(PermissionDeniedError):
        reports.run(reporter, "audit_trail", {"anonymize": "false"})
    assert not AuditLog.objects.filter(action=reports.ACT_PII_VIEW).exists()


def test_uc_007_report_empty_range_returns_zero_rows(reporter):
    """VMS-UC-007: an empty range gives an empty, well-formed result."""
    res = reports.run(reporter, "daily_summary", {"date": "2020-01-01"})
    assert all(v == 0 for v in res["summary"].values())
    vol = reports.run(reporter, "frequent_visitors", {"start": "2020-01-01", "end": "2020-01-02"})
    assert vol["rows"] == []
    out = reports.export(reporter, "frequent_visitors",
                         {"start": "2020-01-01", "end": "2020-01-02"})
    assert out["row_count"] == 0 and list(out["rows"]) == []


def test_uc_007_report_admin_zone_scope_excludes_other_zone_events(db):
    """VMS-UC-007: a zone-scoped admin sees only own-zone activity in zone reports."""
    from modules.vms.models import RoleAssignment
    z1, z2 = f.make_zone(name="Z1"), f.make_zone(name="Z2")
    f.make_role_assignment(user_id=4001, role="admin", scope_type=RoleAssignment.ScopeType.ZONE,
                           scope_id=z1.pk)
    vp = f.make_visit_pass()
    for z, n in ((z1, 1), (z2, 2)):
        for _ in range(n):
            f.make_visit_log(visit_pass=vp, event="zone_allowed", zone=z)
    zone_admin = f.make_actor(permissions=[VIEW, EXPORT], user_id=4001)
    campus = f.make_actor(permissions=[VIEW], user_id=4000)
    day = timezone.localdate().isoformat()
    scoped = reports.run(zone_admin, "zone_access", {"start": day, "end": day})
    assert [(r["zone"], r["allowed"]) for r in scoped["rows"]] == [("Z1", 1)]
    full = reports.run(campus, "zone_access", {"start": day, "end": day})
    assert {(r["zone"], r["allowed"]) for r in full["rows"]} == {("Z1", 1), ("Z2", 2)}
    with pytest.raises(NotFoundError):
        reports.run(zone_admin, "zone_access", {"start": day, "end": day, "zone": z2.pk})
