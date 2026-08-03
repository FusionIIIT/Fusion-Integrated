"""Registering for a season (rules 1, 20, 21).

Nothing created a PlacementRegistration before this, so `can_apply` refused
every student with `not_registered` and the application flow was closed in
production. The last test in this file is the one that matters: a student who
registers can then actually apply.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from core.api.exceptions import ConflictError
from modules.placement.domain import registration as rules
from modules.placement.models import (
    Company,
    JobPosting,
    PlacementPolicy,
    PlacementRegistration,
)
from modules.placement.services import registration as service

pytestmark = pytest.mark.django_db

SEASON = "2026-27"
STUDENT = 1001
TODAY = date(2026, 8, 3)


def terms(**season_kw):
    return rules.SeasonTerms(**{"late_fee": 1000, "reregistration_fee": 2000,
                                **season_kw})


# -- The rules, pure ------------------------------------------------------------
class TestRules:

    def test_an_eligible_student_inside_the_window_may_register(self):
        t = rules.assess(terms(closes_on=date(2026, 9, 1)),
                         rules.Applicant(), today=TODAY)
        assert t.route is rules.Route.OPEN

    def test_past_the_deadline_the_route_is_late_not_refused(self):
        """Rule 20 keeps a door open — a fee and the Cell's approval."""
        t = rules.assess(terms(closes_on=date(2026, 7, 1)),
                         rules.Applicant(), today=TODAY)
        assert t.route is rules.Route.LATE
        assert t.fee == 1000
        assert t.allowed

    def test_a_missing_declared_result_refuses_rather_than_passes(self):
        """Same fail-closed rule as the eligibility engine: absence is not a
        pass."""
        t = rules.assess(terms(min_cpi=Decimal("6.0")),
                         rules.Applicant(cpi=None), today=TODAY)
        assert t.route is rules.Route.REFUSED
        assert t.reason == "no_declared_result"

    def test_a_cpi_below_the_minimum_is_refused_with_the_numbers(self):
        t = rules.assess(terms(min_cpi=Decimal("7.0")),
                         rules.Applicant(cpi=Decimal("6.8")), today=TODAY)
        assert t.reason == "cpi_below_minimum"
        assert "6.8" in t.message and "7.0" in t.message

    def test_backlogs_are_only_checked_when_the_season_says_so(self):
        allowed = rules.assess(terms(allow_backlogs=True),
                               rules.Applicant(active_backlogs=2), today=TODAY)
        refused = rules.assess(terms(allow_backlogs=False),
                               rules.Applicant(active_backlogs=2), today=TODAY)
        assert allowed.route is rules.Route.OPEN
        assert refused.reason == "has_backlogs"

    def test_a_de_registered_student_gets_the_reregistration_route(self):
        t = rules.assess(terms(), rules.Applicant(current_status="opted_out"),
                         today=TODAY)
        assert t.route is rules.Route.REREGISTER
        assert t.fee == 2000

    def test_the_reregistration_route_closes_after_one_use(self):
        """Rule 21(ii) — "acceptable only once"."""
        t = rules.assess(
            terms(),
            rules.Applicant(current_status="opted_out", reregistration_count=1),
            today=TODAY)
        assert t.route is rules.Route.REFUSED
        assert t.reason == "reregistration_spent"

    def test_a_permanently_barred_student_has_no_route_at_all(self):
        t = rules.assess(terms(),
                         rules.Applicant(current_status="opted_out",
                                         is_permanently_barred=True),
                         today=TODAY)
        assert t.reason == "barred"

    def test_a_closed_season_refuses_everyone(self):
        assert rules.assess(terms(is_active=False), rules.Applicant(),
                            today=TODAY).reason == "season_closed"


# -- The service ------------------------------------------------------------------
@pytest.fixture
def policy():
    return PlacementPolicy.objects.create(
        season=SEASON, is_active=True,
        registration_closes_on=timezone.localdate() + timedelta(days=30))


def _staff(perms=("placement_cell.registration.manage",), uid=9):
    from fusion_auth.principal import Principal
    return Principal.from_session(
        make_session(user_id=uid, kind="staff", permissions=perms,
                     modules=("placement_cell",)))


class TestRegistering:

    def test_a_student_can_register(self, stub_iam, policy):
        stub_iam()
        reg = service.register(season=SEASON, user_id=STUDENT)
        assert reg.status == "registered"
        assert reg.registered_at is not None

    def test_registering_twice_is_refused_not_duplicated(self, stub_iam, policy):
        stub_iam()
        service.register(season=SEASON, user_id=STUDENT)
        with pytest.raises(ConflictError):
            service.register(season=SEASON, user_id=STUDENT)
        assert PlacementRegistration.objects.count() == 1

    def test_late_registration_needs_a_fee_reference(self, stub_iam, policy):
        """Rule 20 — "a copy of the payment challan/receipt shall be
        submitted"."""
        stub_iam()
        policy.registration_closes_on = timezone.localdate() - timedelta(days=1)
        policy.save()
        with pytest.raises(ConflictError):
            service.approve_late(season=SEASON, user_id=STUDENT,
                                 fee_reference="  ", actor=_staff())

    def test_late_registration_is_recorded_as_late(self, stub_iam, policy):
        stub_iam()
        policy.registration_closes_on = timezone.localdate() - timedelta(days=1)
        policy.save()
        reg = service.approve_late(season=SEASON, user_id=STUDENT,
                                   fee_reference="CH-2026-114", actor=_staff())
        assert reg.status == "registered"
        assert reg.registered_late is True
        assert reg.late_fee_reference == "CH-2026-114"
        assert reg.approved_by_user_id == 9

    def test_late_approval_needs_the_manage_permission(self, stub_iam, policy):
        from core.api.exceptions import PermissionDeniedError
        stub_iam()
        with pytest.raises(PermissionDeniedError):
            service.approve_late(
                season=SEASON, user_id=STUDENT, fee_reference="X",
                actor=_staff(perms=("placement_cell.report.view",)))

    def test_reregistration_is_allowed_once(self, stub_iam, policy):
        stub_iam()
        service.register(season=SEASON, user_id=STUDENT)
        service.opt_out(season=SEASON, user_id=STUDENT, reason="higher studies")

        reg = service.reregister(season=SEASON, user_id=STUDENT,
                                 fee_reference="CH-777", actor=_staff())
        assert reg.status == "registered"
        assert reg.reregistration_count == 1

        service.opt_out(season=SEASON, user_id=STUDENT, reason="again")
        with pytest.raises(ConflictError) as exc:
            service.reregister(season=SEASON, user_id=STUDENT,
                               fee_reference="CH-778", actor=_staff())
        assert exc.value.code == "reregistration_spent"

    def test_a_debarred_student_cannot_opt_out_of_the_debarment(
            self, stub_iam, policy):
        stub_iam()
        service.register(season=SEASON, user_id=STUDENT)
        PlacementRegistration.objects.update(status="debarred")
        with pytest.raises(ConflictError):
            service.opt_out(season=SEASON, user_id=STUDENT)


# -- HTTP ---------------------------------------------------------------------------
class TestRegistrationApi:

    def _client(self, stub_iam, perms=("placement_cell.registration.self",),
                uid=STUDENT):
        stub_iam(make_session(user_id=uid, modules=("placement_cell",),
                              permissions=perms))
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token abc")
        return c

    def test_a_student_registers_themselves(self, stub_iam, policy):
        client = self._client(stub_iam)
        response = client.post("/api/v1/placement/registrations",
                               {"season": SEASON}, format="json")
        assert response.status_code == 201
        assert PlacementRegistration.objects.get().user_id == STUDENT

    def test_the_body_cannot_name_someone_else(self, stub_iam, policy):
        """user_id comes from the credential, or a student registers a peer."""
        client = self._client(stub_iam)
        client.post("/api/v1/placement/registrations",
                    {"season": SEASON, "user_id": 2002}, format="json")
        assert PlacementRegistration.objects.get().user_id == STUDENT

    def test_terms_tell_a_student_what_route_is_open(self, stub_iam, policy):
        client = self._client(stub_iam)
        body = client.get(
            f"/api/v1/placement/registrations/terms?season={SEASON}").json()
        assert body["route"] == "open"
        assert body["allowed"] is True

    def test_a_student_cannot_approve_their_own_late_registration(
            self, stub_iam, policy):
        client = self._client(stub_iam)
        assert client.post("/api/v1/placement/registrations/approve-late", {
            "season": SEASON, "user_id": STUDENT, "fee_reference": "none",
        }, format="json").status_code == 403


# -- The point of all of it ----------------------------------------------------------
def test_a_registered_student_can_actually_apply(stub_iam, policy, user_ref):
    """Before this, `can_apply` refused everyone with `not_registered` because
    no registration could exist. This is the regression guard."""
    from modules.placement.services import applications

    stub_iam(make_session(user_id=STUDENT, modules=("placement_cell",),
                          permissions=("placement_cell.application.create",)),
             users={STUDENT: user_ref(STUDENT)})
    company = Company.objects.create(
        name="Acme", slug="acme", status="active",
        approval_status="approved", approved_by_user_id=9)
    posting = JobPosting.objects.create(
        company=company, title="SDE", placement_year=SEASON, description="d",
        status="published", closes_at=timezone.now() + timedelta(days=7),
        published_at=timezone.now(), eligibility_rule={},
        eligibility_rule_locked_at=timezone.now())

    before = applications.evaluate_for(posting=posting, user_id=STUDENT,
                                       policy=policy)
    assert before["season_decision"]["rule"] == "not_registered"

    service.register(season=SEASON, user_id=STUDENT)

    after = applications.evaluate_for(posting=posting, user_id=STUDENT,
                                      policy=policy)
    assert after["season_decision"]["allowed"] is True
