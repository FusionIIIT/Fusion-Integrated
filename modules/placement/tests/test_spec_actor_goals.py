"""The remaining actor goals of the use cases, through the HTTP API."""
from dataclasses import replace
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.placement.models import (
    Announcement,
    Application,
    InterviewRound,
    NotificationOutbox,
    PlacementStatsSnapshot,
)
from modules.placement.services import stats
from modules.placement.tests.test_spec_journeys import (
    API,
    OTHER,
    SEASON,
    STUDENT,
    World,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def world(stub_iam):
    return World(stub_iam)


class TestStudentProfileAndResume:

    def test_student_opens_their_profile_built_from_the_portal_record(self, world):
        # PC-UC-001, PC-AFR-001, PC-AFR-002, PC-AFR-003, PC-BR-025, PC-CFR-001
        body = world.student().get(f"{API}/profile/resume").json()
        assert body["user_id"] == STUDENT
        assert body["profile_completed"] is True
        assert (body["discipline"], body["batch_year"]) == ("CSE", 2023)
        assert set(body["academic"]) >= {"semester", "declared_seq", "computed_by"}
        assert body["academic"]["cpi"] == "8.2"

    def test_student_gets_a_structured_resume_from_profile_data(self, world):
        # PC-UC-023, PC-AFR-005
        world.users[STUDENT] = replace(world.users[STUDENT],
                                       resume_link="https://drive.example/cv")
        body = world.student().get(f"{API}/profile/resume").json()
        assert set(body) >= {"name", "roll_no", "programme", "discipline",
                             "batch_year", "resume_link", "academic"}
        assert body["resume_link"] == "https://drive.example/cv"

    def test_a_student_cannot_open_any_candidate_profile(self, world):
        # PC-UC-001 E2, PC-BR-023: refused for the role, so no id leaks whether it exists.
        c = world.student()
        assert c.get(f"{API}/profiles/{OTHER}").status_code == 403
        assert c.get(f"{API}/profiles/999999").status_code == 403


class TestBrowseAndTrack:

    def test_student_browses_jobs_and_internships_and_never_drafts(self, world):
        # PC-UC-002, PC-AFR-006, PC-AFR-019, PC-CFR-002, PC-CFR-007
        job = world.tpo_publishes()
        intern = world.recruiter.post(f"{API}/postings", world.posting_body(
            kind="internship", title="Intern"), format="json").json()["id"]
        world.recruiter.post(f"{API}/postings/{intern}/publish")
        draft = world.recruiter.post(f"{API}/postings", world.posting_body(title="Draft"),
                                     format="json").json()["id"]
        rows = world.student().get(f"{API}/postings").json()["results"]
        assert {r["id"] for r in rows} == {job, intern}
        assert draft not in {r["id"] for r in rows}
        detail = world.student().get(f"{API}/postings/{job}").json()
        assert detail["description"] and detail["closes_at"] and detail["eligibility_rule"]

    def test_with_no_published_posting_the_list_is_empty(self, world):
        # PC-UC-002 A1
        assert world.student().get(f"{API}/postings").json()["results"] == []

    def test_student_tracks_only_their_own_applications(self, world):
        # PC-UC-004, PC-UC-004 E1, PC-AFR-010, PC-CFR-004
        pid = world.tpo_publishes()
        mine = world.student_applies(pid)
        Application.objects.create(posting_id=pid, user_id=OTHER, status="submitted")
        rows = world.student().get(f"{API}/applications").json()["results"]
        assert [(r["id"], r["status"]) for r in rows] == [(mine, "submitted")]

    def test_a_student_with_no_application_sees_an_empty_history(self, world):
        # PC-UC-004 A1
        assert world.student().get(f"{API}/applications").json()["results"] == []


class TestTpoApplicationManagement:

    def test_tpo_reviews_and_filters_applications_and_moves_one_to_review(self, world):
        # PC-UC-008, PC-BR-010, PC-AFR-023, PC-AFR-024, PC-AFR-025, PC-AFR-009, PC-CFR-003, PC-CFR-008
        pid = world.tpo_publishes()
        app = world.student_applies(pid)
        c = world.tpo()
        rows = c.get(f"{API}/applications?posting={pid}").json()["results"]
        assert [r["id"] for r in rows] == [app]
        r = c.post(f"{API}/applications/{app}/transition", {"to_status": "under_review"},
                   format="json")
        assert r.json()["status"] == "under_review"
        history = c.get(f"{API}/applications/{app}/history").json()["results"]
        assert [h["to_status"] for h in history][-1] == "under_review"

    def test_tpo_tracks_interview_progress(self, world):
        # PC-AFR-029, PC-UC-009 step 5, PC-CFR-009
        pid = world.company_publishes()
        app = world.student_applies(pid)
        world.company_shortlists(app)
        world.schedule(world.tpo(), pid, app)
        rounds = world.tpo().get(f"{API}/interviews/rounds?posting={pid}").json()["results"]
        assert [r["id"] for r in rounds] == list(
            InterviewRound.objects.filter(posting_id=pid).values_list("id", flat=True))


class TestCompanyApplicationReview:

    def test_company_sees_applications_to_its_own_postings(self, world):
        # PC-AFR-046, PC-UC-016 step 2, PC-CFR-015
        pid = world.company_publishes()
        app = world.student_applies(pid)
        rows = world.recruiter.get(f"{API}/applications").json()["results"]
        assert [r["id"] for r in rows] == [app]

    def test_company_records_a_rejection_update_and_it_is_notified(self, world):
        # PC-UC-016 A1, PC-AFR-048, PC-AFR-053, PC-AFR-051
        app = world.student_applies(world.company_publishes())
        r = world.recruiter.post(f"{API}/applications/{app}/transition",
                                 {"to_status": "rejected", "reason": "Not shortlisted."},
                                 format="json")
        assert r.json()["status"] == "rejected"
        topics = set(NotificationOutbox.objects.filter(recipient_user_id=STUDENT)
                     .values_list("topic", flat=True))
        assert {"application.submitted", "application.rejected"} <= topics


class TestAnnouncements:

    def test_tpo_publishes_an_announcement_kept_in_history_and_notified(self, world):
        # PC-UC-020, PC-AFR-040, PC-AFR-043, PC-AFR-056, PC-CFR-013
        c = world.tpo()
        r = c.post(f"{API}/announcements", {"title": "Drive on Monday", "body": "Hall 2.",
                                            "topic": "drive"}, format="json")
        assert r.status_code == 201
        aid = r.json()["id"]
        c.post(f"{API}/announcements/{aid}/withdraw", {"reason": "Moved."}, format="json")
        assert Announcement.objects.filter(pk=aid, is_withdrawn=True).exists()
        assert aid in [a["id"] for a in c.get(f"{API}/announcements").json()["results"]]
        assert NotificationOutbox.objects.filter(topic="announcement.published").exists()

    def test_chairman_publishes_an_official_announcement(self, world):
        # PC-UC-013, PC-AFR-041
        from modules.placement import registry
        c = world._client(user_id=70, kind="faculty", roles=("placement chairman",),
                          active_role="placement chairman",
                          permissions=registry.ROLE_GRANTS["placement chairman"])
        r = c.post(f"{API}/announcements", {"title": "Internship programme",
                                            "body": "Apply by Friday.",
                                            "topic": "workshop"}, format="json")
        assert r.status_code == 201
        assert world.student().get(f"{API}/announcements").json()["results"][0][
            "title"] == "Internship programme"

    def test_an_announcement_outside_the_placement_topics_is_refused(self, world):
        # PC-BR-017, PC-AFR-042, PC-UC-013 E1
        r = world.tpo().post(f"{API}/announcements", {"title": "Mess menu", "body": "x",
                                                      "topic": "mess"}, format="json")
        assert r.status_code in (400, 409)
        assert not Announcement.objects.exists()

    def test_a_student_cannot_publish(self, world):
        # PC-UC-020 E1
        r = world.student().post(f"{API}/announcements", {"title": "x", "body": "y"},
                                 format="json")
        assert r.status_code == 403


class TestStudentStatistics:

    def test_student_sees_anonymised_figures_for_a_past_season(self, world):
        # PC-UC-024, PC-AFR-015, PC-AFR-016, PC-BR-016, PC-CFR-006
        PlacementStatsSnapshot.objects.create(
            policy=world.policy, dimension="overall", registered=10, placed=6,
            companies_participated=2)
        body = world.student().get(f"{API}/stats?season={SEASON}").json()
        assert (body["available"], body["placed"], body["placement_rate"]) == (True, 6, 60.0)
        assert "mean_ctc" not in body

    def test_below_the_small_cell_floor_nothing_is_published(self, world):
        # PC-UC-024 E1
        stats.rebuild(season=SEASON)
        assert world.student().get(f"{API}/stats?season={SEASON}").json()[
            "available"] is False

    def test_the_tpo_sees_the_figure_a_student_cannot(self, world):
        # PC-BR-023, PC-AFR-062
        assert "by_company" in world.tpo().get(f"{API}/stats?season={SEASON}").json()
        assert "by_company" not in world.student().get(f"{API}/stats?season={SEASON}").json()

    def test_an_offer_deadline_defaults_from_the_season(self, world):
        # PC-BR-013: a represented deadline always exists.
        app = world.student_applies(world.company_publishes())
        world.company_shortlists(app)
        offer = world.company_offers(app)
        from modules.placement.models import Offer
        respond_by = Offer.objects.get(pk=offer).respond_by
        assert respond_by > timezone.now() + timedelta(hours=1)
