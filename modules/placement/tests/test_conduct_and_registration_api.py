"""Season registration (the configured completeness condition) and conduct, over HTTP."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.placement.models import ConductIncident, PlacementRegistration
from modules.placement.tests.test_spec_journeys import API, OTHER, SEASON, STUDENT, World

pytestmark = pytest.mark.django_db


@pytest.fixture
def world(stub_iam):
    w = World(stub_iam)
    w.policy.registration_closes_on = timezone.localdate() + timedelta(days=10)
    w.policy.save()
    return w


class TestRegistration:

    def test_student_reads_terms_registers_and_lists_their_registration(self, world):
        PlacementRegistration.objects.filter(user_id=STUDENT).delete()
        c = world.student()
        assert c.get(f"{API}/registrations/terms?season={SEASON}").json()["route"] == "open"
        assert c.post(f"{API}/registrations", {"season": SEASON},
                      format="json").status_code == 201
        rows = c.get(f"{API}/registrations").json()["results"]
        assert [r["status"] for r in rows] == ["registered"]

    def test_terms_without_a_season_is_400(self, world):
        assert world.student().get(f"{API}/registrations/terms").status_code == 400

    def test_student_opts_out(self, world):
        r = world.student().post(f"{API}/registrations/opt-out",
                                 {"season": SEASON, "reason": "Higher studies."},
                                 format="json")
        assert r.status_code == 200
        assert r.json()["status"] != "registered"

    def test_office_approves_a_late_registration_and_a_reregistration(self, world):
        PlacementRegistration.objects.filter(user_id=OTHER).delete()
        c = world.tpo()
        r = c.post(f"{API}/registrations/approve-late",
                   {"season": SEASON, "user_id": OTHER, "fee_reference": "CH-1"},
                   format="json")
        assert r.status_code == 200
        assert r.json()["status"] == "registered"
        PlacementRegistration.objects.filter(user_id=OTHER).update(status="opted_out")
        r = c.post(f"{API}/registrations/re-register",
                   {"season": SEASON, "user_id": OTHER, "fee_reference": "CH-2"},
                   format="json")
        assert r.status_code == 200

    def test_a_student_cannot_approve_registrations(self, world):
        r = world.student().post(f"{API}/registrations/approve-late",
                                 {"season": SEASON, "user_id": STUDENT,
                                  "fee_reference": "x"}, format="json")
        assert r.status_code == 403


class TestConduct:

    def test_office_records_waives_sanctions_and_lifts(self, world):
        c = world.tpo()
        r = c.post(f"{API}/conduct/incidents", {
            "season": SEASON, "user_id": STUDENT, "kind": "consent_failure",
            "note": "Absent from the test."}, format="json")
        assert r.status_code == 201
        incident = r.json()["incident"]["id"]
        assert r.json()["recommendation"]["sanction"]
        rows = c.get(f"{API}/conduct/incidents?user_id={STUDENT}").json()["results"]
        assert [x["id"] for x in rows] == [incident]
        waived = c.post(f"{API}/conduct/incidents/{incident}/waive",
                        {"reason": "Wrote in advance."}, format="json")
        assert waived.status_code == 200
        assert ConductIncident.objects.get(pk=incident).waived_at is not None
        barred = c.post(f"{API}/conduct/sanctions", {
            "season": SEASON, "user_id": STUDENT, "sanction": "bar_season",
            "rule": "21", "reason": "Misconduct."}, format="json")
        assert barred.status_code == 200
        lifted = c.post(f"{API}/conduct/sanctions/lift", {
            "season": SEASON, "user_id": STUDENT, "reason": "Appeal upheld."},
            format="json")
        assert lifted.status_code == 200
        assert lifted.json()["status"] == "registered"

    def test_student_reads_their_own_conduct_record(self, world):
        world.tpo().post(f"{API}/conduct/incidents", {
            "season": SEASON, "user_id": STUDENT, "kind": "code_of_conduct",
            "note": "x"}, format="json")
        mine = world.student().get(f"{API}/conduct/mine")
        assert mine.status_code == 200

    def test_a_bad_user_filter_is_400(self, world):
        assert world.tpo().get(f"{API}/conduct/incidents?user_id=abc").status_code == 400

    def test_a_student_cannot_record_an_incident(self, world):
        r = world.student().post(f"{API}/conduct/incidents", {
            "season": SEASON, "user_id": OTHER, "kind": "code_of_conduct", "note": "x"},
            format="json")
        assert r.status_code == 403
        assert not ConductIncident.objects.exists()
