"""Each refusal a write can give, with the code a person sees (Step 5.11, error paths)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.pms.domain import state_machine as sm
from modules.pms.models import (
    Appeal,
    AttorneyAssignment,
    Communication,
    DirectorProfile,
    Escalation,
    Inventor,
    LicensingRequest,
    MaintenanceCycle,
    OfficeAction,
    PmsPolicy,
)
from modules.pms.tests.conftest import (
    ATTORNEY,
    CO_INVENTOR,
    DIRECTOR,
    DIRECTOR_2,
    POLICY,
    approved_with_attorney,
    make_app,
    pdf,
    with_budget,
    with_cycle,
)

pytestmark = pytest.mark.django_db
TODAY = timezone.localdate
TEXT = "x" * 60


def code(response):
    return response.json()["error"]["code"]


# -- drafting and inventors -------------------------------------------------------
# BR-PMS-045 PMS-AFR-079
def test_preferred_attorney_must_be_on_the_panel_br_pms_045(world):
    a = world["applicant"]
    assert code(a.post("applications", {"preferred_attorney_user_id": 1003})) \
        == "preference_not_on_panel"
    assert a.post("applications", {"preferred_attorney_user_id": ATTORNEY}).status_code == 201


def test_only_the_applicant_edits_a_draft(world):
    app = make_app(sm.DRAFT)
    Inventor.objects.create(application=app, user_id=CO_INVENTOR, name="C", share_percent=1)
    assert world["co_inventor"].patch(f"applications/{app.pk}",
                                      {"title": "x"}).status_code == 404


def test_an_unchanged_edit_writes_no_audit(world):
    app = make_app(sm.DRAFT)
    r = world["applicant"].patch(f"applications/{app.pk}", {"title": app.title})
    assert r.status_code == 200
    assert not app.audit_entries.filter(action="application.edited").exists()


@pytest.mark.parametrize(("rows", "error"), [
    ([{"user_id": 9999, "share_percent": "100"}], "unknown_person"),
    (["just a name"], "invalid"),
])
def test_bad_inventor_rows_are_refused(world, rows, error):
    app = make_app(sm.DRAFT)
    r = world["applicant"].put(f"applications/{app.pk}/inventors", {"inventors": rows})
    assert r.status_code in (400, 422)
    if r.status_code == 422:
        assert code(r) == error


def test_inventors_cannot_change_after_submission(world):
    app = make_app(sm.SUBMITTED)
    r = world["applicant"].put(f"applications/{app.pk}/inventors", {"inventors": [
        {"user_id": 1001, "share_percent": "100"}]})
    assert code(r) == "not_editable"


def test_a_changed_share_clears_that_inventors_agreement_blueprint_q_9(world):
    app = make_app(sm.DRAFT)
    a = world["applicant"]
    a.put(f"applications/{app.pk}/inventors", {"inventors": [
        {"user_id": 1001, "share_percent": "50"}, {"user_id": CO_INVENTOR,
                                                   "share_percent": "50"}]})
    co = Inventor.objects.get(application=app, user_id=CO_INVENTOR)
    a.post(f"applications/{app.pk}/inventors/{co.pk}/agreement",
           {"agreement_reference": "A", "consent": True})
    a.put(f"applications/{app.pk}/inventors", {"inventors": [
        {"user_id": 1001, "share_percent": "40"}, {"user_id": CO_INVENTOR,
                                                   "share_percent": "60"}]})
    co.refresh_from_db()
    assert co.agreement_completed_at is None
    a.put(f"applications/{app.pk}/inventors", {"inventors": [
        {"user_id": 1001, "share_percent": "100"}]})
    assert not Inventor.objects.filter(pk=co.pk).exists()


def test_agreement_refusals(world):
    app = make_app(sm.DRAFT)
    a = world["applicant"]
    assert code(a.post(f"applications/{app.pk}/inventors/999/agreement",
                       {"agreement_reference": "A", "consent": False})) == "not_found"
    inv = app.inventors.get()
    assert code(a.post(f"applications/{app.pk}/inventors/{inv.pk}/agreement",
                       {"agreement_reference": " ", "consent": False})) \
        == "agreement_reference_required"
    filed = make_app(sm.FILED)
    finv = filed.inventors.get()
    assert code(a.post(f"applications/{filed.pk}/inventors/{finv.pk}/agreement",
                       {"agreement_reference": "A", "consent": True})) == "not_editable"


# -- withdrawal ----------------------------------------------------------------
# BR-PMS-070 PMS-AFR-128
def test_consent_is_required_when_the_setting_says_so_br_pms_070(world):
    PmsPolicy.objects.create(version=2, effective_from=timezone.now(), published_by_user_id=1,
                             payload={**POLICY, "withdrawal_consent_required": True})
    app = make_app(sm.SUBMITTED)
    co = Inventor.objects.create(application=app, user_id=CO_INVENTOR, name="C",
                                 share_percent=1)
    a = world["applicant"]
    assert code(a.post(f"applications/{app.pk}/withdraw", {"reason": "r"})) \
        == "consent_missing"
    r = a.post(f"applications/{app.pk}/withdraw", {"reason": "r",
                                                   "consented_inventor_ids": [co.pk]})
    assert r.json()["status"] == sm.WITHDRAWN


def test_withdrawal_cancels_offers_and_closes_budgets(world):
    app = make_app(sm.APPROVED)
    with_cycle(app, status="decided", decision="approve")
    offer = AttorneyAssignment.objects.create(application=app, attorney_user_id=ATTORNEY,
                                              assigned_by_user_id=1)
    budget = with_budget(app, status=sm.PROPOSED)
    world["applicant"].post(f"applications/{app.pk}/withdraw", {"reason": "r"})
    offer.refresh_from_db()
    budget.refresh_from_db()
    assert offer.status == sm.CANCELLED and budget.status == sm.BUDGET_CLOSED


# -- review and appeals --------------------------------------------------------
def test_unknown_decision_is_refused(world):
    from modules.pms.services import review

    app = make_app(sm.UNDER_REVIEW)
    from core.api.exceptions import DomainError

    with pytest.raises(DomainError) as exc:
        review.decide(actor=world["director"].principal, pk=app.pk, decision="maybe",
                      justification=TEXT)
    assert exc.value.code == "invalid_decision"


def _rejected(world):
    app = make_app(sm.REJECTED, appeal_due_on=TODAY() + timedelta(10),
                   revision_due_on=TODAY() + timedelta(60))
    cycle = with_cycle(app, DIRECTOR, status="decided", decision="reject")
    return app, cycle


def test_appeal_refusals(world):
    app, cycle = _rejected(world)
    appeal = Appeal.objects.create(application=app, rejected_cycle=cycle, grounds="g",
                                   justification="j")
    Appeal.objects.filter(pk=appeal.pk).update(status="decided")
    p, d2 = world["pcc"], world["director2"]
    assert code(p.post("appeals/999/assign", {"director_user_id": DIRECTOR_2})) == "not_found"
    assert code(p.post(f"appeals/{appeal.pk}/assign", {"director_user_id": DIRECTOR_2})) \
        == "appeal_closed"
    assert code(d2.post("appeals/999/decision", {"outcome": "uphold", "note": TEXT})) \
        == "not_found"
    open_appeal = Appeal.objects.create(application=make_app(sm.APPEAL_SUBMITTED),
                                        rejected_cycle=cycle, grounds="g", justification="j")
    assert code(d2.post(f"appeals/{open_appeal.pk}/decision",
                        {"outcome": "uphold", "note": TEXT})) == "not_assigned"


def test_modify_without_a_new_decision_is_refused(world):
    app, cycle = _rejected(world)
    Appeal.objects.create(application=app, rejected_cycle=cycle, grounds="g", justification="j",
                          director_user_id=DIRECTOR_2)
    app.status = sm.APPEAL_SUBMITTED
    app.save()
    appeal = app.appeals.get()
    r = world["director2"].post(f"appeals/{appeal.pk}/decision",
                                {"outcome": "modify", "note": TEXT})
    assert code(r) == "modified_decision_required"
    r = world["director2"].post(f"appeals/{appeal.pk}/decision", {
        "outcome": "modify", "modified_decision": "needs_revision", "note": TEXT})
    assert r.json()["modified_decision"] == "needs_revision"
    app.refresh_from_db()
    assert app.status == sm.NEEDS_REVISION and app.revision_due_on is not None


def test_conflicted_appeal_director_refused(world):
    app, cycle = _rejected(world)
    Inventor.objects.create(application=app, user_id=DIRECTOR_2, name="D", share_percent=1)
    appeal = Appeal.objects.create(application=app, rejected_cycle=cycle, grounds="g",
                                   justification="j", director_user_id=DIRECTOR_2)
    app.status = sm.APPEAL_SUBMITTED
    app.save()
    assert code(world["director2"].post(f"appeals/{appeal.pk}/decision", {
        "outcome": "uphold", "note": TEXT})) == "director_conflicted"
    from modules.pms.tests.conftest import PCC

    Inventor.objects.create(application=app, user_id=PCC, name="P", share_percent=1)
    assert code(world["pcc"].post(f"appeals/{appeal.pk}/assign",
                                  {"director_user_id": DIRECTOR})) == "pcc_admin_conflicted"


# -- attorneys and rosters -------------------------------------------------------
# BR-PMS-040 BR-PMS-127 PMS-AFR-217
def test_attorney_assignment_refusals(world):
    p = world["pcc"]
    early = make_app(sm.UNDER_REVIEW)
    assert code(p.post(f"applications/{early.pk}/assign-attorney",
                       {"attorney_user_id": ATTORNEY})) == "not_approved"
    taken = approved_with_attorney()
    taken.status = sm.APPROVED
    taken.save()
    assert code(p.post(f"applications/{taken.pk}/assign-attorney",
                       {"attorney_user_id": ATTORNEY})) == "assignment_exists"
    assert code(world["attorney"].post("attorney-assignments/999/respond",
                                       {"accept": True})) == "not_found"
    offer = AttorneyAssignment.objects.create(application=make_app(sm.APPROVED),
                                              attorney_user_id=ATTORNEY,
                                              assigned_by_user_id=1)
    assert code(world["attorney"].post(f"attorney-assignments/{offer.pk}/respond",
                                       {"accept": False})) == "reason_required"


def test_roster_refusals(world):
    p = world["pcc"]
    assert code(p.post("directors", {"user_id": 9999, "domain_codes": ["materials"]})) \
        == "unknown_person"
    assert code(p.post("directors", {"user_id": DIRECTOR, "domain_codes": []})) \
        == "areas_required"
    assert code(p.post("directors", {"user_id": DIRECTOR, "domain_codes": ["alchemy"]})) \
        == "unknown_area"
    assert code(p.post("directors/999/end")) == "not_found"
    entry = DirectorProfile.objects.get(user_id=DIRECTOR)
    assert p.post(f"directors/{entry.pk}/end").status_code == 200
    assert code(p.post(f"directors/{entry.pk}/end")) == "already_ended"
    r = p.post("directors", {"user_id": DIRECTOR_2, "domain_codes": ["software"]})
    assert r.status_code == 201
    assert DirectorProfile.objects.filter(user_id=DIRECTOR_2).count() == 2


# -- legal work and budget --------------------------------------------------------
def test_legal_refusals(world):
    app = approved_with_attorney()
    t = world["attorney"]
    assert t.post(f"applications/{app.pk}/assessments",
                  {"recommendation": "maybe"}).status_code == 400
    assert code(t.post(f"applications/{app.pk}/assessments",
                       {"assessment_id": 999})) == "not_found"
    aid = t.post(f"applications/{app.pk}/assessments", {
        "analysis": "a", "novelty": "n", "non_obviousness": "o", "utility": "u",
        "recommendation": "do_not_file"}).json()["assessments"][0]["id"]
    assert t.post(f"assessments/{aid}/finalize").status_code == 200
    assert code(t.post(f"assessments/{aid}/finalize")) == "assessment_final"
    assert code(t.post(f"applications/{app.pk}/assessments",
                       {"assessment_id": aid})) == "assessment_final"
    assert code(t.post("assessments/999/finalize")) == "not_found"
    assert code(t.post(f"applications/{app.pk}/legal-requests",
                       {"kind": "information", "message": " "})) == "message_required"
    assert code(t.post(f"applications/{app.pk}/legal-advice", {"advice": ""})) \
        == "advice_required"
    early = make_app(sm.APPROVED)
    AttorneyAssignment.objects.create(application=early, attorney_user_id=ATTORNEY,
                                      assigned_by_user_id=1, status=sm.ACCEPTED)
    assert code(t.post(f"applications/{early.pk}/legal-advice", {"advice": "a"})) \
        == "case_not_active"


def test_budget_refusals(world):
    app = approved_with_attorney()
    t, d = world["attorney"], world["director"]
    with_budget(app, status=sm.PROPOSED)
    assert code(t.post(f"applications/{app.pk}/budgets", {
        "filing_fee": "1", "attorney_fee": "1", "admin_cost": "1"})) == "budget_open"
    other = approved_with_attorney()
    with_budget(other)
    assert code(t.post(f"applications/{other.pk}/budgets", {
        "filing_fee": "1", "attorney_fee": "1", "admin_cost": "1"})) == "budget_already_approved"
    open_budget = app.budgets.get()
    assert code(world["director2"].post(f"budgets/{open_budget.pk}/decision",
                                        {"approve": True})) in ("not_found", "not_assigned")
    assert code(d.post("budgets/999/decision", {"approve": True})) == "not_found"
    PmsPolicy.objects.create(version=2, effective_from=timezone.now(), published_by_user_id=1,
                             payload={**POLICY, "cost_threshold": None})
    assert code(d.post(f"budgets/{open_budget.pk}/decision", {"approve": True})) \
        == "budget_threshold_missing"


def test_budget_escalation_refusals(world):
    app = approved_with_attorney()
    b = with_budget(app, status=sm.ESCALATED, total="200000")
    p = world["pcc"]
    assert code(p.post(f"budgets/{b.pk}/route", {"routed_to": " "})) == "target_required"
    assert code(p.post(f"budgets/{b.pk}/external-decision", {
        "approved": True, "reference": "R", "decided_on": str(TODAY())})) \
        == "invalid_transition"
    assert p.post(f"budgets/{b.pk}/route", {"routed_to": "FC"}).status_code == 200
    assert code(p.post(f"budgets/{b.pk}/external-decision", {
        "approved": False, "reference": " ", "decided_on": str(TODAY())})) \
        == "reference_required"
    assert code(p.post(f"budgets/{b.pk}/external-decision", {
        "approved": False, "reference": "R",
        "decided_on": str(TODAY() + timedelta(1))})) == "date_in_future"
    assert p.post(f"budgets/{b.pk}/external-decision", {
        "approved": False, "reference": "R", "decided_on": str(TODAY())}).json()[
        "status"] == "external_rejected"


# BR-PMS-052 PMS-AFR-096
def test_budget_cannot_be_proposed_before_approval(world):
    app = make_app(sm.UNDER_REVIEW)
    AttorneyAssignment.objects.create(application=app, attorney_user_id=ATTORNEY,
                                      assigned_by_user_id=1, status=sm.ACCEPTED)
    assert code(world["attorney"].post(f"applications/{app.pk}/budgets", {
        "filing_fee": "1", "attorney_fee": "1", "admin_cost": "1"})) == "budget_not_allowed"


# -- filing and post-filing --------------------------------------------------------
def test_filing_refusals(world):
    app = approved_with_attorney()
    with_budget(app)
    t = world["attorney"]
    body = {"jurisdiction": "IN", "office_name": "IPO", "external_filing_id": "IN100",
            "filing_date": str(TODAY()), "confirmation_reference": "c"}
    assert code(t.post(f"applications/{app.pk}/filings", {**body, "office_name": " "})) \
        == "office_required"
    assert t.post(f"applications/{app.pk}/filings", body).status_code == 200
    assert code(t.post(f"applications/{app.pk}/filings", body)) == "filing_duplicate"
    second = {**body, "jurisdiction": "EP", "external_filing_id": "EP100",
              "international_justification": "Europe market."}
    assert t.post(f"applications/{app.pk}/filings", second).status_code == 200
    early = make_app(sm.APPROVED)
    AttorneyAssignment.objects.create(application=early, attorney_user_id=ATTORNEY,
                                      assigned_by_user_id=1, status=sm.ACCEPTED)
    assert code(t.post(f"applications/{early.pk}/filings", body)) == "filing_not_allowed"


# BR-PMS-142 PMS-AFR-232
def test_communication_refusals(world):
    app = approved_with_attorney()
    app.status = sm.FILED
    app.save()
    t = world["attorney"]
    base = {"received_on": str(TODAY()), "reference": "R"}
    assert code(t.post(f"applications/{app.pk}/communications",
                       {**base, "kind": "other", "reference": ""})) == "reference_required"
    assert code(t.post(f"applications/{app.pk}/communications", {
        **base, "kind": "other", "received_on": str(TODAY() + timedelta(1))})) \
        == "date_in_future"
    assert code(t.post(f"applications/{app.pk}/communications", {**base, "kind": "grant"})) \
        == "grant_date_required"
    assert code(t.post(f"applications/{app.pk}/communications", {
        **base, "kind": "grant", "grant_date": str(TODAY())})) == "patent_number_required"
    assert code(t.post(f"applications/{app.pk}/communications", {
        **base, "kind": "grant", "grant_date": str(TODAY()), "patent_number": "P",
        "jurisdiction": "US"})) == "jurisdiction_not_filed"
    assert t.post(f"applications/{app.pk}/communications",
                  {**base, "kind": "refusal"}).json()["status"] == sm.REFUSED
    pre = approved_with_attorney()
    assert code(t.post(f"applications/{pre.pk}/communications",
                       {**base, "kind": "office_action"})) == "communication_not_allowed"


def _office_action(app, review=False, due=None):
    comm = Communication.objects.create(application=app, kind="office_action",
                                        received_on=TODAY(), reference="FER",
                                        recorded_by_user_id=ATTORNEY)
    return OfficeAction.objects.create(communication=comm, application=app,
                                       requires_applicant_review=review, response_due_on=due)


# BR-PMS-065 PMS-AFR-121 PMS-AFR-123
def test_office_action_refusals(world):
    app = approved_with_attorney()
    app.status = sm.FILED
    app.save()
    oa = _office_action(app, due=TODAY() - timedelta(days=1))
    t = world["attorney"]
    assert code(t.post("office-actions/999/response", {"draft": "d"})) == "not_found"
    assert code(t.post(f"office-actions/{oa.pk}/response", {"draft": " "})) == "draft_required"
    t.post(f"office-actions/{oa.pk}/response", {"draft": "d"})
    assert code(t.post(f"office-actions/{oa.pk}/submission", {
        "submitted_on": str(TODAY()), "reference": "R"})) == "response_deadline_missed"
    assert code(t.post(f"office-actions/{oa.pk}/submission", {
        "submitted_on": str(TODAY()), "reference": ""})) == "reference_required"
    t.post(f"office-actions/{oa.pk}/extension", {"new_due_on": str(TODAY() + timedelta(9)),
                                                 "reason": "office granted"})
    assert t.post(f"office-actions/{oa.pk}/submission", {
        "submitted_on": str(TODAY()), "reference": "R"}).json()["status"] == "submitted"
    assert code(t.post(f"office-actions/{oa.pk}/extension", {
        "new_due_on": str(TODAY() + timedelta(30)), "reason": "r"})) == "already_submitted"


# BR-PMS-059 BR-PMS-061 PMS-AFR-109 PMS-AFR-110
def test_maintenance_refusals(world):
    app = approved_with_attorney()
    t = world["attorney"]
    assert code(t.post(f"applications/{app.pk}/maintenance-cycles",
                       {"due_on": str(TODAY() + timedelta(9))})) == "not_granted"
    app.status, app.grant_date, app.patent_number = sm.GRANTED, TODAY(), "P1"
    app.grant_jurisdiction = "IN"
    app.save()
    assert code(t.post(f"applications/{app.pk}/maintenance-cycles",
                       {"due_on": str(TODAY())})) == "date_not_future"
    r = t.post(f"applications/{app.pk}/maintenance-cycles",
               {"due_on": str(TODAY() + timedelta(9))})
    assert r.json()["source"] == "manual"
    assert code(t.post(f"applications/{app.pk}/maintenance-cycles",
                       {"due_on": str(TODAY() + timedelta(19))})) == "cycle_open"
    cycle = MaintenanceCycle.objects.get(application=app)
    assert code(t.post("maintenance-cycles/999/request-decision")) == "not_found"
    t.post(f"maintenance-cycles/{cycle.pk}/request-decision")
    assert code(world["director2"].post(f"maintenance-cycles/{cycle.pk}/decision",
                                        {"renew": True})) in ("not_found", "not_assigned")
    assert code(world["pcc"].post(f"maintenance-cycles/{cycle.pk}/reassign",
                                  {"director_user_id": DIRECTOR_2})) == "decider_active"
    MaintenanceCycle.objects.filter(pk=cycle.pk).update(due_on=TODAY() - timedelta(1))
    assert code(world["director"].post(f"maintenance-cycles/{cycle.pk}/decision",
                                       {"renew": True})) == "renewal_deadline_passed"
    MaintenanceCycle.objects.filter(pk=cycle.pk).update(due_on=TODAY() + timedelta(9))
    world["director"].post(f"maintenance-cycles/{cycle.pk}/decision", {"renew": True})
    assert code(t.post(f"maintenance-cycles/{cycle.pk}/action", {
        "reference": "", "amount": "1", "actioned_on": str(TODAY())})) == "reference_required"
    assert code(t.post(f"maintenance-cycles/{cycle.pk}/action", {
        "reference": "R", "amount": "1", "actioned_on": str(TODAY() + timedelta(1))})) \
        == "date_in_future"
    r = t.post(f"maintenance-cycles/{cycle.pk}/action", {
        "reference": "R", "amount": "1", "actioned_on": str(TODAY())})
    assert r.json()["status"] == sm.RENEWED


def test_conflicted_pcc_cannot_reassign_renewal(world):
    from modules.pms.tests.conftest import PCC

    app = approved_with_attorney()
    app.status, app.grant_date, app.patent_number = sm.GRANTED, TODAY(), "P1"
    app.save()
    Inventor.objects.create(application=app, user_id=PCC, name="P", share_percent=1)
    cycle = MaintenanceCycle.objects.create(application=app, seq=1, source="manual",
                                            due_on=TODAY() + timedelta(9),
                                            status=sm.DECISION_REQUESTED)
    assert code(world["pcc"].post(f"maintenance-cycles/{cycle.pk}/reassign",
                                  {"director_user_id": DIRECTOR_2})) == "pcc_admin_conflicted"


# -- documents and prior art ---------------------------------------------------------
# BR-PMS-087 BR-PMS-140 PMS-AFR-157 PMS-AFR-230
def test_document_refusals(world, scanner):
    app = make_app(sm.DRAFT)
    a = world["applicant"]
    upload = {"file": pdf(), "kind": "claims", "title": " ", "sensitivity": "restricted"}
    assert code(a.post(f"applications/{app.pk}/documents", upload, fmt="multipart")) \
        == "title_required"
    assert code(a.post(f"applications/{app.pk}/documents",
                       {"file": pdf(), "document_id": 999}, fmt="multipart")) == "not_found"
    assert a.post("applications/999/documents", {**upload, "file": pdf(), "title": "t"},
                  fmt="multipart").status_code == 404
    submitted = make_app(sm.SUBMITTED)
    assert code(a.post(f"applications/{submitted.pk}/documents",
                       {**upload, "file": pdf(), "title": "t"},
                       fmt="multipart")) == "upload_not_allowed"
    empty = {"file": pdf(content=b""), "kind": "claims", "title": "t",
             "sensitivity": "restricted"}
    assert a.post(f"applications/{app.pk}/documents", empty, fmt="multipart").status_code \
        in (400, 422)


def test_sensitivity_changes(world):
    app = make_app(sm.SUBMITTED)
    doc = app.documents.get()
    p = world["pcc"]
    assert code(p.patch("documents/999", {"sensitivity": "restricted"})) == "not_found"
    assert code(p.patch(f"documents/{doc.pk}", {"sensitivity": "public_internal"})) \
        == "unchanged"
    assert p.patch(f"documents/{doc.pk}", {"sensitivity": "restricted"}).json()[
        "sensitivity"] == "restricted"


def test_a_missing_stored_file_is_404_not_500(world, scanner):
    app = make_app(sm.SUBMITTED)
    version = app.documents.get().versions.get()
    assert code(world["applicant"].get(f"documents/versions/{version.pk}/download")) \
        == "file_missing"


def test_prior_art_refusals(world):
    app = make_app(sm.DRAFT)
    a = world["applicant"]
    assert code(a.post("prior-art/searches", {"query": " "})) == "query_required"
    base = {"kind": "patent", "title": "T"}
    assert code(a.post(f"applications/{app.pk}/prior-art", {**base, "title": ""})) \
        == "title_required"
    assert code(a.post(f"applications/{app.pk}/prior-art", {**base, "url": "ftp://x"})) \
        == "invalid_url"
    assert code(a.post(f"applications/{app.pk}/prior-art", {**base, "search_id": 999})) \
        == "not_found"
    sid = a.post("prior-art/searches", {"query": "anything"}).json()["search_id"]
    assert a.post(f"applications/{app.pk}/prior-art", {**base, "identifier": "US9",
                                                       "search_id": sid}).status_code == 201
    assert code(a.post(f"applications/{app.pk}/prior-art", {**base, "identifier": "US9"})) \
        == "reference_exists"
    assert code(world["pcc"].post(f"applications/{make_app(sm.SUBMITTED).pk}/prior-art",
                                  base)) in ("attach_not_allowed", "permission_denied")


# -- licensing, settings, escalations ----------------------------------------------
def test_licensing_refusals(world):
    a, p = world["applicant"], world["pcc"]
    draft = make_app(sm.DRAFT)
    assert code(a.post("licensing-requests", {"application_id": draft.pk,
                                              "kind": "licensing", "summary": "s"})) \
        == "application_draft"
    PmsPolicy.objects.create(version=2, effective_from=timezone.now(), published_by_user_id=1,
                             payload={**POLICY, "licensing_route": None})
    app = make_app(sm.FILED)
    req = a.post("licensing-requests", {"application_id": app.pk, "kind": "licensing",
                                        "summary": "s"}).json()
    assert req["status"] == "submitted"
    assert code(p.post(f"licensing-requests/{req['id']}/route")) == "licensing_route_missing"
    assert code(p.post("licensing-requests/999/route")) == "not_found"
    assert code(p.post(f"licensing-requests/{req['id']}/notes", {"note": " "})) \
        == "note_required"
    PmsPolicy.objects.create(version=3, effective_from=timezone.now(), published_by_user_id=1,
                             payload={**POLICY, "licensing_route": {
                                 "kind": "director", "director_user_id": DIRECTOR}})
    assert p.post(f"licensing-requests/{req['id']}/route").json()["status"] == "routed"
    d = world["director"]
    d.post(f"licensing-requests/{req['id']}/notes", {"note": "n"})
    body = {"counterparty": "", "signed_on": str(TODAY()), "terms_summary": "t"}
    assert code(d.post(f"licensing-requests/{req['id']}/agreement", body)) == "party_required"
    assert code(d.post(f"licensing-requests/{req['id']}/agreement",
                       {**body, "counterparty": "C", "terms_summary": ""})) == "terms_required"
    assert code(d.post(f"licensing-requests/{req['id']}/agreement", {
        **body, "counterparty": "C", "signed_on": str(TODAY() + timedelta(1))})) \
        == "date_in_future"
    assert LicensingRequest.objects.get(pk=req["id"]).status == sm.NEGOTIATING


def test_settings_refusals(world):
    p = world["pcc"]
    current = p.get("policy").json()
    bad = {**current["payload"], "pcc_contact_user_id": 9999}
    assert code(p.post("policy", {"based_on_version": current["version"], "payload": bad})) \
        == "unknown_person"
    assert code(p.post("policy", {"based_on_version": current["version"],
                                  "payload": {**current["payload"], "appeal_period_days": 0}})) \
        == "invalid_policy"
    assert p.get("setup").json()["gaps"] == []


def test_escalation_handling(world):
    app = make_app(sm.UNDER_REVIEW)
    case = Escalation.objects.create(kind="missed_review", application=app, subject_id=1)
    p = world["pcc"]
    assert code(p.post(f"escalations/{case.pk}/handle", {"action": "route", "note": ""})) \
        == "note_required"
    assert p.post(f"escalations/{case.pk}/handle", {
        "action": "route", "note": "Sent to Dean."}).json()["status"] == "routed"
    assert code(p.post(f"escalations/{case.pk}/handle", {
        "action": "route", "note": "again"})) == "escalation_closed"
    assert p.get("escalations", {"status": "routed"}).json()[0]["id"] == case.pk
    assert p.get("escalations", {"status": "bogus"}).status_code == 400
    assert p.post(f"escalations/{case.pk}/handle", {
        "action": "resolve", "note": "Done."}).json()["status"] == "resolved"
    from modules.pms.services import escalations as svc
    from modules.pms.services.base import InvalidRequest

    with pytest.raises(InvalidRequest):
        svc.handle(actor=p.principal, escalation_id=case.pk, action="delete", note="x")


def test_report_definition_refusals(world):
    p = world["pcc"]
    assert code(p.post("report-definitions", {"name": " ", "report_type": "status",
                                              "schedule": "none"})) == "name_required"
    d = p.post("report-definitions", {"name": "N", "report_type": "status",
                                      "schedule": "none"}).json()
    assert p.post(f"report-definitions/{d['id']}/deactivate").json()["active"] is False
    assert code(p.post(f"report-definitions/{d['id']}/deactivate")) == "already_inactive"
    assert code(world["director"].post(f"report-definitions/{d['id']}/deactivate")) \
        == "not_found"
    assert code(p.get("report-runs/999/download")) == "not_found"
    assert p.get("report-definitions").json()[0]["name"] == "N"
