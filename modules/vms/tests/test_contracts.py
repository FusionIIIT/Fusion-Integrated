"""vms's public contract for other modules (contracts.py): visit status and the hostel feed."""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.api.exceptions import BadRequestError
from modules.vms import contracts
from modules.vms.models import VisitLog
from modules.vms.services import integration
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db


def _admin():
    return f.make_actor(kind="staff", permissions=["vms.integration.manage"])


def _on_site(host_id, zone=None):
    vr = f.make_visit_request(status="approved", host_user_id=host_id)
    vp = f.make_visit_pass(visit_request=vr)
    f.make_visit_log(visit_pass=vp, event=VisitLog.Event.CHECK_IN, zone=zone or f.make_zone())
    return vp


# --- get_visit_status ---------------------------------------------------------------

def test_get_visit_status_returns_one_entry_per_requested_host_even_when_zero():
    out = contracts.get_visit_status([501, 502])
    assert set(out) == {501, 502}
    assert out[501] == contracts.VisitStatusDTO(501, 0, 0)


def test_get_visit_status_counts_pending_for_the_host_and_on_site_guests():
    f.make_visit_request(status="pending", host_user_id=501)
    f.make_visit_request(status="pending", host_user_id=501)
    f.make_visit_request(status="approved", host_user_id=501)        # not pending
    f.make_visit_request(status="awaiting_admin", host_user_id=501)  # waits for an Admin
    f.make_visit_request(status="pending", host_user_id=502)
    _on_site(501)
    _on_site(501)
    out = contracts.get_visit_status([501, 502, 503])
    assert (out[501].pending_requests, out[501].visitors_on_site) == (2, 2)
    assert (out[502].pending_requests, out[502].visitors_on_site) == (1, 0)
    assert out[503] == contracts.VisitStatusDTO(503, 0, 0)


def test_get_visit_status_a_visitor_who_left_is_not_counted():
    vp = _on_site(501)
    f.make_visit_log(visit_pass=vp, event=VisitLog.Event.CHECK_OUT)
    assert contracts.get_visit_status([501])[501].visitors_on_site == 0


def test_get_visit_status_empty_input_and_duplicates():
    assert contracts.get_visit_status([]) == {}
    assert set(contracts.get_visit_status([501, 501, 501])) == {501}


def test_get_visit_status_uses_a_constant_number_of_queries():
    for host in range(600, 610):
        f.make_visit_request(status="pending", host_user_id=host)
        _on_site(host)
    with CaptureQueriesContext(connection) as ctx:
        contracts.get_visit_status(list(range(600, 610)))
    assert len(ctx) <= 3


# --- hostel feed (AFR-225, UC-020 step 4) -----------------------------------------------

def _enable(zone_ids, enabled=True):
    integration.set_value(actor=_admin(), key="hostel_management", value={
        "enabled": enabled, "base_url": "https://hostel.example.test", "zone_ids": zone_ids})


def test_hostel_feed_is_empty_when_the_integration_was_never_configured():
    _on_site(501)
    assert contracts.get_hostel_visit_log() == []


def test_hostel_feed_is_empty_when_disabled_even_with_zones_listed():
    hostel = f.make_zone(name="Hostel A")
    _on_site(501, zone=hostel)
    _enable([hostel.pk], enabled=False)
    assert contracts.get_hostel_visit_log() == []


def test_hostel_feed_is_empty_when_enabled_without_any_scoped_zone():
    _on_site(501, zone=f.make_zone(name="Hostel A"))
    _enable([])
    assert contracts.get_hostel_visit_log() == []


def test_hostel_feed_returns_only_events_in_the_scoped_zones_and_no_contact_data():
    hostel, lobby = f.make_zone(name="Hostel A"), f.make_zone(name="Lobby")
    inside = _on_site(501, zone=hostel)
    _on_site(502, zone=lobby)
    _enable([hostel.pk])
    rows = contracts.get_hostel_visit_log()
    assert len(rows) == 1
    row = rows[0]
    assert (row.event, row.zone_id, row.zone_name, row.pass_id, row.host_user_id) == (
        "check_in", hostel.pk, "Hostel A", inside.pk, 501)
    assert row.visitor_name == inside.visit_request.visitor.full_name
    fields = set(contracts.HostelVisitLogDTO.__dataclass_fields__)
    assert not fields & {"phone", "email", "id_doc_number", "id_doc_type"}


def test_hostel_feed_pages_by_after_id_oldest_first():
    hostel = f.make_zone(name="Hostel A")
    vp = _on_site(501, zone=hostel)
    f.make_visit_log(visit_pass=vp, event=VisitLog.Event.CHECK_OUT, zone=hostel)
    f.make_visit_log(visit_pass=vp, event=VisitLog.Event.CHECK_IN, zone=hostel)
    _enable([hostel.pk])
    first = contracts.get_hostel_visit_log(limit=2)
    assert [r.log_id for r in first] == sorted(r.log_id for r in first) and len(first) == 2
    rest = contracts.get_hostel_visit_log(after_id=first[-1].log_id)
    assert len(rest) == 1 and rest[0].log_id > first[-1].log_id
    assert contracts.get_hostel_visit_log(after_id=rest[-1].log_id) == []


def test_hostel_feed_limit_is_clamped():
    hostel = f.make_zone(name="Hostel A")
    _on_site(501, zone=hostel)
    _enable([hostel.pk])
    assert len(contracts.get_hostel_visit_log(limit=0)) == 1
    assert len(contracts.get_hostel_visit_log(limit=10**6)) == 1


# --- the scope setting itself ----------------------------------------------------------

@pytest.mark.parametrize("bad", ["1", [True], ["x"], [10**9], [1.5]])
def test_hostel_zone_ids_must_be_a_list_of_existing_zone_ids(bad):
    with pytest.raises(BadRequestError):
        integration.set_value(actor=_admin(), key="hostel_management", value={
            "enabled": False, "zone_ids": bad})


def test_hostel_zone_ids_must_be_active_zones():
    zone = f.make_zone(name="Closed", is_active=False)
    with pytest.raises(BadRequestError):
        integration.set_value(actor=_admin(), key="hostel_management", value={
            "enabled": False, "zone_ids": [zone.pk]})


def test_hostel_zone_ids_are_deduplicated_sorted_and_audited_by_field_name():
    a, b = f.make_zone(name="H1"), f.make_zone(name="H2")
    out = integration.set_value(actor=_admin(), key="hostel_management", value={
        "enabled": False, "zone_ids": [b.pk, a.pk, b.pk]})
    assert out["value"]["zone_ids"] == sorted([a.pk, b.pk])
    from modules.vms.models import AuditLog
    log = AuditLog.objects.filter(action="vms.integration.updated").latest("id")
    assert "zone_ids" in log.detail["changed_fields"]
