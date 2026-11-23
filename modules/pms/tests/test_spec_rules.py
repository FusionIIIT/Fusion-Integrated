"""Rules whose effect no journey shows on its own; each test names the ids it proves."""
from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings as live_settings
from django.utils import timezone

from modules.pms import registry
from modules.pms.api import serializers as s
from modules.pms.domain import state_machine as sm
from modules.pms.models import (
    AttorneyAssignment,
    Communication,
    DeadlineAlert,
    LicensingRequest,
    MaintenanceCycle,
    Notification,
    OfficeAction,
)
from modules.pms.services import deadlines
from modules.pms.tests.conftest import (
    ATTORNEY,
    DIRECTOR,
    PCC,
    approved_with_attorney,
    make_app,
    pdf,
    with_cycle,
)

pytestmark = pytest.mark.django_db
TEXT = "The claims overlap the cited coating art; narrow claim 1 to the tested range."


# PMS-AFR-062 PMS-AFR-063 PMS-AFR-196
@pytest.mark.parametrize("decision", ["reject", "needs_revision"])
def test_the_applicant_receives_the_directors_feedback(world, decision):
    app = make_app(sm.UNDER_REVIEW)
    with_cycle(app, DIRECTOR)
    world["director"].post(f"applications/{app.pk}/review",
                           {"decision": decision, "justification": TEXT})
    notice = Notification.objects.get(topic="review.decided")
    assert notice.recipient_user_id == app.applicant_user_id
    assert TEXT in notice.body


# PMS-AFR-067 BR-PMS-034
def test_a_rejected_application_can_be_revised_and_resubmitted(world):
    app = make_app(sm.UNDER_REVIEW)
    with_cycle(app, DIRECTOR)
    world["director"].post(f"applications/{app.pk}/review",
                           {"decision": "reject", "justification": TEXT})
    a = world["applicant"]
    assert a.patch(f"applications/{app.pk}", {"claims": "1. Narrower."}).status_code == 200
    r = a.post(f"applications/{app.pk}/resubmit", {"responses": {"review": TEXT}})
    assert r.json()["status"] == sm.RESUBMITTED


# BR-PMS-092 PMS-AFR-165
def test_only_a_rejected_application_can_be_appealed(world):
    app = make_app(sm.NEEDS_REVISION)
    r = world["applicant"].post(f"applications/{app.pk}/appeal",
                                {"grounds": "g", "justification": "j"})
    assert r.json()["error"]["code"] == "invalid_transition"


# PMS-AFR-064
def test_an_approved_application_is_routed_to_attorney_assignment(world):
    app = make_app(sm.UNDER_REVIEW)
    with_cycle(app, DIRECTOR)
    world["director"].post(f"applications/{app.pk}/review",
                           {"decision": "approve", "justification": TEXT})
    work = world["pcc"].get("my-work").json()
    assert [(i["kind"], i["id"]) for i in work] == [("assign_attorney", app.pk)]


# PMS-AFR-083 PMS-AFR-142
def test_the_assigned_attorney_searches_and_records_prior_art(world):
    app = approved_with_attorney()
    t = world["attorney"]
    assert t.post(f"applications/{app.pk}/prior-art", {
        "kind": "publication", "title": "Coating study", "identifier": "DOI-1"}).status_code \
        == 201
    body = t.post("prior-art/searches", {"query": "coating", "application_id": app.pk}).json()
    assert body["results"][0]["reference"]["identifier"] == "DOI-1"


# PMS-AFR-087 PMS-AFR-089
def test_extension_request_and_opinion_notice(world):
    app = approved_with_attorney()
    t = world["attorney"]
    t.post(f"applications/{app.pk}/legal-requests", {"kind": "extension",
                                                      "message": "Need two weeks."})
    assert Notification.objects.filter(topic="legal.request",
                                       recipient_user_id=app.applicant_user_id).exists()
    aid = t.post(f"applications/{app.pk}/assessments", {
        "analysis": "a", "novelty": "n", "non_obviousness": "o", "utility": "u",
        "recommendation": "needs_amendment"}).json()["assessments"][0]["id"]
    t.post(f"assessments/{aid}/finalize")
    recipients = set(Notification.objects.filter(topic="assessment.final")
                     .values_list("recipient_user_id", flat=True))
    assert recipients == {app.applicant_user_id, DIRECTOR}


# BR-PMS-076 BR-PMS-077 PMS-AFR-137 PMS-AFR-138
def test_e_signatures_are_never_collected_while_not_configured():
    assert set(s.PmsAgreementIn().fields) == {"agreement_reference", "consent"}
    from modules.pms.domain.policy import PolicySpec

    assert not any("signature" in f for f in PolicySpec.__dataclass_fields__)


# BR-PMS-131 PMS-AFR-221
def test_the_single_pcc_admin_rule_is_a_recorded_gap_with_one_office_role():
    offices = [d for d, codes in registry.ROLE_GRANTS.items() if "pms.policy.publish" in codes]
    assert offices == ["pms_pcc_admin"]


# PMS-AFR-215
def test_transport_is_tls_only_at_nginx():
    conf = (Path(live_settings.BASE_DIR) / "ops/nginx/fusion-platform.conf").read_text()
    assert "ssl_protocols TLSv1.2 TLSv1.3" in conf
    assert "Strict-Transport-Security" in conf


# PMS-AFR-214
def test_stored_documents_are_private_files_outside_the_repository(world, scanner):
    app = make_app(sm.DRAFT)
    world["applicant"].post(f"applications/{app.pk}/documents", {
        "file": pdf(), "kind": "claims", "title": "Claims", "sensitivity": "restricted"},
        fmt="multipart")
    stored = [p for p in Path(live_settings.PMS_UPLOAD_ROOT).rglob("*") if p.is_file()]
    assert len(stored) == 1
    assert stored[0].stat().st_mode & 0o777 == 0o600
    assert Path(live_settings.BASE_DIR) not in stored[0].resolve().parents


# PMS-AFR-099 PMS-AFR-203 PMS-AFR-204 PMS-AFR-210
def test_the_attorney_uploads_the_filing_package_and_the_applicant_hears(world, scanner):
    app = approved_with_attorney()
    t = world["attorney"]
    doc = t.post(f"applications/{app.pk}/documents", {
        "file": pdf(), "kind": "filing_package", "title": "Filing package",
        "sensitivity": "confidential"}, fmt="multipart").json()
    package = next(d for d in doc if d["kind"] == "filing_package")
    t.post(f"applications/{app.pk}/documents", {"file": pdf(), "document_id": package["id"]},
           fmt="multipart")
    bodies = list(Notification.objects.filter(topic="document.updated",
                                              recipient_user_id=app.applicant_user_id)
                  .values_list("body", flat=True))
    assert any(b.startswith("A new document") for b in bodies)
    assert any(b.startswith("Version 2") for b in bodies)
    assert app.audit_entries.filter(action="document.uploaded").count() == 2


# PMS-AFR-159 PMS-AFR-229 CFR-PMS-019 CFR-PMS-029
def test_a_technology_transfer_request_is_routed_and_kept_confidential(world):
    app = make_app(sm.FILED)
    r = world["applicant"].post("licensing-requests", {
        "application_id": app.pk, "kind": "technology_transfer", "summary": "Transfer it."})
    assert r.json()["kind"] == "technology_transfer" and r.json()["status"] == "routed"
    assert LicensingRequest.objects.get().committee_name == "Technology Transfer Committee"
    assert world["other"].get("licensing-requests").json() == []


# PMS-AFR-173 PMS-AFR-174 PMS-AFR-175 PMS-AFR-202 BR-PMS-098 BR-PMS-099 BR-PMS-100
def test_the_sweep_alerts_on_every_kind_of_deadline(world):
    soon = timezone.localdate() + timedelta(days=5)
    revising = make_app(sm.NEEDS_REVISION, revision_due_on=soon)
    filed = approved_with_attorney()
    filed.status = sm.FILED
    filed.save()
    comm = Communication.objects.create(application=filed, kind="office_action",
                                        received_on=timezone.localdate(), reference="F",
                                        recorded_by_user_id=ATTORNEY)
    OfficeAction.objects.create(communication=comm, application=filed, response_due_on=soon)
    no_deadline = Communication.objects.create(application=filed, kind="other",
                                               received_on=timezone.localdate(),
                                               reference="G", recorded_by_user_id=ATTORNEY)
    OfficeAction.objects.create(communication=no_deadline, application=filed)
    granted = make_app(sm.GRANTED, grant_date=timezone.localdate(), patent_number="P")
    MaintenanceCycle.objects.create(application=granted, seq=1, due_on=soon, source="manual",
                                    deciding_director_user_id=DIRECTOR,
                                    status=sm.DECISION_REQUESTED)
    deadlines.sweep()
    assert set(DeadlineAlert.objects.values_list("kind", flat=True)) == {
        "revision", "office_action", "maintenance"}
    assert set(Notification.objects.filter(topic="deadline.reminder")
               .values_list("recipient_user_id", flat=True)) == {
        revising.applicant_user_id, ATTORNEY, DIRECTOR}


# PMS-AFR-179 PMS-AFR-180 PMS-AFR-200 PMS-AFR-201 BR-PMS-104
def test_a_missed_deadline_escalates_to_the_configured_chain(world):
    app = make_app(sm.UNDER_REVIEW)
    with_cycle(app, DIRECTOR, due=timezone.localdate() - timedelta(days=1))
    deadlines.sweep()
    notice = Notification.objects.get(topic="escalation.raised")
    assert notice.recipient_user_id == PCC


# PMS-AFR-081 BW-PMS-07
def test_reassignment_after_a_decline_reaches_attorney_assigned(world):
    app = make_app(sm.PENDING_REVIEW)
    with_cycle(app, status="decided", decision="approve")
    AttorneyAssignment.objects.create(application=app, attorney_user_id=3002,
                                      assigned_by_user_id=PCC, status=sm.DECLINED)
    offer = world["pcc"].post(f"applications/{app.pk}/assign-attorney",
                              {"attorney_user_id": ATTORNEY}).json()["attorney_assignments"]
    live = next(o for o in offer if o["status"] == "offered")
    world["attorney"].post(f"attorney-assignments/{live['id']}/respond", {"accept": True})
    app.refresh_from_db()
    assert app.status == sm.ATTORNEY_ASSIGNED


# PMS-AFR-163 BR-PMS-139
def test_a_recorded_agreement_says_it_was_not_shared_with_finance(world):
    app = make_app(sm.FILED)
    req = LicensingRequest.objects.create(application=app, applicant_user_id=1001,
                                          kind="licensing", summary="s", status="negotiating",
                                          route_kind="committee", committee_name="TTC")
    r = world["pcc"].post(f"licensing-requests/{req.pk}/agreement", {
        "counterparty": "Acme", "signed_on": str(timezone.localdate()),
        "terms_summary": "Royalty 3%.", "financial_terms": "3% of net sales."})
    assert r.json()["agreement"]["financial_sync"] == "not_shared_no_integration"
