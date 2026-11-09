"""Anonymisation (D-9), PII audit, CSV export, read-only guarantee, query budget, API auth."""
import csv
import io
import json

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext, override_settings

from core.api.exceptions import PermissionDeniedError
from modules.vms.models import AuditLog
from modules.vms.services import reports
from modules.vms.tests import factories as f
from modules.vms.tests.h_reports.conftest import D1, D2, D3, EXPORT, PII, VIEW

pytestmark = pytest.mark.django_db

BASE = "/api/v1/vms/reports"
MARCH = {"start": D1, "end": D3}
TWO_DAYS = {"start": D1, "end": D2}


# --- anonymisation -------------------------------------------------------------------

def test_anonymised_by_default(data, pii_reporter):
    res = reports.run(pii_reporter, "frequent_visitors", MARCH)   # holds PII perm, still masked
    assert res["anonymized"] is True
    top = res["rows"][0]
    assert top["visitor"] == reports.visitor_label(data.v[1].pk)
    assert top["visitor"].startswith("Visitor #") and len(top["visitor"]) == len("Visitor #") + 6
    assert top["phone"] == "*" * 8 + "11" and top["email"] == "***@corp.example"
    assert top["id_doc_number"] == "******11"
    blob = json.dumps(res)
    for v in data.v.values():
        assert v.full_name not in blob and v.id_doc_number not in blob
        assert v.phone not in blob and v.email not in blob
    assert "visitor_id" not in res["columns"] and "full_name" not in res["columns"]
    assert not AuditLog.objects.filter(action=reports.ACT_PII_VIEW).exists()


def test_masks():
    assert reports.mask_phone("9800000011") == "********11"
    assert reports.mask_email("a@b.org") == "***@b.org"
    assert reports.mask_id("PASS-111") == "******11"
    assert reports.mask_phone("") == reports.mask_email("") == reports.mask_id("") == ""


def test_hash_is_stable_keyed_and_not_the_plain_id(data):
    label = reports.visitor_label(7)
    assert label == reports.visitor_label(7) != reports.visitor_label(8)
    with override_settings(SECRET_KEY="another-secret-key-for-test-purposes-only-1234567890"):
        assert reports.visitor_label(7) != label


def test_pii_requires_permission_and_audits(data, reporter, pii_reporter):
    with pytest.raises(PermissionDeniedError):
        reports.run(reporter, "frequent_visitors", {**MARCH, "anonymize": "false"})
    assert not AuditLog.objects.filter(action=reports.ACT_PII_VIEW).exists()

    res = reports.run(pii_reporter, "frequent_visitors", {**MARCH, "anonymize": False})
    assert res["anonymized"] is False
    assert res["rows"][0]["visitor"] == "Person 1" and res["rows"][0]["visitor_id"]
    log = AuditLog.objects.get(action=reports.ACT_PII_VIEW)
    assert log.actor_user_id == pii_reporter.user_id
    assert log.entity_type == "report" and log.entity_id == "frequent_visitors"
    assert log.detail["params"]["anonymize"] is False and log.detail["rows"] == 3


def test_audit_trail_and_blacklist_names_only_with_pii(data, pii_reporter):
    anon = reports.run(pii_reporter, "audit_trail", {**TWO_DAYS, "visitor_id": data.v[5].pk})
    assert all(r["visitor"].startswith("Visitor #") for r in anon["rows"])
    assert all(r["justification"] == "" for r in anon["rows"])
    assert "VIP guest" not in json.dumps(anon)
    named = reports.run(pii_reporter, "audit_trail",
                        {**TWO_DAYS, "visitor_id": data.v[5].pk, "anonymize": "false"})
    assert {r["visitor"] for r in named["rows"]} == {"Person 5"}
    assert "VIP guest" in json.dumps(named)

    bl = reports.run(pii_reporter, "blacklist_hits", TWO_DAYS)
    assert "Mallory" not in json.dumps(bl) and not any(r["dimension"] == "hit"
                                                       for r in bl["rows"])
    bl = reports.run(pii_reporter, "blacklist_hits", {**TWO_DAYS, "anonymize": False})
    hits = {r["visitor"] for r in bl["rows"] if r["dimension"] == "hit"}
    assert hits == {"Mallory", "Trudy", ""}
    assert AuditLog.objects.filter(action=reports.ACT_PII_VIEW).count() == 2


# --- read-only & budget ----------------------------------------------------------------

ALL_KEYS = list(reports.CATALOGUE)


def _params(key):
    if key == "event_attendance":
        return {**MARCH, "event_id": f.make_event_batch().pk}
    return MARCH


def _writes(ctx):
    return [q["sql"] for q in ctx.captured_queries
            if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))]


@pytest.mark.parametrize("key", ALL_KEYS)
def test_report_is_read_only(data, reporter, key):
    params = _params(key)
    with CaptureQueriesContext(connection) as ctx:
        reports.run(reporter, key, params)
    assert _writes(ctx) == []


def test_only_audit_rows_are_written_for_pii(data, pii_reporter):
    with CaptureQueriesContext(connection) as ctx:
        reports.run(pii_reporter, "frequent_visitors", {**MARCH, "anonymize": False})
    writes = _writes(ctx)
    assert len(writes) == 1 and 'INSERT INTO "vms_auditlog"' in writes[0]


@pytest.mark.parametrize("key", ALL_KEYS)
def test_query_budget_per_report(data, reporter, key, django_assert_max_num_queries):
    params = _params(key)
    with django_assert_max_num_queries(10 if key == "event_attendance" else 4):
        reports.run(reporter, key, params)


# --- export ----------------------------------------------------------------------------

def _csv(resp):
    body = b"".join(resp.streaming_content).decode()
    return list(csv.reader(io.StringIO(body)))


def test_csv_headers_and_row_count(data, api_as):
    client = api_as(permissions=[EXPORT])
    r = client.get(f"{BASE}/denial_stats/export?start={D1}&end={D2}&fmt=csv")
    assert r.status_code == 200 and r["Content-Type"].startswith("text/csv")
    assert "attachment" in r["Content-Disposition"]
    rows = _csv(r)
    assert rows[0] == ["dimension", "bucket", "count"]
    assert len(rows) - 1 == 8
    assert rows[1:3] == [["reason", "blacklisted", "1"], ["reason", "outside_validity", "1"]]


def test_csv_export_is_anonymised_and_audited(data, api_as):
    client = api_as(permissions=[EXPORT])
    r = client.get(f"{BASE}/frequent_visitors/export?start={D1}&end={D3}&top=2")
    rows = _csv(r)
    assert rows[0] == ["visitor", "phone", "email", "id_doc_number", "visits"]
    assert len(rows) == 3 and rows[1][0].startswith("Visitor #") and rows[1][4] == "7"
    assert "Person" not in json.dumps(rows)
    log = AuditLog.objects.get(action=reports.ACT_EXPORT)
    assert log.entity_id == "frequent_visitors"
    assert log.detail["format"] == "csv" and log.detail["rows"] == 2
    assert log.detail["params"]["top"] == 2 and log.detail["pii"] is False


def test_csv_export_pii_needs_permission_then_audits_both(data, api_as):
    url = f"{BASE}/frequent_visitors/export?start={D1}&end={D3}&anonymize=false"
    assert api_as(permissions=[EXPORT]).get(url).status_code == 403
    assert not AuditLog.objects.exists()
    r = api_as(permissions=[EXPORT, PII]).get(url)
    assert _csv(r)[1][1] == "Person 1"
    assert set(AuditLog.objects.values_list("action", flat=True)) == {
        reports.ACT_EXPORT, reports.ACT_PII_VIEW}


def test_pdf_returns_501_and_is_not_audited(data, api_as):
    r = api_as(permissions=[EXPORT]).get(f"{BASE}/daily_summary/export?fmt=pdf")
    assert r.status_code == 501
    assert r.json()["error"]["code"] == "pdf_backend_unavailable"
    assert not AuditLog.objects.exists()
    assert api_as(permissions=[EXPORT]).get(
        f"{BASE}/daily_summary/export?fmt=docx").status_code == 400


# --- endpoints -------------------------------------------------------------------------

def test_catalogue_and_run_endpoints(data, api_as):
    client = api_as(permissions=[VIEW])
    cat = client.get(BASE).json()
    assert [c["key"] for c in cat] == ALL_KEYS
    r = client.get(f"{BASE}/daily_summary?date={D1}")
    assert r.status_code == 200
    assert r.json()["summary"]["registered"] == 7 and r.json()["anonymized"] is True
    # anonymize absent must never mean false (DRF boolean gotcha)
    top = client.get(f"{BASE}/frequent_visitors?start={D1}&end={D3}").json()
    assert top["anonymized"] is True


def test_endpoint_auth_matrix(data, api_as):
    urls = [BASE, f"{BASE}/daily_summary", f"{BASE}/daily_summary/export"]
    for url in urls:
        assert api_as(anonymous=True).get(url).status_code == 401
    # export permission alone cannot run on-screen reports and vice versa
    assert api_as(permissions=[EXPORT]).get(BASE).status_code == 403
    assert api_as(permissions=[EXPORT]).get(f"{BASE}/daily_summary").status_code == 403
    assert api_as(permissions=[VIEW]).get(f"{BASE}/daily_summary/export").status_code == 403
    assert api_as(permissions=[]).get(f"{BASE}/daily_summary").status_code == 403
    # anonymize=false without view_pii
    assert api_as(permissions=[VIEW]).get(
        f"{BASE}/frequent_visitors?anonymize=false").status_code == 403
    # reports never accept writes
    for verb in ("post", "put", "patch", "delete"):
        assert getattr(api_as(permissions=[VIEW, EXPORT, PII]), verb)(
            f"{BASE}/daily_summary").status_code == 405


def test_endpoint_validation_and_scope(data, api_as, zone_admin):
    client = api_as(permissions=[VIEW])
    assert client.get(f"{BASE}/nope").status_code == 404
    assert client.get(f"{BASE}/peak_hours?start=2025-01-01&end=2026-03-01").status_code == 400
    assert client.get(f"{BASE}/peak_hours?start={D2}&end={D1}").status_code == 400
    assert client.get(f"{BASE}/peak_hours?anonymize=maybe").status_code == 400
    scoped = api_as(user_id=zone_admin.user_id, permissions=[VIEW])
    assert scoped.get(f"{BASE}/daily_summary?date={D1}&zone={data.z2.pk}").status_code == 404
    assert scoped.get(f"{BASE}/daily_summary?date={D1}").json()["summary"]["registered"] == 4
