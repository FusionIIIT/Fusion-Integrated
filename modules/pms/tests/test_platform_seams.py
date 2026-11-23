"""The scanner backends, the system checks, readiness, the contract and the reports."""
import os
import socket
from datetime import date, timedelta
from pathlib import Path

import pytest
from django.conf import settings as live_settings
from django.utils import timezone

from modules.pms import checks, registry
from modules.pms.contracts import get_patent_summaries
from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import (
    AuditEntry,
    Communication,
    Inventor,
    LicensingRequest,
    OfficeAction,
    ReferenceCounter,
)
from modules.pms.services import notifications, scanning
from modules.pms.tests.conftest import (
    ATTORNEY,
    DIRECTOR,
    approved_with_attorney,
    make_app,
    with_budget,
    with_cycle,
)


# -- scanning: BR-PMS-016 ------------------------------------------------------------
def _write(tmp_path, data):
    path = tmp_path / "f.pdf"
    path.write_bytes(data)
    return path


def test_development_scanner_runs_only_with_debug(settings, tmp_path):
    settings.PMS_MALWARE_SCANNER, settings.DEBUG = "development", True
    assert scanning.scan(_write(tmp_path, b"%PDF clean")) == "development"
    with pytest.raises(InvalidInput) as exc:
        scanning.scan(_write(tmp_path, b"%PDF " + scanning.EICAR))
    assert exc.value.code == "malware_found"
    assert scanning.ping() is None
    settings.DEBUG = False
    assert scanning.configured() is not None
    with pytest.raises(scanning.ScannerUnavailable):
        scanning.scan(_write(tmp_path, b"%PDF clean"))
    with pytest.raises(scanning.ScannerUnavailable):
        scanning._development(_write(tmp_path, b"%PDF clean"))


def test_unknown_backend_is_not_configured(settings):
    settings.PMS_MALWARE_SCANNER = "magic"
    assert "clamd" in scanning.configured()


def test_unreachable_clamd_refuses_and_readiness_says_so(settings, tmp_path):
    settings.PMS_MALWARE_SCANNER = "clamd"
    settings.PMS_CLAMD_SOCKET = str(tmp_path / "missing.sock")
    with pytest.raises(scanning.ScannerUnavailable):
        scanning.scan(_write(tmp_path, b"%PDF"))
    assert "not reachable" in scanning.ping()


def test_clamd_over_tcp_and_odd_replies(settings, tmp_path):
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(4)
    settings.PMS_MALWARE_SCANNER, settings.PMS_CLAMD_SOCKET = "clamd", ""
    settings.PMS_CLAMD_HOST, settings.PMS_CLAMD_PORT = "127.0.0.1", server.getsockname()[1]
    import threading

    def answer(reply):
        conn, _ = server.accept()
        with conn:
            conn.recv(65536)
            conn.sendall(reply)

    t = threading.Thread(target=answer, args=(b"stream: ERROR\0",))
    t.start()
    with pytest.raises(scanning.ScannerUnavailable):
        scanning.scan(_write(tmp_path, b"%PDF"))
    t.join()
    t = threading.Thread(target=answer, args=(b"NOPE\0",))
    t.start()
    assert scanning.ping() == "clamd did not answer PONG."
    t.join()
    server.close()


# -- checks and readiness --------------------------------------------------------------
def test_upload_root_inside_the_repo_is_an_error(settings):
    settings.PMS_UPLOAD_ROOT = str(Path(live_settings.BASE_DIR) / "uploads")
    assert [e.id for e in checks.check_upload_root(None)] == [checks.UPLOADS_IN_REPO]
    assert "inside the repository" in checks.upload_root_problem()


def test_world_readable_upload_root_warns(settings, tmp_path):
    root = tmp_path / "open"
    root.mkdir()
    os.chmod(root, 0o755)
    settings.PMS_UPLOAD_ROOT = str(root)
    assert [e.id for e in checks.check_upload_root(None)] == [checks.UPLOADS_WORLD_READABLE]
    assert "chmod 700" in checks.upload_root_problem()


def test_uncreatable_upload_root_is_reported(settings, tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir(mode=0o500)
    settings.PMS_UPLOAD_ROOT = str(locked / "sub")
    try:
        assert "cannot be created" in checks.upload_root_problem()
    finally:
        os.chmod(locked, 0o700)


def test_the_development_scanner_with_debug_off_fails_the_system_check(settings):
    settings.PMS_MALWARE_SCANNER, settings.DEBUG = "development", False
    assert [e.id for e in checks.check_scanner_backend(None)] == [
        checks.DEV_SCANNER_IN_PRODUCTION]
    settings.PMS_MALWARE_SCANNER = "magic"
    assert [e.id for e in checks.check_scanner_backend(None)] == [checks.UNKNOWN_SCANNER]
    settings.PMS_MALWARE_SCANNER = "clamd"
    assert checks.check_scanner_backend(None) == []


def test_readiness_lists_each_prerequisite_as_an_instruction(settings, tmp_path):
    settings.PMS_UPLOAD_ROOT = str(Path(live_settings.BASE_DIR) / "uploads")
    settings.PMS_MALWARE_SCANNER, settings.PMS_CLAMD_SOCKET = "clamd", ""
    settings.PMS_CLAMD_HOST = ""
    unmet = registry.readiness()
    assert len(unmet) == 2
    assert unmet[1].startswith("Malware scanner: ")


# -- contract ---------------------------------------------------------------------
@pytest.mark.django_db
def test_patent_summaries_count_filed_and_granted_only():
    filed = make_app(sm.FILED)
    make_app(sm.GRANTED, grant_date=date(2026, 1, 1), patent_number="P1")
    make_app(sm.UNDER_REVIEW)
    Inventor.objects.create(application=filed, user_id=1002, name="C", share_percent=1)
    out = get_patent_summaries([1001, 1002, 7777, None])
    assert (out[1001].filed, out[1001].granted) == (1, 1)
    assert (out[1002].filed, out[1002].granted) == (1, 0)
    assert (out[7777].filed, out[7777].granted) == (0, 0)
    assert get_patent_summaries([]) == {}


# -- models ------------------------------------------------------------------------
@pytest.mark.django_db
def test_model_labels():
    app = make_app(sm.SUBMITTED)
    assert str(app) == app.reference
    draft = make_app(sm.DRAFT)
    assert str(draft) == f"draft #{draft.pk}"
    assert str(ReferenceCounter(year=2026, last=3)) == "2026: 3"
    assert str(app.documents.get().versions.get()).endswith(" v1")


# -- reports: PMS-AFR-182..187, 237..239 ------------------------------------------------
# PMS-AFR-183 PMS-AFR-184 PMS-AFR-185 PMS-AFR-186 PMS-AFR-238 PMS-AFR-239
@pytest.mark.django_db
def test_every_report_type_renders_for_the_office(world):
    app = make_app(sm.UNDER_REVIEW)
    with_cycle(app, DIRECTOR)
    with_budget(approved_with_attorney(), status=sm.PROPOSED)
    comm = Communication.objects.create(application=app, kind="office_action",
                                        received_on=timezone.localdate(), reference="F",
                                        recorded_by_user_id=ATTORNEY)
    OfficeAction.objects.create(communication=comm, application=app,
                                response_due_on=timezone.localdate() + timedelta(9))
    AuditEntry.objects.create(action="application.submit", application=app,
                              from_state="draft", to_state="submitted")
    p = world["pcc"]
    for kind in ("status", "financial", "deadlines", "inventors", "portfolio", "workload",
                 "dashboard", "history", "trend"):
        r = p.get(f"reports/{kind}")
        assert r.status_code == 200, (kind, r.content)
    assert p.get("reports/history").json()["rows"][0]["submitted"] == 1
    assert p.get("reports/trend").json()["rows"][0]["change"] == ""
    assert p.get("reports/salary").status_code == 422
    assert p.get("reports/status", {"colour": "x"}).status_code == 400
    assert p.get("reports/status", {"columns": "nope"}).status_code == 422


# PMS-AFR-190
@pytest.mark.django_db
def test_report_filters_narrow_rows(world):
    make_app(sm.UNDER_REVIEW)
    make_app(sm.FILED, domain="software")
    p = world["pcc"]
    today = str(timezone.localdate())
    assert len(p.get("reports/status", {"status": "filed"}).json()["rows"]) == 1
    assert len(p.get("reports/status", {"domain_code": "software"}).json()["rows"]) == 1
    assert len(p.get("reports/status", {"date_from": today, "date_to": today}).json()[
        "rows"]) == 2
    assert p.get("reports/status", {"columns": "reference,title"}).json()["columns"] == [
        "reference", "title"]


@pytest.mark.django_db
def test_my_work_lists_each_lanes_items(world):
    a = make_app(sm.DRAFT)
    revise = make_app(sm.NEEDS_REVISION)
    comm = Communication.objects.create(application=revise, kind="office_action",
                                        received_on=timezone.localdate(), reference="F",
                                        recorded_by_user_id=ATTORNEY)
    OfficeAction.objects.create(communication=comm, application=revise,
                                status=sm.AWAITING_APPLICANT)
    kinds = {i["kind"] for i in world["applicant"].get("my-work").json()}
    assert kinds == {"draft", "revision", "office_action_approval"}
    reviewing = make_app(sm.ATTORNEY_ASSIGNED)
    with_cycle(reviewing, DIRECTOR, status="decided", decision="approve")
    with_budget(reviewing, status=sm.PROPOSED)
    LicensingRequest.objects.create(application=reviewing, applicant_user_id=1001,
                                    kind="licensing", summary="s",
                                    routed_director_user_id=DIRECTOR, status="routed",
                                    route_kind="director")
    kinds = {i["kind"] for i in world["director"].get("my-work").json()}
    assert {"budget", "licensing"} <= kinds
    assert a.pk


@pytest.mark.django_db
def test_reference_data_and_deadlines_views(world):
    world["applicant"]._go()
    body = world["applicant"].get("reference-data").json()
    assert body["appeal_period_days"] == 30 and body["domains"][0]["code"] == "materials"


@pytest.mark.django_db
def test_failed_delivery_is_retried_then_parked(world, monkeypatch):
    world["applicant"]._go()
    notifications.enqueue(topic="t", dedupe_key="x1", recipient_user_id=1001, subject="s",
                          body="b")
    notifications.enqueue(topic="t", dedupe_key="x2", recipient_user_id=4242, subject="s",
                          body="b")
    assert notifications.enqueue(topic="t", dedupe_key="x1", recipient_user_id=1001,
                                 subject="s", body="b") is None
    assert notifications.enqueue(topic="t", dedupe_key="x3", recipient_user_id=None,
                                 subject="s", body="b") is None

    def boom(**kw):
        raise OSError("smtp down")

    monkeypatch.setattr(notifications, "send_mail", boom)
    report = notifications.deliver_pending()
    assert report.failed == 2
    from modules.pms.models import Notification

    assert Notification.objects.get(dedupe_key="x2").status == "failed"
    assert Notification.objects.get(dedupe_key="x1").status == "pending"
    assert notifications.deliver_pending().deferred + notifications.deliver_pending().sent == 0


@pytest.mark.django_db
def test_people_search_returns_names_and_kinds_only(world):
    a = world["applicant"]
    assert a.get("people", {"q": "a"}).json() == {"results": []}
    rows = a.get("people", {"q": "Person"}).json()["results"]
    assert set(rows[0]) == {"user_id", "display_name", "kind"}
    assert a.get("people", {"q": "Person", "kind": "alien"}).status_code == 400


@pytest.mark.django_db
def test_people_search_says_when_the_directory_is_down(world, monkeypatch):
    from fusion_auth.client import IamUnavailable
    from modules.pms.selectors import people

    class Down:
        def search_users(self, **kw):
            raise IamUnavailable("down")

    world["applicant"]._go()
    monkeypatch.setattr(people, "get_client", Down)
    r = world["applicant"].client.get("/api/v1/pms/people", {"q": "Person"})
    assert r.json()["error"]["code"] == "directory_unavailable"
