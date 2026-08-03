"""The debarment ladder (policy rules 18, 19, 21).

The load-bearing property is restraint: the policy says a student "may be"
debarred and leaves the call to the Chairperson, so recording an incident must
never impose a sanction by itself. A system stricter than the signed document
is as wrong as one that is laxer, and here it costs a student a placement.

Rule 19's first tier is also narrower than it looks — the next TWO drives, not
the season — so a season-wide flag would over-punish.
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.placement.domain import conduct
from modules.placement.models import (
    Company,
    ConductIncident,
    JobPosting,
    PlacementPolicy,
    PlacementRegistration,
)
from modules.placement.services import conduct as service

pytestmark = pytest.mark.django_db

SEASON = "2026-27"
STUDENT = 1001
INCIDENTS = "/api/v1/placement/conduct/incidents"
SANCTIONS = "/api/v1/placement/conduct/sanctions"


def _staff(stub_iam, perms=("placement_cell.registration.debar",), uid=9):
    stub_iam(make_session(user_id=uid, kind="staff",
                          modules=("placement_cell",), permissions=perms))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _actor(uid=9, perms=("placement_cell.registration.debar",)):
    from fusion_auth.principal import Principal
    return Principal.from_session(
        make_session(user_id=uid, kind="staff", permissions=perms,
                     modules=("placement_cell",)))


@pytest.fixture
def registration():
    policy = PlacementPolicy.objects.create(season=SEASON, is_active=True)
    return PlacementRegistration.objects.create(
        policy=policy, user_id=STUDENT, status="registered")


def make_posting(company, published_offset_days):
    when = timezone.now() + timedelta(days=published_offset_days)
    return JobPosting.objects.create(
        company=company, title=f"Role {published_offset_days}",
        placement_year=SEASON, description="d", status="published",
        published_at=when, closes_at=when + timedelta(days=30),
        eligibility_rule={}, eligibility_rule_locked_at=when)


# -- The ladder, as pure rules -------------------------------------------------
class TestLadder:

    def test_a_first_consent_failure_bars_two_drives_not_the_season(self):
        """Rule 19 says "the next two campus placement processes". Barring the
        season would be a heavier sanction than the policy authorises."""
        r = conduct.recommend(conduct.IncidentKind.CONSENT_FAILURE,
                              prior_incidents=0)
        assert r.sanction is conduct.Sanction.BAR_NEXT_TWO
        assert r.rule == "19"

    def test_a_repeat_consent_failure_bars_the_season(self):
        r = conduct.recommend(conduct.IncidentKind.CONSENT_FAILURE,
                              prior_incidents=1)
        assert r.sanction is conduct.Sanction.BAR_SEASON

    def test_a_first_conduct_breach_deregisters_with_a_way_back(self):
        """Rule 21 offers re-registration once, on a fee."""
        r = conduct.recommend(conduct.IncidentKind.CODE_OF_CONDUCT,
                              prior_incidents=0)
        assert r.sanction is conduct.Sanction.DEREGISTER

    def test_a_second_conduct_breach_closes_that_route(self):
        r = conduct.recommend(conduct.IncidentKind.CODE_OF_CONDUCT,
                              prior_incidents=1)
        assert r.sanction is conduct.Sanction.BAR_PERMANENT

    def test_unfair_means_skips_the_ladder(self):
        """Rule 18 debars on the first instance."""
        r = conduct.recommend(conduct.IncidentKind.MISREPRESENTATION,
                              prior_incidents=0)
        assert r.sanction is conduct.Sanction.BAR_SEASON
        assert r.rule == "18"

    def test_no_recommendation_is_ever_automatic(self):
        """Every rule reads "may be" or defers to the Chairperson."""
        for kind in conduct.IncidentKind:
            for priors in (0, 1, 5):
                assert conduct.recommend(kind, prior_incidents=priors).automatic \
                    is False

    def test_the_two_drive_bar_is_served_by_sitting_out_two_drives(self):
        bar = conduct.Sanction.BAR_NEXT_TWO
        assert conduct.bars_this_drive(sanction=bar, drives_since_sanction=0)
        assert conduct.bars_this_drive(sanction=bar, drives_since_sanction=1)
        assert not conduct.bars_this_drive(sanction=bar, drives_since_sanction=2)

    def test_a_season_bar_is_never_served(self):
        assert conduct.bars_this_drive(sanction=conduct.Sanction.BAR_SEASON,
                                       drives_since_sanction=99)


# -- Recording ------------------------------------------------------------------
class TestRecording:

    def test_recording_does_not_debar(self, registration):
        """The whole point. The policy leaves the decision to a human."""
        _, rec = service.record(season=SEASON, user_id=STUDENT,
                                kind="consent_failure", note="No-show at Acme",
                                actor=_actor())
        registration.refresh_from_db()
        assert registration.status == "registered"
        assert registration.sanction == ""
        assert rec.sanction is conduct.Sanction.BAR_NEXT_TWO

    def test_the_ladder_counts_from_the_record_not_a_tally(self, registration):
        """A stored counter can drift; the incidents cannot."""
        service.record(season=SEASON, user_id=STUDENT, kind="consent_failure",
                       note="first", actor=_actor())
        _, second = service.record(season=SEASON, user_id=STUDENT,
                                   kind="consent_failure", note="second",
                                   actor=_actor())
        assert second.sanction is conduct.Sanction.BAR_SEASON

    def test_the_two_ladders_escalate_independently(self, registration):
        """A conduct breach must not push a consent failure up a rung."""
        service.record(season=SEASON, user_id=STUDENT, kind="code_of_conduct",
                       note="dress code", actor=_actor())
        _, rec = service.record(season=SEASON, user_id=STUDENT,
                                kind="consent_failure", note="no-show",
                                actor=_actor())
        assert rec.sanction is conduct.Sanction.BAR_NEXT_TWO

    def test_a_waived_incident_stops_counting(self, registration):
        """Rule 19: "in any unavoidable circumstances, the student may inform
        the placement cell in writing"."""
        incident, _ = service.record(season=SEASON, user_id=STUDENT,
                                     kind="consent_failure", note="ill",
                                     actor=_actor())
        service.waive(incident_id=incident.pk, reason="Wrote in advance; ill",
                      actor=_actor())

        _, rec = service.record(season=SEASON, user_id=STUDENT,
                                kind="consent_failure", note="second",
                                actor=_actor())
        assert rec.sanction is conduct.Sanction.BAR_NEXT_TWO

    def test_a_waived_incident_stays_on_the_record(self, registration):
        incident, _ = service.record(season=SEASON, user_id=STUDENT,
                                     kind="consent_failure", note="ill",
                                     actor=_actor())
        service.waive(incident_id=incident.pk, reason="informed in writing",
                      actor=_actor())
        incident.refresh_from_db()
        assert incident.waived is True
        assert incident.waived_by_user_id == 9
        assert ConductIncident.objects.count() == 1

    def test_an_incident_needs_a_note(self, registration):
        with pytest.raises(ConflictError):
            service.record(season=SEASON, user_id=STUDENT,
                           kind="consent_failure", note="   ", actor=_actor())

    def test_recording_needs_the_debar_permission(self, registration):
        with pytest.raises(PermissionDeniedError):
            service.record(season=SEASON, user_id=STUDENT,
                           kind="consent_failure", note="x",
                           actor=_actor(perms=("placement_cell.report.view",)))


# -- Imposing and lifting --------------------------------------------------------
class TestSanctions:

    def test_a_season_bar_marks_the_registration_debarred(self, registration):
        service.apply_sanction(season=SEASON, user_id=STUDENT,
                               sanction="bar_season", rule="19",
                               reason="Second no-show", actor=_actor())
        registration.refresh_from_db()
        assert registration.status == "debarred"
        assert registration.sanctioned_by_user_id == 9

    def test_a_two_drive_bar_leaves_the_student_registered(self, registration):
        """They are still in the season, just sitting out two drives."""
        service.apply_sanction(season=SEASON, user_id=STUDENT,
                               sanction="bar_next_two", rule="19",
                               reason="No-show", actor=_actor())
        registration.refresh_from_db()
        assert registration.status == "registered"
        assert registration.sanction == "bar_next_two"

    def test_a_sanction_needs_a_stated_reason(self, registration):
        with pytest.raises(ConflictError):
            service.apply_sanction(season=SEASON, user_id=STUDENT,
                                   sanction="bar_season", rule="19",
                                   reason="", actor=_actor())

    def test_a_sanction_can_be_lifted(self, registration):
        service.apply_sanction(season=SEASON, user_id=STUDENT,
                               sanction="bar_season", rule="19",
                               reason="No-show", actor=_actor())
        service.lift(season=SEASON, user_id=STUDENT,
                     reason="Appeal upheld", actor=_actor())
        registration.refresh_from_db()
        assert registration.status == "registered"
        assert registration.sanction == ""

    def test_the_student_is_told(self, registration):
        from modules.placement.models import NotificationOutbox

        service.apply_sanction(season=SEASON, user_id=STUDENT,
                               sanction="bar_season", rule="19",
                               reason="No-show", actor=_actor())
        assert NotificationOutbox.objects.filter(
            topic="conduct.sanctioned", recipient_user_id=STUDENT).exists()


# -- The bar against actual drives -----------------------------------------------
class TestDriveScopedBar:

    @pytest.fixture
    def company(self):
        return Company.objects.create(
            name="Acme", slug="acme", status="active",
            approval_status="approved", approved_by_user_id=9)

    def test_the_next_two_drives_are_barred_and_the_third_is_not(
            self, registration, company):
        """Rule 19's first tier, counted against drives rather than days — a
        quiet fortnight should not discharge the sanction."""
        service.apply_sanction(season=SEASON, user_id=STUDENT,
                               sanction="bar_next_two", rule="19",
                               reason="No-show", actor=_actor())
        registration.refresh_from_db()

        first, second, third = (make_posting(company, 1),
                                make_posting(company, 2),
                                make_posting(company, 3))

        assert service.bars_posting(registration, first)
        assert service.bars_posting(registration, second)
        assert not service.bars_posting(registration, third)

    def test_a_drive_published_before_the_sanction_is_untouched(
            self, registration, company):
        """A sanction is not retroactive."""
        earlier = make_posting(company, -5)
        service.apply_sanction(season=SEASON, user_id=STUDENT,
                               sanction="bar_next_two", rule="19",
                               reason="No-show", actor=_actor())
        registration.refresh_from_db()
        assert not service.bars_posting(registration, earlier)

    def test_no_sanction_bars_nothing(self, registration, company):
        assert not service.bars_posting(registration, make_posting(company, 1))


# -- HTTP -------------------------------------------------------------------------
class TestConductApi:

    def test_posting_an_incident_returns_the_recommendation(self, stub_iam,
                                                            registration):
        client = _staff(stub_iam)
        response = client.post(INCIDENTS, {
            "season": SEASON, "user_id": STUDENT,
            "kind": "consent_failure", "note": "No-show at Acme",
        }, format="json")

        assert response.status_code == 201
        body = response.json()
        assert body["recommendation"]["sanction"] == "bar_next_two"
        assert body["recommendation"]["automatic"] is False
        # And nothing was imposed.
        registration.refresh_from_db()
        assert registration.status == "registered"

    def test_a_student_cannot_record_an_incident_against_anyone(
            self, stub_iam, registration):
        client = _staff(stub_iam,
                        perms=("placement_cell.application.view_self",),
                        uid=STUDENT)
        assert client.post(INCIDENTS, {
            "season": SEASON, "user_id": 2002, "kind": "consent_failure",
            "note": "made up", "": "",
        }, format="json").status_code == 403

    def test_a_student_cannot_lift_their_own_sanction(self, stub_iam,
                                                      registration):
        service.apply_sanction(season=SEASON, user_id=STUDENT,
                               sanction="bar_season", rule="19",
                               reason="No-show", actor=_actor())
        client = _staff(stub_iam,
                        perms=("placement_cell.application.view_self",),
                        uid=STUDENT)
        response = client.post("/api/v1/placement/conduct/sanctions/lift", {
            "season": SEASON, "user_id": STUDENT, "reason": "please",
        }, format="json")

        assert response.status_code == 403
        registration.refresh_from_db()
        assert registration.status == "debarred"

    def test_report_view_alone_does_not_grant_debarment(self, stub_iam,
                                                        registration):
        """`report.view` makes someone staff for scoping; sanctioning a student
        is a different authority."""
        client = _staff(stub_iam, perms=("placement_cell.report.view",))
        assert client.post(SANCTIONS, {
            "season": SEASON, "user_id": STUDENT, "sanction": "bar_season",
            "rule": "19", "reason": "x",
        }, format="json").status_code == 403
