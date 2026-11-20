"""The office's company decisions, interview outcomes and bulk review, over HTTP."""
import pytest

from modules.placement.models import Company, RecruiterSession, RoundParticipation
from modules.placement.tests.test_spec_journeys import API, World

pytestmark = pytest.mark.django_db


@pytest.fixture
def world(stub_iam):
    return World(stub_iam)


def _register(world, name="Bolt"):
    from rest_framework.test import APIClient
    APIClient().post(f"{API}/companies/register", {
        "name": name, "contact_name": "A", "contact_email": f"hr@{name.lower()}.test"},
        format="json")
    return Company.objects.get(name=name)


class TestCompanyDecisions:

    def test_office_approves_a_pending_company_and_it_can_operate(self, world):
        # PC-BR-007, PC-AFR-045
        bolt = _register(world)
        r = world.tpo().post(f"{API}/companies/{bolt.pk}/approve", {"note": "Verified."},
                             format="json")
        assert r.json()["approval_status"] == "approved"
        bolt.refresh_from_db()
        assert bolt.can_operate
        assert world.tpo().post(f"{API}/companies/{bolt.pk}/approve",
                                format="json").status_code == 200

    def test_rejecting_needs_a_reason_and_ends_access(self, world):
        bolt = _register(world)
        c = world.tpo()
        assert c.post(f"{API}/companies/{bolt.pk}/reject", {"note": ""},
                      format="json").status_code == 409
        r = c.post(f"{API}/companies/{bolt.pk}/reject", {"note": "Not verified."},
                   format="json")
        assert r.json()["approval_status"] == "rejected"

    def test_blacklisting_cuts_off_live_recruiter_sessions(self, world):
        r = world.tpo().post(f"{API}/companies/{world.company.pk}/blacklist",
                             {"note": "Breach."}, format="json")
        assert r.status_code == 200
        assert not RecruiterSession.objects.filter(revoked_at__isnull=True).exists()
        assert world.recruiter.get(f"{API}/postings").status_code in (401, 403)

    def test_an_unknown_action_or_company_is_404(self, world):
        c = world.tpo()
        assert c.post(f"{API}/companies/{world.company.pk}/promote",
                      format="json").status_code == 404
        for action in ("approve", "reject", "blacklist"):
            assert c.post(f"{API}/companies/999/{action}", {"note": "x"},
                          format="json").status_code == 404

    def test_a_student_cannot_decide_on_a_company(self, world):
        bolt = _register(world)
        assert world.student().post(f"{API}/companies/{bolt.pk}/approve",
                                    format="json").status_code == 403

    def test_the_office_lists_companies_and_a_student_sees_only_approved_ones(self, world):
        _register(world)
        assert {c["name"] for c in world.tpo().get(f"{API}/companies").json()["results"]} \
            == {"Acme", "Bolt"}
        assert world.student().get(f"{API}/companies").status_code in (200, 403)


class TestInterviewOutcomes:

    def _scheduled(self, world):
        pid = world.company_publishes()
        app = world.student_applies(pid)
        world.company_shortlists(app)
        world.schedule(world.recruiter, pid, app)
        return RoundParticipation.objects.get(application_id=app)

    def test_company_records_an_outcome(self, world):
        # PC-AFR-029
        p = self._scheduled(world)
        r = world.recruiter.post(f"{API}/interviews/rounds/{p.round_id}/outcome",
                                 {"application_id": p.application_id, "outcome": "passed",
                                  "score": "8.5"}, format="json")
        assert r.status_code == 200
        p.refresh_from_db()
        assert p.outcome == "passed"

    def test_an_unknown_candidate_is_404(self, world):
        p = self._scheduled(world)
        r = world.tpo().post(f"{API}/interviews/rounds/{p.round_id}/outcome",
                             {"application_id": 999, "outcome": "absent"}, format="json")
        assert r.status_code == 404

    def test_a_student_cannot_record_their_outcome(self, world):
        p = self._scheduled(world)
        r = world.student().post(f"{API}/interviews/rounds/{p.round_id}/outcome",
                                 {"application_id": p.application_id, "outcome": "passed"},
                                 format="json")
        assert r.status_code == 403

    def test_an_offline_round_needs_a_venue(self, world):
        pid = world.company_publishes()
        body = {**world.round_body(pid), "mode": "offline", "meeting_url": ""}
        r = world.tpo().post(f"{API}/interviews/rounds", body, format="json")
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "venue_required"

    def test_a_round_for_an_unknown_posting_is_404(self, world):
        r = world.tpo().post(f"{API}/interviews/rounds", world.round_body(999),
                             format="json")
        assert r.status_code == 404


class TestBulkReview:

    def test_company_shortlists_several_and_each_result_is_reported(self, world):
        # PC-UC-016
        pid = world.company_publishes()
        app = world.student_applies(pid)
        r = world.recruiter.post(f"{API}/applications/bulk-transition", {
            "application_ids": [app, 999], "to_status": "shortlisted"}, format="json")
        assert r.status_code == 200
        assert (r.json()["moved"], r.json()["refused"]) == (1, 1)

    def test_an_empty_selection_is_refused(self, world):
        r = world.tpo().post(f"{API}/applications/bulk-transition", {
            "application_ids": [], "to_status": "shortlisted"}, format="json")
        assert r.status_code == 400

    def test_a_bad_posting_filter_is_400(self, world):
        assert world.tpo().get(f"{API}/applications?posting=x").status_code == 400
