"""Every live use case end to end through HTTP only, actor by actor (Step 5.12)."""
from datetime import date, timedelta

import pytest
from django.core import mail
from django.utils import timezone
from freezegun import freeze_time

from modules.pms.domain import state_machine as sm
from modules.pms.models import (
    Application,
    AuditEntry,
    Escalation,
    FinancialRecord,
    MaintenanceCycle,
    Notification,
    PriorArtSearch,
    ReportRun,
)
from modules.pms.services import deadlines, notifications, reports
from modules.pms.tests.conftest import (
    ATTORNEY,
    CO_INVENTOR,
    DIRECTOR,
    DIRECTOR_2,
    PCC,
    pdf,
)

pytestmark = pytest.mark.django_db
JUSTIFY = "The claimed coating method is novel and the claims are clearly supported."


def draft(world, **fields):
    a = world["applicant"]
    r = a.post("applications", {"title": "Graphene anode", "abstract": "An anode.",
                                "description": "A detailed description.",
                                "claims": "1. An anode comprising graphene.",
                                "domain_code": "materials", **fields})
    assert r.status_code == 201, r.json()
    pk = r.json()["id"]
    r = a.put(f"applications/{pk}/inventors", {"inventors": [
        {"user_id": 1001, "share_percent": "60"},
        {"user_id": CO_INVENTOR, "share_percent": "40"}]})
    assert r.status_code == 200, r.json()
    return pk


def submitted(world):
    pk = draft(world)
    r = world["applicant"].post(f"applications/{pk}/documents",
                                {"file": pdf(), "kind": "specification",
                                 "title": "Complete specification",
                                 "sensitivity": "confidential"}, fmt="multipart")
    assert r.status_code == 201, r.json()
    r = world["applicant"].post(f"applications/{pk}/submit")
    assert r.status_code == 200, r.json()
    return pk


def under_review(world):
    pk = submitted(world)
    r = world["pcc"].post(f"applications/{pk}/assign-director", {"director_user_id": DIRECTOR})
    assert r.status_code == 200, r.json()
    return pk


def decided(world, decision):
    pk = under_review(world)
    r = world["director"].post(f"applications/{pk}/review",
                               {"decision": decision, "justification": JUSTIFY})
    assert r.status_code == 200, r.json()
    return pk


def with_attorney(world):
    pk = decided(world, "approve")
    r = world["pcc"].post(f"applications/{pk}/assign-attorney", {"attorney_user_id": ATTORNEY})
    assert r.status_code == 200, r.json()
    offer = r.json()["attorney_assignments"][0]["id"]
    r = world["attorney"].post(f"attorney-assignments/{offer}/respond", {"accept": True})
    assert r.status_code == 200, r.json()
    return pk


def ready_to_file(world):
    pk = with_attorney(world)
    budget = world["attorney"].post(f"applications/{pk}/budgets", {
        "filing_fee": "8000", "attorney_fee": "40000", "admin_cost": "2000"}).json()["id"]
    assert world["director"].post(f"budgets/{budget}/decision",
                                  {"approve": True}).status_code == 200
    detail = world["applicant"].get(f"applications/{pk}").json()
    for inv in detail["inventors"]:
        assert world["applicant"].post(
            f"applications/{pk}/inventors/{inv['id']}/agreement",
            {"agreement_reference": "IPR/2026/1", "consent": True}).status_code == 200
    return pk


def filed(world):
    pk = ready_to_file(world)
    r = world["attorney"].post(f"applications/{pk}/filings", {
        "jurisdiction": "IN", "office_name": "Indian Patent Office",
        "external_filing_id": f"2026210{pk:05d}", "filing_date": str(timezone.localdate()),
        "confirmation_reference": "CBR 1"})
    assert r.status_code == 200, r.json()
    return pk


def granted(world):
    pk = filed(world)
    r = world["attorney"].post(f"applications/{pk}/communications", {
        "kind": "grant", "received_on": str(timezone.localdate()), "reference": "GRANT-1",
        "grant_date": str(timezone.localdate()), "patent_number": "IN400001",
        "jurisdiction": "IN"})
    assert r.status_code == 200, r.json()
    return pk


# -- UC-PMS-001 ----------------------------------------------------------------
# UC-PMS-001 PMS-AFR-038 PMS-AFR-042 PMS-AFR-044 PMS-AFR-045 PMS-AFR-047 PMS-AFR-048 PMS-AFR-192
def test_uc_pms_001_submit_application(world, scanner):
    pk = submitted(world)
    app = Application.objects.get(pk=pk)
    assert app.status == sm.SUBMITTED
    assert app.reference.startswith(f"PMS-{timezone.now().year}-")
    assert AuditEntry.objects.filter(application=app, action="application.submit",
                                     to_state="submitted").exists()
    assert Notification.objects.filter(topic="application.submitted",
                                       recipient_user_id=1001).exists()
    assert scanner.scans == 1


# UC-PMS-001 BR-PMS-017 PMS-AFR-042 CFR-PMS-005
def test_uc_pms_001_incomplete_submission_names_what_is_missing(world, scanner):
    pk = draft(world)
    r = world["applicant"].post(f"applications/{pk}/submit")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "incomplete"
    assert "supporting document" in r.json()["error"]["message"]
    assert Application.objects.get(pk=pk).status == sm.DRAFT


# UC-PMS-001 BR-PMS-014 BR-PMS-016 PMS-AFR-039 PMS-AFR-041
def test_uc_pms_001_a_failed_document_keeps_the_prior_state(world, scanner):
    pk = draft(world)
    r = world["applicant"].post(f"applications/{pk}/documents", {
        "file": pdf("x.pdf", b"PK\x03\x04 a zip"), "kind": "claims", "title": "Claims",
        "sensitivity": "restricted"}, fmt="multipart")
    assert r.json()["error"]["code"] == "not_pdf"
    r = world["applicant"].post(f"applications/{pk}/documents", {
        "file": pdf("v.pdf", b"%PDF-1.4 " + b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-"
                    b"ANTIVIRUS-TEST-FILE!$H+H*"),
        "kind": "claims", "title": "Claims", "sensitivity": "restricted"}, fmt="multipart")
    assert r.json()["error"]["code"] == "malware_found"
    assert world["applicant"].get(f"applications/{pk}/documents").json() == []


# UC-PMS-001 BR-PMS-016 PMS-AFR-041
def test_uc_pms_001_no_scanner_means_no_acceptance(world, settings, tmp_path):
    settings.PMS_MALWARE_SCANNER, settings.PMS_CLAMD_SOCKET = "clamd", ""
    settings.PMS_UPLOAD_ROOT = str(tmp_path)
    pk = draft(world)
    r = world["applicant"].post(f"applications/{pk}/documents", {
        "file": pdf(), "kind": "claims", "title": "Claims", "sensitivity": "restricted"},
        fmt="multipart")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "scanner_unavailable"
    assert [f for f in tmp_path.rglob("*") if f.is_file()] == []


# -- UC-PMS-002, 030 -------------------------------------------------------------
# UC-PMS-002 PMS-AFR-010 PMS-AFR-047 PMS-AFR-209 CFR-PMS-001
def test_uc_pms_002_track_status_and_history(world, scanner):
    pk = under_review(world)
    a = world["applicant"]
    assert a.get("applications").json()["results"][0]["status"] == sm.UNDER_REVIEW
    history = a.get(f"applications/{pk}/history").json()
    assert [h["to_state"] for h in history if h["action"].startswith("application.")
            and h["to_state"]][-2:] == ["submitted", "under_review"]


# UC-PMS-002 BR-PMS-130 PMS-AFR-220 CFR-PMS-027
def test_uc_pms_002_another_applicants_record_is_blocked(world, scanner):
    pk = submitted(world)
    assert world["other"].get(f"applications/{pk}").status_code == 404


# UC-PMS-030 BR-PMS-003 PMS-AFR-016
def test_uc_pms_030_own_reports_only(world, scanner):
    submitted(world)
    rows = world["applicant"].get("reports/status").json()["rows"]
    assert len(rows) == 1
    assert world["other"].get("reports/status").json()["rows"] == []
    assert world["applicant"].get("reports/financial").status_code == 422


# -- UC-PMS-003 ------------------------------------------------------------------
# UC-PMS-003 PMS-AFR-132 PMS-AFR-133 PMS-AFR-136 PMS-AFR-140 CFR-PMS-016
def test_uc_pms_003_manage_co_inventors_and_agreements(world, scanner):
    pk = draft(world)
    detail = world["applicant"].get(f"applications/{pk}").json()
    assert {i["user_id"] for i in detail["inventors"]} == {1001, CO_INVENTOR}
    inv = detail["inventors"][1]["id"]
    r = world["applicant"].post(f"applications/{pk}/inventors/{inv}/agreement",
                                {"agreement_reference": "IPR/1", "consent": True})
    assert r.json()["inventors"][1]["agreement_completed_at"]
    assert Notification.objects.filter(topic="inventors.changed",
                                       recipient_user_id=CO_INVENTOR).exists()


# UC-PMS-003 BR-PMS-073 BR-PMS-074 PMS-AFR-134 PMS-AFR-135
def test_uc_pms_003_invalid_shares_are_not_committed(world, scanner):
    pk = draft(world)
    r = world["applicant"].put(f"applications/{pk}/inventors", {"inventors": [
        {"user_id": 1001, "share_percent": "70"}, {"name": "X", "affiliation": "Y",
                                                    "share_percent": "20"}]})
    assert r.json()["error"]["code"] == "shares_not_100"
    assert len(world["applicant"].get(f"applications/{pk}").json()["inventors"]) == 2


# -- UC-PMS-004 ------------------------------------------------------------------
# UC-PMS-004 PMS-AFR-141 PMS-AFR-143 PMS-AFR-144 PMS-AFR-146 PMS-AFR-147 PMS-AFR-231 CFR-PMS-017
def test_uc_pms_004_search_and_attach_prior_art(world, scanner):
    pk = draft(world)
    a = world["applicant"]
    r = a.post(f"applications/{pk}/prior-art", {"kind": "patent", "identifier": "US1",
                                                "title": "Graphene anode coating"})
    assert r.status_code == 201
    r = a.post("prior-art/searches", {"query": "graphene coating", "application_id": pk})
    body = r.json()
    assert body["results"][0]["reference"]["identifier"] == "US1"
    assert {s["status"] for s in body["sources"]} == {"not connected"}
    assert PriorArtSearch.objects.filter(actor_user_id=1001).count() == 1


# -- UC-PMS-005 ------------------------------------------------------------------
# UC-PMS-005 BR-PMS-033 PMS-AFR-066 PMS-AFR-070 PMS-AFR-071 BW-PMS-02 CFR-PMS-008
def test_uc_pms_005_revise_and_resubmit(world, scanner):
    pk = decided(world, "needs_revision")
    a = world["applicant"]
    assert a.patch(f"applications/{pk}", {"claims": "1. A narrower claim."}).status_code == 200
    r = a.post(f"applications/{pk}/resubmit", {"responses": {
        "review": "Claim 1 is narrowed to the coating temperature the Director asked about."}})
    assert r.status_code == 200, r.json()
    app = Application.objects.get(pk=pk)
    assert app.status == sm.RESUBMITTED and app.version == 2
    assert app.versions.count() == 2
    r = world["pcc"].post(f"applications/{pk}/assign-director", {"director_user_id": DIRECTOR})
    assert r.json()["review_cycles"][-1]["cycle_no"] == 2


# UC-PMS-005 BR-PMS-036 PMS-AFR-069
def test_uc_pms_005_unchanged_resubmission_is_refused(world, scanner):
    pk = decided(world, "needs_revision")
    r = world["applicant"].post(f"applications/{pk}/resubmit", {"responses": {
        "review": "I believe the original wording already addresses all of this feedback."}})
    assert r.json()["error"]["code"] == "revision_unchanged"


# UC-PMS-005 BR-PMS-035 BR-PMS-038 PMS-AFR-068 PMS-AFR-072
def test_uc_pms_005_late_resubmission_expires_the_application(world, scanner):
    pk = decided(world, "needs_revision")
    with freeze_time(timezone.now() + timedelta(days=61)):
        r = world["applicant"].post(f"applications/{pk}/resubmit", {"responses": {
            "review": "x" * 60}})
    assert r.json()["error"]["code"] == "revision_period_over"
    assert Application.objects.get(pk=pk).status == sm.EXPIRED


# -- UC-PMS-006 ------------------------------------------------------------------
# UC-PMS-006 PMS-AFR-125 PMS-AFR-129 PMS-AFR-130 PMS-AFR-131 BW-PMS-16 CFR-PMS-015
def test_uc_pms_006_withdraw(world, scanner):
    pk = under_review(world)
    r = world["applicant"].post(f"applications/{pk}/withdraw", {"reason": "Publishing."})
    assert r.json()["status"] == sm.WITHDRAWN
    assert r.json()["review_cycles"][0]["status"] == "closed"
    assert world["pcc"].get("my-work").json() == []


# UC-PMS-006 BR-PMS-067 PMS-AFR-126
def test_uc_pms_006_ineligible_status_blocks_withdrawal(world, scanner):
    pk = filed(world)
    r = world["applicant"].post(f"applications/{pk}/withdraw", {"reason": "Changed mind."})
    assert r.json()["error"]["code"] == "withdrawal_after_filing"


# -- UC-PMS-007, 008 ---------------------------------------------------------------
# UC-PMS-007 PMS-AFR-049 PMS-AFR-056 PMS-AFR-057 PMS-AFR-193 PMS-AFR-194 CFR-PMS-006
def test_uc_pms_007_assign_to_director(world, scanner):
    pk = submitted(world)
    cands = world["pcc"].get(f"applications/{pk}/director-candidates").json()
    assert [c["user_id"] for c in cands] == [DIRECTOR, DIRECTOR_2]
    r = world["pcc"].post(f"applications/{pk}/assign-director", {"director_user_id": DIRECTOR})
    assert r.json()["status"] == sm.UNDER_REVIEW
    assert Notification.objects.filter(topic="review.assigned",
                                       recipient_user_id=DIRECTOR).exists()
    assert Notification.objects.filter(topic="application.status",
                                       recipient_user_id=1001).exists()


# UC-PMS-007 BR-PMS-023 PMS-AFR-051
def test_uc_pms_007_no_eligible_director_stays_submitted(world, scanner):
    pk = submitted(world)
    world["applicant"]._go()
    Application.objects.filter(pk=pk).update(domain_code="software")
    assert world["pcc"].get(f"applications/{pk}/director-candidates").json() == []
    r = world["pcc"].post(f"applications/{pk}/assign-director", {"director_user_id": DIRECTOR})
    assert r.json()["error"]["code"] == "director_area_mismatch"
    assert Application.objects.get(pk=pk).status == sm.SUBMITTED


# UC-PMS-008 PMS-AFR-059 PMS-AFR-065 BW-PMS-01 CFR-PMS-007
def test_uc_pms_008_review_approve(world, scanner):
    pk = decided(world, "approve")
    assert Application.objects.get(pk=pk).status == sm.APPROVED
    assert Notification.objects.filter(topic="review.approved", recipient_user_id=PCC).exists()


# UC-PMS-008 BR-PMS-030 PMS-AFR-060
def test_uc_pms_008_short_justification_is_refused(world, scanner):
    pk = under_review(world)
    r = world["director"].post(f"applications/{pk}/review",
                               {"decision": "reject", "justification": "No."})
    assert r.json()["error"]["code"] == "justification_too_short"


# UC-PMS-008 PMS-AFR-222
def test_uc_pms_008_unassigned_director_cannot_decide(world, scanner):
    pk = under_review(world)
    r = world["director2"].post(f"applications/{pk}/review",
                                {"decision": "approve", "justification": JUSTIFY})
    assert r.status_code == 403 and r.json()["error"]["code"] == "not_assigned"


# -- UC-PMS-009 ------------------------------------------------------------------
# UC-PMS-009 PMS-AFR-090 PMS-AFR-091 PMS-AFR-097 PMS-AFR-098 BR-PMS-053 BW-PMS-08 CFR-PMS-011
def test_uc_pms_009_budget_approved_and_logged(world, scanner):
    pk = with_attorney(world)
    budget = world["attorney"].post(f"applications/{pk}/budgets", {
        "filing_fee": "8000", "attorney_fee": "40000", "admin_cost": "2000"})
    assert budget.status_code == 201
    r = world["director"].post(f"budgets/{budget.json()['id']}/decision", {"approve": True})
    assert r.json()["status"] == "approved"
    assert r.json()["availability"] == "not_available"
    assert FinancialRecord.objects.get(kind="budget_approved").authorization_level == "director"


# UC-PMS-009 BR-PMS-051 PMS-AFR-095 PMS-AFR-197 PMS-AFR-226 BW-PMS-10
def test_uc_pms_009_above_threshold_escalates(world, scanner):
    pk = with_attorney(world)
    budget = world["attorney"].post(f"applications/{pk}/budgets", {
        "filing_fee": "200000", "attorney_fee": "0", "admin_cost": "0"}).json()["id"]
    r = world["director"].post(f"budgets/{budget}/decision", {"approve": True})
    assert r.json()["status"] == "escalated"
    assert Escalation.objects.filter(kind="budget_threshold", status="open").exists()
    assert Notification.objects.filter(topic="budget.decided",
                                       recipient_user_id=ATTORNEY).exists()


# UC-PMS-009 PMS-AFR-236 BW-PMS-09 CFR-PMS-030
def test_uc_pms_009_budget_rejected(world, scanner):
    pk = with_attorney(world)
    budget = world["attorney"].post(f"applications/{pk}/budgets", {
        "filing_fee": "8000", "attorney_fee": "1", "admin_cost": "1"}).json()["id"]
    r = world["director"].post(f"budgets/{budget}/decision", {"approve": False})
    assert r.json()["status"] == "rejected"


# -- UC-PMS-010, 011 ---------------------------------------------------------------
# UC-PMS-010 UC-PMS-011 PMS-AFR-074 PMS-AFR-080 PMS-AFR-195 BW-PMS-06 CFR-PMS-009
def test_uc_pms_010_011_assign_attorney_and_accept(world, scanner):
    pk = with_attorney(world)
    assert Application.objects.get(pk=pk).status == sm.ATTORNEY_ASSIGNED
    assert Notification.objects.filter(topic="attorney.assigned",
                                       recipient_user_id=ATTORNEY).exists()


# UC-PMS-010 BR-PMS-041 PMS-AFR-075
def test_uc_pms_010_non_panel_attorney_needs_exception(world, scanner):
    pk = decided(world, "approve")
    r = world["pcc"].post(f"applications/{pk}/assign-attorney", {"attorney_user_id": 1003})
    assert r.json()["error"]["code"] == "attorney_not_eligible"
    r = world["pcc"].post(f"applications/{pk}/assign-attorney", {
        "attorney_user_id": 1003, "exception_reason": "Board resolution 12 permits it."})
    assert r.json()["attorney_assignments"][0]["is_exception"] is True


# UC-PMS-011 PMS-AFR-081 BW-PMS-07
def test_uc_pms_011_decline_moves_to_pending_review(world, scanner):
    pk = decided(world, "approve")
    offer = world["pcc"].post(f"applications/{pk}/assign-attorney",
                              {"attorney_user_id": ATTORNEY}).json()["attorney_assignments"][0]
    r = world["attorney"].post(f"attorney-assignments/{offer['id']}/respond",
                               {"accept": False, "reason": "Conflict with another client."})
    assert r.json()["status"] == "declined"
    assert Application.objects.get(pk=pk).status == sm.PENDING_REVIEW
    assert Notification.objects.filter(topic="attorney.declined",
                                       recipient_user_id=PCC).exists()


# -- UC-PMS-012, 033 ----------------------------------------------------------------
# UC-PMS-012 BR-PMS-046 PMS-AFR-082 PMS-AFR-084 PMS-AFR-085 PMS-AFR-086 PMS-AFR-088 CFR-PMS-010
def test_uc_pms_012_patentability_assessment(world, scanner):
    pk = with_attorney(world)
    t = world["attorney"]
    r = t.post(f"applications/{pk}/assessments", {"analysis": "Claims read on D1 partly."})
    aid = r.json()["assessments"][0]["id"]
    assert t.post(f"assessments/{aid}/finalize").json()["error"]["code"] \
        == "opinion_incomplete"
    t.post(f"applications/{pk}/assessments", {
        "assessment_id": aid, "analysis": "a", "novelty": "n", "non_obviousness": "o",
        "utility": "u", "recommendation": "file_patent"})
    assert t.post(f"assessments/{aid}/finalize").json()["status"] == "final"
    r = t.post(f"applications/{pk}/legal-requests", {"kind": "information",
                                                      "message": "Send lab data."})
    assert r.json()["legal_requests"][0]["kind"] == "information"


# UC-PMS-033 PMS-AFR-037 CFR-PMS-004
def test_uc_pms_033_legal_advice(world, scanner):
    pk = with_attorney(world)
    r = world["attorney"].post(f"applications/{pk}/legal-advice",
                               {"advice": "Do not publish before filing."})
    assert r.json()["legal_advice"][0]["stage"] == sm.ATTORNEY_ASSIGNED
    assert r.json()["status"] == sm.ATTORNEY_ASSIGNED


# -- UC-PMS-013 --------------------------------------------------------------------
# UC-PMS-013 PMS-AFR-100 PMS-AFR-101 PMS-AFR-104 PMS-AFR-105 PMS-AFR-198 BR-PMS-055 CFR-PMS-012
def test_uc_pms_013_external_filing(world, scanner):
    pk = filed(world)
    app = Application.objects.get(pk=pk)
    assert app.status == sm.FILED and app.filings.count() == 1
    assert app.filings.get().format_validation == "not_validated_no_rules"
    assert Notification.objects.filter(topic="filing.confirmed",
                                       recipient_user_id=1001).exists()


# UC-PMS-013 BR-PMS-128 PMS-AFR-218 BW-PMS-11 CFR-PMS-026
def test_uc_pms_013_missing_prerequisite_blocks_filing(world, scanner):
    pk = with_attorney(world)
    r = world["attorney"].post(f"applications/{pk}/filings", {
        "jurisdiction": "IN", "office_name": "IPO", "external_filing_id": "20262100001",
        "filing_date": str(timezone.localdate()), "confirmation_reference": "c"})
    assert r.json()["error"]["code"] == "filing_blocked"
    assert "budget" in r.json()["error"]["message"]


# UC-PMS-013 BR-PMS-056 PMS-AFR-102 PMS-AFR-103
def test_uc_pms_013_international_filing_needs_justification(world, scanner):
    pk = ready_to_file(world)
    r = world["attorney"].post(f"applications/{pk}/filings", {
        "jurisdiction": "EP", "office_name": "EPO", "external_filing_id": "EP26000001",
        "filing_date": str(timezone.localdate()), "confirmation_reference": "c"})
    assert r.json()["error"]["code"] == "international_justification_required"


# -- UC-PMS-014, 015, 029 -----------------------------------------------------------
def _office_action(world, pk, review):
    r = world["attorney"].post(f"applications/{pk}/communications", {
        "kind": "office_action", "received_on": str(timezone.localdate()),
        "reference": "FER/1", "response_due_on": str(timezone.localdate() + timedelta(60)),
        "requires_applicant_review": review})
    assert r.status_code == 200, r.json()
    return r.json()["office_actions"][0]["id"]


# UC-PMS-014 UC-PMS-015 UC-PMS-029 PMS-AFR-116 PMS-AFR-118 PMS-AFR-119 PMS-AFR-199 BW-PMS-12
def test_uc_pms_014_015_029_office_action_with_applicant_review(world, scanner):
    pk = filed(world)
    oa = _office_action(world, pk, True)
    t, a = world["attorney"], world["applicant"]
    assert t.post(f"office-actions/{oa}/response", {"draft": "Claim 1 amended."}).json()[
        "status"] == sm.AWAITING_APPLICANT
    r = t.post(f"office-actions/{oa}/submission", {"submitted_on": str(timezone.localdate()),
                                                   "reference": "R1"})
    assert r.json()["error"]["code"] == "invalid_transition"
    assert a.post(f"office-actions/{oa}/approve").json()["status"] == sm.APPLICANT_APPROVED
    assert t.post(f"office-actions/{oa}/submission", {
        "submitted_on": str(timezone.localdate()), "reference": "R1"}).json()["status"] \
        == sm.RESPONSE_SUBMITTED


# UC-PMS-015 BR-PMS-146 PMS-AFR-120 PMS-AFR-122 BW-PMS-13 CFR-PMS-014
def test_uc_pms_015_without_applicant_review_and_with_extension(world, scanner):
    pk = filed(world)
    oa = _office_action(world, pk, False)
    t = world["attorney"]
    assert t.post(f"office-actions/{oa}/response", {"draft": "Reply."}).json()["status"] \
        == sm.RESPONSE_READY
    later = str(timezone.localdate() + timedelta(days=120))
    assert t.post(f"office-actions/{oa}/extension", {"new_due_on": later,
                                                     "reason": "Data pending."}).json()[
        "current_due_on"] == later


# UC-PMS-014 BR-PMS-138 PMS-AFR-106 PMS-AFR-117 PMS-AFR-228
def test_uc_pms_014_non_office_action_communication(world, scanner):
    pk = filed(world)
    r = world["attorney"].post(f"applications/{pk}/communications", {
        "kind": "other", "received_on": str(timezone.localdate()), "reference": "LTR-1"})
    assert r.json()["office_actions"] == []
    assert r.json()["status"] == sm.FILED


# -- UC-PMS-016, 027 -----------------------------------------------------------------
# UC-PMS-016 UC-PMS-027 BR-PMS-097 PMS-AFR-172 PMS-AFR-176 PMS-AFR-181 CFR-PMS-021
def test_uc_pms_016_027_deadlines_alerts_and_escalation(world, scanner):
    pk = under_review(world)
    with freeze_time(timezone.now() + timedelta(days=18)):
        report = deadlines.sweep()
    assert report.alerts >= 1
    with freeze_time(timezone.now() + timedelta(days=40)):
        deadlines.sweep()
        rows = world["pcc"].get("deadlines").json()
        assert rows[0]["missed"] is True
        case = world["pcc"].get("escalations").json()[0]
        assert case["kind"] == "missed_review"
        r = world["pcc"].post(f"applications/{pk}/assign-director",
                              {"director_user_id": DIRECTOR_2})
        assert r.status_code == 200, r.json()
    assert Escalation.objects.get(pk=case["id"]).status == "resolved"


# UC-PMS-027 PMS-AFR-026 PMS-AFR-029 BW-PMS-10 CFR-PMS-028
def test_uc_pms_027_handle_exceptional_case(world, scanner):
    pk = with_attorney(world)
    budget = world["attorney"].post(f"applications/{pk}/budgets", {
        "filing_fee": "200000", "attorney_fee": "0", "admin_cost": "0"}).json()["id"]
    world["director"].post(f"budgets/{budget}/decision", {"approve": True})
    p = world["pcc"]
    assert p.post(f"budgets/{budget}/route", {"routed_to": "Finance Committee"}).json()[
        "status"] == "escalation_tracked"
    r = p.post(f"budgets/{budget}/external-decision", {
        "approved": True, "reference": "FC/31", "decided_on": str(timezone.localdate())})
    assert r.json()["status"] == "external_approved"


# -- UC-PMS-017, 018 -----------------------------------------------------------------
# UC-PMS-017 UC-PMS-018 PMS-AFR-108 PMS-AFR-111 PMS-AFR-112 PMS-AFR-113 PMS-AFR-114 PMS-AFR-115
def test_uc_pms_017_018_maintenance_renewal(world, scanner):
    pk = granted(world)
    cycle = MaintenanceCycle.objects.get(application_id=pk)
    assert cycle.due_on == date.fromordinal(timezone.localdate().toordinal()) + (
        cycle.due_on - timezone.localdate())
    t = world["attorney"]
    assert t.post(f"maintenance-cycles/{cycle.pk}/request-decision").json()[
        "deciding_director_user_id"] == DIRECTOR
    assert world["director"].post(f"maintenance-cycles/{cycle.pk}/decision",
                                  {"renew": True}).json()["status"] == sm.RENEW_APPROVED
    r = t.post(f"maintenance-cycles/{cycle.pk}/action", {
        "reference": "RCPT-1", "amount": "4000", "actioned_on": str(timezone.localdate())})
    assert r.json()["status"] == sm.RENEWED
    assert MaintenanceCycle.objects.filter(application_id=pk, seq=2).exists()
    assert MaintenanceCycle.objects.get(application_id=pk, seq=1).status == sm.RENEWED
    assert FinancialRecord.objects.filter(kind="maintenance_payment").count() == 1


# UC-PMS-018 BR-PMS-061 PMS-AFR-110 BW-PMS-15 CW-PMS-04 CFR-PMS-013
def test_uc_pms_018_do_not_renew(world, scanner):
    pk = granted(world)
    cycle = MaintenanceCycle.objects.get(application_id=pk)
    world["attorney"].post(f"maintenance-cycles/{cycle.pk}/request-decision")
    r = world["director"].post(f"maintenance-cycles/{cycle.pk}/decision", {"renew": False})
    assert r.json()["status"] == sm.DO_NOT_RENEW


# -- UC-PMS-019 -----------------------------------------------------------------------
# UC-PMS-019 BR-PMS-082 PMS-AFR-150 PMS-AFR-151 PMS-AFR-152 PMS-AFR-153 PMS-AFR-155 CFR-PMS-018
def test_uc_pms_019_document_versions(world, scanner):
    pk = draft(world)
    a = world["applicant"]
    doc = a.post(f"applications/{pk}/documents", {"file": pdf(), "kind": "claims",
                                                  "title": "Claims",
                                                  "sensitivity": "restricted"},
                 fmt="multipart").json()[0]
    r = a.post(f"applications/{pk}/documents", {"file": pdf(), "document_id": doc["id"]},
               fmt="multipart")
    versions = r.json()[0]["versions"]
    assert [v["number"] for v in versions] == [2, 1]
    assert [v["is_current"] for v in versions] == [True, False]
    download = a.client.get(f"/api/v1/pms/documents/versions/{versions[1]['id']}/download")
    assert download.status_code == 200
    assert b"".join(download.streaming_content).startswith(b"%PDF")


# -- UC-PMS-020, 021 ------------------------------------------------------------------
# UC-PMS-020 UC-PMS-021 BR-PMS-088 BR-PMS-139 PMS-AFR-158 PMS-AFR-160 PMS-AFR-161 PMS-AFR-162
def test_uc_pms_020_021_licensing(world, scanner):
    pk = filed(world)
    r = world["applicant"].post("licensing-requests", {"application_id": pk,
                                                       "kind": "licensing",
                                                       "summary": "Licence the coating."})
    assert r.json()["status"] == "routed"
    req = r.json()["id"]
    p = world["pcc"]
    assert p.post(f"licensing-requests/{req}/notes", {"note": "Term sheet."}).json()[
        "status"] == "negotiating"
    r = p.post(f"licensing-requests/{req}/agreement", {
        "counterparty": "Acme Cells", "signed_on": str(timezone.localdate()),
        "terms_summary": "Non-exclusive."})
    assert r.json()["agreement"]["financial_sync"] == "not_shared_no_integration"
    assert world["director"].get("licensing-requests").json() == []


# -- UC-PMS-022, 023 ------------------------------------------------------------------
def _appeal(world):
    pk = decided(world, "reject")
    r = world["applicant"].post(f"applications/{pk}/appeal", {
        "grounds": "The cited art is a different field.", "justification": "See claim 4."})
    assert r.json()["status"] == sm.APPEAL_SUBMITTED
    appeal = r.json()["appeals"][0]["id"]
    assert world["pcc"].post(f"appeals/{appeal}/assign", {"director_user_id": DIRECTOR}).json()[
        "error"]["code"] == "appeal_same_director"
    assert world["pcc"].post(f"appeals/{appeal}/assign",
                             {"director_user_id": DIRECTOR_2}).status_code == 200
    return pk, appeal


@pytest.mark.parametrize(("outcome", "modified", "status"), [
    ("remand", None, sm.NEEDS_REVISION),              # BW-PMS-03
    ("uphold", None, sm.REJECTION_UPHELD),            # BW-PMS-04
    ("modify", "approve", sm.APPROVED),               # BW-PMS-05
])
# UC-PMS-022 UC-PMS-023 PMS-AFR-167 PMS-AFR-168 PMS-AFR-169 PMS-AFR-170 PMS-AFR-171 CFR-PMS-020
def test_uc_pms_022_023_appeal(world, scanner, outcome, modified, status):
    pk, appeal = _appeal(world)
    r = world["director2"].post(f"appeals/{appeal}/decision", {
        "outcome": outcome, "modified_decision": modified, "note": JUSTIFY})
    assert r.json()["outcome"] == outcome
    assert Application.objects.get(pk=pk).status == status


# UC-PMS-022 BR-PMS-093 PMS-AFR-166
def test_uc_pms_022_late_appeal_is_refused(world, scanner):
    pk = decided(world, "reject")
    with freeze_time(timezone.now() + timedelta(days=31)):
        r = world["applicant"].post(f"applications/{pk}/appeal", {"grounds": "g",
                                                                  "justification": "j"})
    assert r.json()["error"]["code"] == "appeal_period_over"


# -- UC-PMS-024, 031, 032, 028 ----------------------------------------------------------
# UC-PMS-024 PMS-AFR-182 PMS-AFR-188 PMS-AFR-189 PMS-AFR-191 PMS-AFR-237 CFR-PMS-022
def test_uc_pms_024_reports_export_and_schedule(world, scanner):
    submitted(world)
    p = world["pcc"]
    assert p.get("reports/dashboard").json()["rows"][0]["value"] == 1
    export = p.client.get("/api/v1/pms/reports/status/export")
    assert b"PMS-" in b"".join(export.streaming_content)
    d = p.post("report-definitions", {"name": "Weekly", "report_type": "status",
                                      "schedule": "weekly"}).json()
    monday = date(2026, 11, 23)
    assert reports.run_scheduled(today=monday) == 1
    run = ReportRun.objects.get(definition_id=d["id"])
    assert p.client.get(f"/api/v1/pms/report-runs/{run.pk}/download").status_code == 200
    assert AuditEntry.objects.filter(action="report.exported").count() == 2


# UC-PMS-031 UC-PMS-032 BR-PMS-005 BR-PMS-006 PMS-AFR-023 PMS-AFR-187 CFR-PMS-002
def test_uc_pms_031_032_director_reports_and_oversight(world, scanner):
    under_review(world)
    d = world["director"]
    assert d.get("oversight").json()["by_status"]["under_review"] == 1
    assert d.get("reports/workload").json()["rows"] == [
        {"person": "Person 2001", "role": "Director", "open_items": 1}]


# UC-PMS-028 BR-PMS-121 PMS-AFR-207 PMS-AFR-208 PMS-AFR-211 PMS-AFR-213 CFR-PMS-024
def test_uc_pms_028_audit_logs(world, scanner):
    pk = submitted(world)
    rows = world["pcc"].get("audit", {"application": pk}).json()["results"]
    submit = next(r for r in rows if r["action"] == "application.submit")
    assert (submit["actor_user_id"], submit["application_id"], submit["from_state"],
            submit["to_state"]) == (1001, pk, "draft", "submitted")
    assert submit["at"]
    assert {r["application_id"] for r in world["director"].get("audit").json()["results"]} \
        == {pk}
    Application.objects.filter(pk=pk).update(domain_code="software")
    assert world["director"].get("audit").json()["results"] == []
    assert world["applicant"].get("audit").status_code == 403


# -- UC-PMS-025, 026 ---------------------------------------------------------------------
# UC-PMS-025 PMS-AFR-027 CFR-PMS-003
def test_uc_pms_025_publish_settings(world):
    p = world["pcc"]
    current = p.get("policy").json()
    r = p.post("policy", {"based_on_version": current["version"],
                          "payload": {**current["payload"], "cost_threshold": "5000.00"}})
    assert r.status_code == 201 and r.json()["version"] == 2
    stale = p.post("policy", {"based_on_version": 1, "payload": current["payload"]})
    assert stale.json()["error"]["code"] == "policy_stale"


# UC-PMS-026 BR-PMS-042 PMS-AFR-030 PMS-AFR-223
def test_uc_pms_026_attorney_panel(world):
    p = world["pcc"]
    r = p.post("attorney-panel", {"user_id": 1003, "domain_codes": ["software"]})
    assert r.status_code == 201
    entry = next(e for e in r.json() if e["user_id"] == 1003)
    assert p.post(f"attorney-panel/{entry['id']}/end").status_code == 200
    assert all(e["user_id"] != 1003 for e in p.get("attorney-panel").json())


# BR-PMS-116 PMS-AFR-206 CFR-PMS-023
def test_notifications_are_delivered_by_email(world, scanner):
    submitted(world)
    report = notifications.deliver_pending()
    assert report.sent >= 1
    assert ["u1001@example.test"] in [m.to for m in mail.outbox]
