"""Step 5.11: the questions a malicious insider asks, each pinned by a test."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.pms.domain import state_machine as sm
from modules.pms.models import (
    Application,
    AttorneyAssignment,
    Budget,
    Escalation,
    Inventor,
    MaintenanceCycle,
    ReviewCycle,
)
from modules.pms.tests.conftest import (
    ATTORNEY,
    DIRECTOR,
    DIRECTOR_2,
    PCC,
    Actor,
    approved_with_attorney,
    make_app,
    with_budget,
    with_cycle,
)

pytestmark = pytest.mark.django_db
TEXT = "x" * 60


# BR-PMS-026 BR-PMS-025 PMS-AFR-053 PMS-AFR-054
def test_a_director_cannot_review_their_own_invention_br_pms_026(world):
    app = make_app(sm.SUBMITTED)
    Inventor.objects.create(application=app, user_id=DIRECTOR, name="D", share_percent=1)
    r = world["pcc"].post(f"applications/{app.pk}/assign-director",
                          {"director_user_id": DIRECTOR})
    assert r.json()["error"]["code"] == "director_conflicted"


def test_a_director_added_as_inventor_after_assignment_still_cannot_decide(world):
    app = make_app(sm.UNDER_REVIEW)
    with_cycle(app, DIRECTOR)
    Inventor.objects.create(application=app, user_id=DIRECTOR, name="D", share_percent=1)
    r = world["director"].post(f"applications/{app.pk}/review",
                               {"decision": "approve", "justification": TEXT})
    assert r.json()["error"]["code"] == "director_conflicted"


# BR-PMS-027 PMS-AFR-055
def test_pcc_admin_cannot_assign_their_own_application_br_pms_027(stub_iam, world):
    app = make_app(sm.SUBMITTED, applicant=PCC)
    r = world["pcc"].post(f"applications/{app.pk}/assign-director",
                          {"director_user_id": DIRECTOR})
    assert r.status_code == 403 and r.json()["error"]["code"] == "pcc_admin_conflicted"
    assert Escalation.objects.filter(kind="conflicted_admin", application=app).exists()
    r = world["pcc"].post(f"applications/{app.pk}/assign-attorney",
                          {"attorney_user_id": ATTORNEY})
    assert r.status_code == 403


def test_an_application_never_appears_in_its_applicants_review_queue(stub_iam, world):
    """A Director who is also the applicant gets nothing to review on their own record."""
    app = make_app(sm.SUBMITTED, applicant=DIRECTOR)
    r = world["pcc"].post(f"applications/{app.pk}/assign-director",
                          {"director_user_id": DIRECTOR})
    assert r.json()["error"]["code"] == "director_conflicted"
    assert world["director"].get("my-work").json() == []


# BR-PMS-044 PMS-AFR-078
def test_an_attorney_cannot_be_an_inventor_on_their_case_br_pms_044(world):
    app = make_app(sm.APPROVED)
    with_cycle(app, status="decided", decision="approve")
    Inventor.objects.create(application=app, user_id=ATTORNEY, name="A", share_percent=1)
    r = world["pcc"].post(f"applications/{app.pk}/assign-attorney", {
        "attorney_user_id": ATTORNEY, "exception_reason": "trying to sneak it through"})
    assert r.json()["error"]["code"] == "attorney_conflicted"


# BR-PMS-048
def test_no_negative_budget_component_br_pms_048(world):
    app = approved_with_attorney()
    r = world["attorney"].post(f"applications/{app.pk}/budgets", {
        "filing_fee": "-1", "attorney_fee": "0", "admin_cost": "0"})
    assert r.json()["error"]["code"] == "invalid_amount"
    assert not Budget.objects.exists()


def test_no_unlimited_back_dating_of_dates(world):
    app = approved_with_attorney()
    with_budget(app)
    tomorrow = str(timezone.localdate() + timedelta(days=1))
    r = world["attorney"].post(f"applications/{app.pk}/filings", {
        "jurisdiction": "IN", "office_name": "IPO", "external_filing_id": "IN555",
        "filing_date": tomorrow, "confirmation_reference": "c"})
    assert r.json()["error"]["code"] == "filing_date_in_future"


def test_a_renewal_cannot_go_to_an_inactive_director_c19(world):
    app = make_app(sm.GRANTED, grant_date=timezone.localdate(), patent_number="P1",
                   grant_jurisdiction="IN")
    with_cycle(app, DIRECTOR, status="decided", decision="approve")
    AttorneyAssignment.objects.create(application=app, attorney_user_id=ATTORNEY,
                                      assigned_by_user_id=PCC, status=sm.ACCEPTED)
    cycle = MaintenanceCycle.objects.create(application=app, seq=1, source="manual",
                                            due_on=timezone.localdate() + timedelta(30))
    from modules.pms.models import DirectorProfile

    DirectorProfile.objects.filter(user_id=DIRECTOR).update(valid_to=timezone.now())
    world["attorney"].post(f"maintenance-cycles/{cycle.pk}/request-decision")
    assert Escalation.objects.filter(kind="inactive_renewal_director").exists()
    r = world["pcc"].post(f"maintenance-cycles/{cycle.pk}/reassign",
                          {"director_user_id": DIRECTOR})
    assert r.json()["error"]["code"] == "director_not_eligible"
    r = world["pcc"].post(f"maintenance-cycles/{cycle.pk}/reassign",
                          {"director_user_id": DIRECTOR_2})
    assert r.json()["deciding_director_user_id"] == DIRECTOR_2


def test_a_closed_record_cannot_be_changed(world):
    app = make_app(sm.WITHDRAWN)
    a = world["applicant"]
    assert a.patch(f"applications/{app.pk}", {"title": "new"}).json()["error"]["code"] \
        == "not_editable"
    assert a.post(f"applications/{app.pk}/resubmit", {"responses": {}}).json()["error"][
        "code"] == "invalid_transition"
    assert a.post(f"applications/{app.pk}/withdraw", {"reason": "again"}).json()["error"][
        "code"] == "withdrawal_not_eligible"


def test_the_same_request_twice_takes_effect_once(world):
    app = make_app(sm.UNDER_REVIEW)
    with_cycle(app, DIRECTOR)
    d = world["director"]
    body = {"decision": "approve", "justification": TEXT}
    assert d.post(f"applications/{app.pk}/review", body).status_code == 200
    assert d.post(f"applications/{app.pk}/review", body).json()["error"]["code"] \
        == "invalid_transition"
    assert ReviewCycle.objects.filter(application=app, status="decided").count() == 1


def test_server_owned_fields_in_a_body_are_refused(world):
    a = world["applicant"]
    r = a.post("applications", {"title": "t", "status": "approved", "applicant_user_id": 7})
    assert r.status_code == 400
    assert set(r.json()["error"]["details"][0]) == {"field", "message"}
    assert not Application.objects.exists()


# BR-PMS-031 PMS-AFR-061
def test_a_late_review_decision_is_refused_c10(world):
    app = make_app(sm.UNDER_REVIEW)
    with_cycle(app, DIRECTOR, due=timezone.localdate() - timedelta(days=1))
    r = world["director"].post(f"applications/{app.pk}/review",
                               {"decision": "approve", "justification": TEXT})
    assert r.json()["error"]["code"] == "review_deadline_passed"


def test_reassignment_waits_for_the_deadline(world):
    app = make_app(sm.UNDER_REVIEW)
    with_cycle(app, DIRECTOR)
    r = world["pcc"].post(f"applications/{app.pk}/assign-director",
                          {"director_user_id": DIRECTOR_2})
    assert r.json()["error"]["code"] == "review_still_open"


def test_an_acting_student_who_is_also_pcc_admin_cannot_assign(stub_iam, world):
    both = Actor(stub_iam, 1001, "student", also_holds=("pms_pcc_admin",))
    app = make_app(sm.SUBMITTED, applicant=1003)
    assert both.post(f"applications/{app.pk}/assign-director",
                     {"director_user_id": DIRECTOR}).status_code == 403


@pytest.mark.parametrize(("query", "code"), [
    ({"limit": "abc"}, 400), ({"limit": "0"}, 400), ({"status": "nope"}, 400),
    ({"colour": "red"}, 400), ({"cursor": "%%%"}, 200)])
def test_hostile_query_parameters_are_400_not_500(world, query, code):
    assert world["pcc"].get("applications", query).status_code == code


@pytest.mark.parametrize("query", [{"application": "x"}, {"application": "0"},
                                   {"colour": "red"}])
def test_hostile_audit_filters_are_400(world, query):
    assert world["pcc"].get("audit", query).status_code == 400


def test_huge_and_wrongly_typed_bodies_are_refused(world):
    a = world["applicant"]
    assert a.post("applications", {"title": "x" * 301}).status_code == 400
    app = make_app(sm.DRAFT)
    assert a.put(f"applications/{app.pk}/inventors",
                 {"inventors": "everyone"}).status_code == 400
    assert a.put(f"applications/{app.pk}/inventors", {"inventors": [
        {"user_id": 1001, "share_percent": "lots"}]}).json()["error"]["code"] == "invalid_share"
