"""Every basis and composite workflow, end to end through the HTTP API."""
from datetime import timedelta
from decimal import Decimal as D

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.placement import registry
from modules.placement.models import (
    Application,
    Company,
    NotificationOutbox,
    PlacementPolicy,
    PlacementRecord,
    PlacementRegistration,
)
from modules.placement.tests.test_recruiter_isolation import make_recruiter, recruiter_client

pytestmark = pytest.mark.django_db

API = "/api/v1/placement"
SEASON = "2026-27"
STUDENT, OTHER, TPO = 1001, 1002, 62


def _person(uid, *, complete=True):
    return UserRef(user_id=uid, username=f"s{uid}", display_name=f"Student {uid}",
                   kind="student", discipline="CSE", batch_year=2023,
                   profile_completed=complete)


class World:
    def __init__(self, stub_iam):
        self.stub_iam = stub_iam
        self.users = {STUDENT: _person(STUDENT), OTHER: _person(OTHER, complete=False)}
        self.policy = PlacementPolicy.objects.create(season=SEASON, is_active=True)
        for uid in (STUDENT, OTHER):
            PlacementRegistration.objects.create(policy=self.policy, user_id=uid,
                                                 status="registered",
                                                 registered_at=timezone.now())
        self.company = Company.objects.create(
            name="Acme", slug="acme", status="active", approval_status="approved",
            approved_by_user_id=TPO)
        self.recruiter = recruiter_client(make_recruiter(self.company, "hire@acme.test"))

    def _client(self, **session):
        fake = self.stub_iam(make_session(modules=("placement",), **session),
                             users=self.users)
        fake.standings = {STUDENT: {"cpi": "8.2", "active_backlogs": 0},
                          OTHER: {"cpi": "8.2", "active_backlogs": 0}}
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token abc")
        return c

    def tpo(self):
        return self._client(user_id=TPO, kind="staff", roles=("placement officer",),
                            active_role="placement officer",
                            permissions=registry.ROLE_GRANTS["placement officer"])

    def student(self, uid=STUDENT):
        return self._client(user_id=uid, permissions=registry.ROLE_GRANTS["student"])

    def posting_body(self, **over):
        return {"title": "SDE", "placement_year": SEASON, "kind": "fte",
                "description": "Build things.", "ctc_lpa": "12.00",
                "closes_at": (timezone.now() + timedelta(days=7)).isoformat(),
                "eligibility_rule": {"gte": ["cpi", 7.0]}, **over}

    def tpo_publishes(self):
        c = self.tpo()
        made = c.post(f"{API}/postings", self.posting_body(company_id=self.company.pk),
                      format="json")
        assert made.status_code == 201, made.content
        r = c.post(f"{API}/postings/{made.json()['id']}/publish")
        assert r.json()["status"] == "published"
        return made.json()["id"]

    def company_publishes(self):
        made = self.recruiter.post(f"{API}/postings", self.posting_body(), format="json")
        assert made.status_code == 201, made.content
        r = self.recruiter.post(f"{API}/postings/{made.json()['id']}/publish")
        assert r.json()["status"] == "published"
        return made.json()["id"]

    def company_submits_then_tpo_publishes(self):
        made = self.recruiter.post(f"{API}/postings", self.posting_body(), format="json")
        pid = made.json()["id"]
        r = self.recruiter.post(f"{API}/postings/{pid}/submit")
        assert r.json()["status"] == "pending_approval"
        listed = [p["id"] for p in self.student().get(f"{API}/postings").json()["results"]]
        assert pid not in listed
        assert self.recruiter.post(f"{API}/postings/{pid}/publish").status_code == 409
        assert self.tpo().post(f"{API}/postings/{pid}/publish").json()["status"] == "published"
        return pid

    def student_applies(self, posting_id, uid=STUDENT):
        r = self.student(uid).post(f"{API}/applications/apply",
                                   {"posting_id": posting_id}, format="json")
        assert r.status_code == 201, r.content
        assert r.json()["status"] == "submitted"
        return r.json()["id"]

    def company_shortlists(self, app_id):
        r = self.recruiter.post(f"{API}/applications/{app_id}/transition",
                                {"to_status": "shortlisted"}, format="json")
        assert r.status_code == 200, r.content
        assert r.json()["status"] == "shortlisted"

    def round_body(self, posting_id):
        return {"posting_id": posting_id, "mode": "online",
                "starts_at": (timezone.now() + timedelta(days=2)).isoformat(),
                "ends_at": (timezone.now() + timedelta(days=2, hours=1)).isoformat(),
                "meeting_url": "https://meet.example/r1"}

    def schedule(self, client, posting_id, app_id):
        made = client.post(f"{API}/interviews/rounds", self.round_body(posting_id),
                           format="json")
        assert made.status_code == 201, made.content
        r = client.post(f"{API}/interviews/rounds/{made.json()['id']}/candidates",
                        {"application_ids": [app_id]}, format="json")
        assert r.status_code == 201, r.content
        assert Application.objects.get(pk=app_id).status == "interview_scheduled"

    def company_offers(self, app_id):
        r = self.recruiter.post(f"{API}/offers/issue", {"application_id": app_id},
                                format="json")
        assert r.status_code == 201, r.content
        assert Application.objects.get(pk=app_id).status == "offer_issued"
        return r.json()["id"]

    def student_responds(self, offer_id, accept):
        r = self.student().post(f"{API}/offers/{offer_id}/respond", {"accept": accept},
                                format="json")
        assert r.status_code == 200, r.content
        return r.json()


@pytest.fixture
def world(stub_iam):
    return World(stub_iam)


def _topics():
    return set(NotificationOutbox.objects.values_list("topic", flat=True))


class TestBasisWorkflows:

    def test_bw_pc_01_tpo_publishes_and_an_eligible_student_applies(self, world):
        # PC-UC-006, PC-UC-003, PC-BR-005, PC-AFR-017, PC-AFR-007, BW-PC-01
        world.student_applies(world.tpo_publishes())
        assert {"posting.published", "application.submitted"} <= _topics()

    def test_bw_pc_02_company_publishes_directly_and_a_student_applies(self, world):
        # PC-UC-015 A1, PC-BR-006, PC-AFR-018, BW-PC-02
        world.student_applies(world.company_publishes())

    def test_bw_pc_03_company_submits_tpo_publishes_and_a_student_applies(self, world):
        # PC-UC-015 A2, PC-UC-006 A1, PC-AFR-018, BW-PC-03
        world.student_applies(world.company_submits_then_tpo_publishes())

    def test_bw_pc_04_application_to_company_shortlist(self, world):
        # PC-UC-016, PC-BR-009, PC-AFR-047, PC-AFR-052, BW-PC-04
        app = world.student_applies(world.tpo_publishes())
        world.company_shortlists(app)
        assert "application.shortlisted" in _topics()

    def test_bw_pc_05_shortlist_to_tpo_scheduled_interview(self, world):
        # PC-UC-009, PC-BR-011, PC-BR-012, PC-AFR-026, PC-AFR-054, BW-PC-05
        pid = world.tpo_publishes()
        app = world.student_applies(pid)
        world.company_shortlists(app)
        world.schedule(world.tpo(), pid, app)
        assert "interview.scheduled" in _topics()

    def test_bw_pc_06_company_schedules_the_interview(self, world):
        # PC-UC-021, PC-AFR-027, BW-PC-06
        pid = world.company_publishes()
        app = world.student_applies(pid)
        world.company_shortlists(app)
        world.schedule(world.recruiter, pid, app)

    def test_bw_pc_07_offer_accepted_updates_the_placement_record(self, world):
        # PC-UC-022, PC-UC-005 A1, PC-BR-013, PC-BR-014, PC-AFR-011, PC-AFR-013, PC-AFR-055, BW-PC-07
        app = world.student_applies(world.company_publishes())
        world.company_shortlists(app)
        offer = world.company_offers(app)
        assert world.student_responds(offer, accept=True)["status"] == "accepted"
        record = PlacementRecord.objects.get(user_id=STUDENT, is_active=True)
        assert (record.company_id, record.ctc_lpa) == (world.company.pk, D("12.00"))
        assert Application.objects.get(pk=app).status == "offer_accepted"
        assert "offer.issued" in _topics()

    def test_bw_pc_08_offer_rejected_makes_no_placement_record(self, world):
        # PC-UC-005 A2, PC-AFR-012, BW-PC-08
        app = world.student_applies(world.company_publishes())
        world.company_shortlists(app)
        offer = world.company_offers(app)
        assert world.student_responds(offer, accept=False)["status"] == "declined"
        assert not PlacementRecord.objects.filter(user_id=STUDENT).exists()
        assert Application.objects.get(pk=app).status == "offer_declined"


class TestCompositeWorkflows:

    @pytest.mark.parametrize("path", ["tpo_publishes", "company_publishes",
                                      "company_submits_then_tpo_publishes"])
    def test_cw_pc_01_every_publication_path_leads_to_an_application(self, world, path):
        # CW-PC-01
        world.student_applies(getattr(world, path)())

    @pytest.mark.parametrize("scheduler", ["tpo", "recruiter"])
    def test_cw_pc_02_both_scheduling_paths_reach_interview_scheduled(self, world, scheduler):
        # CW-PC-02
        pid = world.company_publishes()
        app = world.student_applies(pid)
        world.company_shortlists(app)
        client = world.tpo() if scheduler == "tpo" else world.recruiter
        world.schedule(client, pid, app)

    @pytest.mark.parametrize(("accept", "status"), [(True, "offer_accepted"),
                                                    (False, "offer_declined")])
    def test_cw_pc_03_offer_outcome(self, world, accept, status):
        # CW-PC-03
        app = world.student_applies(world.company_publishes())
        world.company_shortlists(app)
        world.student_responds(world.company_offers(app), accept=accept)
        assert Application.objects.get(pk=app).status == status

    def test_cw_pc_04_full_lifecycle_with_interview_before_offer(self, world):
        # PC-AFR-010: the student sees every state on the way., CW-PC-04
        pid = world.company_publishes()
        app = world.student_applies(pid)
        world.company_shortlists(app)
        world.schedule(world.recruiter, pid, app)
        offer = world.company_offers(app)
        world.student_responds(offer, accept=True)
        history = world.student().get(f"{API}/applications/{app}/history").json()
        seen = [h["to_status"] for h in history["results"]]
        assert seen[-4:] == ["shortlisted", "interview_scheduled", "offer_issued",
                             "offer_accepted"]


class TestGuardsOnTheWorkflows:

    def test_pc_br_001_incomplete_profile_blocks_the_application(self, world):
        # PC-UC-003 E1, PC-AFR-004, PC-BR-001
        pid = world.tpo_publishes()
        r = world.student(OTHER).post(f"{API}/applications/apply", {"posting_id": pid},
                                      format="json")
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "profile_incomplete"
        assert not Application.objects.filter(user_id=OTHER, status="submitted").exists()

    def test_pc_br_002_ineligible_student_is_blocked(self, world):
        # PC-UC-003 E2, PC-AFR-008, PC-BR-002
        made = world.tpo().post(f"{API}/postings", world.posting_body(
            company_id=world.company.pk, eligibility_rule={"gte": ["cpi", 9.0]}),
            format="json").json()
        world.tpo().post(f"{API}/postings/{made['id']}/publish")
        r = world.student().post(f"{API}/applications/apply", {"posting_id": made["id"]},
                                 format="json")
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "not_eligible"
        assert not Application.objects.filter(user_id=STUDENT, status="submitted").exists()

    def test_pc_br_003_a_posting_without_a_deadline_cannot_be_published(self, world):
        # PC-UC-006 E1, PC-UC-015 E1, PC-AFR-021, PC-BR-003
        made = world.recruiter.post(f"{API}/postings", world.posting_body(closes_at=None),
                                    format="json").json()
        for action in ("publish", "submit"):
            r = world.recruiter.post(f"{API}/postings/{made['id']}/{action}")
            assert r.status_code == 409
            assert r.json()["error"]["code"] == "incomplete_posting"

    def test_pc_br_004_criteria_use_the_recorded_vocabulary_only(self, world):
        # PC-AFR-020, PC-AFR-022, PC-BR-004
        r = world.tpo().post(f"{API}/postings", world.posting_body(
            company_id=world.company.pk, eligibility_rule={"gte": ["shoe_size", 9]}),
            format="json")
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "invalid_eligibility_rule"
        ok = world.tpo().post(f"{API}/postings", world.posting_body(
            company_id=world.company.pk, eligibility_rule={"all": [
                {"gte": ["cpi", 7]}, {"in": ["discipline", ["CSE"]]},
                {"eq": ["batch_year", 2023]}]}), format="json")
        assert ok.status_code == 201

    def test_pc_br_011_an_interview_needs_date_slot_and_mode(self, world):
        # PC-UC-009 E1, PC-UC-021 E1, PC-AFR-028, PC-BR-011
        pid = world.company_publishes()
        body = world.round_body(pid)
        for missing in ("starts_at", "mode"):
            r = world.tpo().post(f"{API}/interviews/rounds",
                                 {k: v for k, v in body.items() if k != missing},
                                 format="json")
            assert r.status_code == 400
        r = world.tpo().post(f"{API}/interviews/rounds", {**body, "meeting_url": ""},
                             format="json")
        assert r.status_code == 409

    def test_pc_br_013_a_response_after_the_deadline_is_refused(self, world):
        # PC-UC-005 E1, PC-BR-013
        app = world.student_applies(world.company_publishes())
        world.company_shortlists(app)
        offer = world.company_offers(app)
        from modules.placement.models import Offer
        Offer.objects.filter(pk=offer).update(respond_by=timezone.now() - timedelta(minutes=1))
        r = world.student().post(f"{API}/offers/{offer}/respond", {"accept": True},
                                 format="json")
        assert r.status_code == 409
        assert not PlacementRecord.objects.filter(user_id=STUDENT).exists()

    def test_pc_br_009_a_company_cannot_offer_on_another_companys_application(self, world):
        # PC-UC-022 E1, PC-AFR-049, PC-BR-009, PC-CFR-016
        app = world.student_applies(world.tpo_publishes())
        other = Company.objects.create(name="Borg", slug="borg", status="active",
                                       approval_status="approved", approved_by_user_id=TPO)
        borg = recruiter_client(make_recruiter(other, "hire@borg.test"))
        r = borg.post(f"{API}/offers/issue", {"application_id": app}, format="json")
        assert r.status_code == 404
        assert Application.objects.get(pk=app).status == "submitted"

    def test_pc_br_030_a_tpo_filter_does_not_change_a_decision(self, world):
        # PC-UC-008 A1, PC-AFR-024: reading and filtering moves nothing., PC-BR-030
        app = world.student_applies(world.tpo_publishes())
        rows = world.tpo().get(f"{API}/applications?status=submitted").json()["results"]
        assert [r["id"] for r in rows] == [app]
        assert Application.objects.get(pk=app).status == "submitted"
