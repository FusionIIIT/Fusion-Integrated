"""Bulk shortlisting and rejection (PC-UC-008).

A bulk endpoint is the natural place for an authorisation check to go missing,
because it is tempting to write a fast path that updates rows directly. These
tests pin the opposite: every item goes through the same service as a single
transition, so scope, permission, state machine and guards all still apply.

The other property is honesty about partial success — a run that moved 38 of 40
must not report as done.
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from core.api.exceptions import ConflictError
from modules.placement.models import (
    Application,
    ApplicationTransition,
    Company,
    JobPosting,
    PlacementPolicy,
)
from modules.placement.services import applications as service

pytestmark = pytest.mark.django_db

SEASON = "2026-27"
BULK = "/api/v1/placement/applications/bulk-transition"

STAFF_PERMS = (
    "placement_cell.application.view",
    "placement_cell.application.review",
)


def _actor(uid=9, perms=STAFF_PERMS, kind="staff"):
    from fusion_auth.principal import Principal
    return Principal.from_session(
        make_session(user_id=uid, kind=kind, permissions=perms,
                     modules=("placement_cell",)))


def _client(stub_iam, perms=STAFF_PERMS, uid=9, kind="staff"):
    stub_iam(make_session(user_id=uid, kind=kind, modules=("placement_cell",),
                          permissions=perms))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


@pytest.fixture
def world():
    PlacementPolicy.objects.create(season=SEASON, is_active=True)
    company = Company.objects.create(
        name="Acme", slug="acme", status="active",
        approval_status="approved", approved_by_user_id=9)
    posting = JobPosting.objects.create(
        company=company, title="SDE", placement_year=SEASON, description="d",
        status="published", published_at=timezone.now(),
        closes_at=timezone.now() + timedelta(days=7),
        eligibility_rule={}, eligibility_rule_locked_at=timezone.now())
    return company, posting


def submitted(posting, count=3, start=1001):
    return [Application.objects.create(posting=posting, user_id=uid,
                                       status="submitted")
            for uid in range(start, start + count)]


# -- The happy path ----------------------------------------------------------------
class TestBulkMove:

    def test_several_applications_move_at_once(self, stub_iam, world):
        stub_iam()
        _, posting = world
        apps = submitted(posting, 3)

        outcomes = service.bulk_transition(
            application_ids=[a.pk for a in apps], to_status="under_review",
            actor=_actor(), scope=Application.objects.all())

        assert all(o.moved for o in outcomes)
        assert set(Application.objects.values_list("status", flat=True)) == \
            {"under_review"}

    def test_each_move_is_recorded_in_the_audit_trail(self, stub_iam, world):
        """Bulk must not be a way to change state without leaving a trace."""
        stub_iam()
        _, posting = world
        apps = submitted(posting, 3)

        service.bulk_transition(application_ids=[a.pk for a in apps],
                               to_status="under_review", actor=_actor(),
                               scope=Application.objects.all())

        assert ApplicationTransition.objects.filter(
            to_status="under_review").count() == 3

    def test_duplicate_ids_are_collapsed(self, stub_iam, world):
        """A double-clicked checkbox must not attempt the move twice."""
        stub_iam()
        _, posting = world
        app = submitted(posting, 1)[0]

        outcomes = service.bulk_transition(
            application_ids=[app.pk, app.pk, app.pk],
            to_status="under_review", actor=_actor(),
            scope=Application.objects.all())

        assert len(outcomes) == 1


# -- Partial success ----------------------------------------------------------------
class TestPartialSuccess:

    def test_one_refusal_does_not_block_the_rest(self, stub_iam, world):
        """A TPO shortlisting forty candidates should not be stopped because
        one withdrew an hour ago."""
        stub_iam()
        _, posting = world
        good = submitted(posting, 2)
        withdrawn = Application.objects.create(
            posting=posting, user_id=3003, status="withdrawn")

        outcomes = service.bulk_transition(
            application_ids=[good[0].pk, withdrawn.pk, good[1].pk],
            to_status="under_review", actor=_actor(),
            scope=Application.objects.all())

        moved = {o.application_id for o in outcomes if o.moved}
        assert moved == {good[0].pk, good[1].pk}
        withdrawn.refresh_from_db()
        assert withdrawn.status == "withdrawn"

    def test_the_refusal_carries_the_same_reason_a_single_move_would(
            self, stub_iam, world):
        stub_iam()
        _, posting = world
        withdrawn = Application.objects.create(
            posting=posting, user_id=3003, status="withdrawn")

        outcome = service.bulk_transition(
            application_ids=[withdrawn.pk], to_status="under_review",
            actor=_actor(), scope=Application.objects.all())[0]

        assert outcome.moved is False
        assert outcome.code == "invalid_transition"
        assert "withdrawn" in outcome.error

    def test_an_out_of_scope_id_is_refused_not_moved(self, stub_iam, world):
        """The scope is the caller's queryset, exactly as for one item."""
        stub_iam()
        _, posting = world
        theirs = submitted(posting, 1, start=5005)[0]

        outcome = service.bulk_transition(
            application_ids=[theirs.pk], to_status="under_review",
            actor=_actor(), scope=Application.objects.none())[0]

        assert outcome.moved is False
        assert outcome.code == "not_found"


# -- Limits -------------------------------------------------------------------------
class TestLimits:

    def test_an_empty_selection_is_refused(self, stub_iam, world):
        stub_iam()
        with pytest.raises(ConflictError) as exc:
            service.bulk_transition(application_ids=[], to_status="under_review",
                                    actor=_actor())
        assert exc.value.code == "nothing_selected"

    def test_the_batch_is_capped(self, stub_iam, world, monkeypatch):
        """A bulk action is a convenience, not a data-migration tool."""
        stub_iam()
        monkeypatch.setattr(service, "MAX_BULK", 2)
        with pytest.raises(ConflictError) as exc:
            service.bulk_transition(application_ids=[1, 2, 3],
                                    to_status="under_review", actor=_actor())
        assert exc.value.code == "too_many"


# -- Authorisation ------------------------------------------------------------------
class TestBulkGrantsNoShortcut:

    def test_a_reason_is_still_required_for_rejection(self, stub_iam, world):
        """The has_reason guard applies per item, so a bulk reject cannot skip
        the reason a single reject demands."""
        stub_iam()
        _, posting = world
        apps = submitted(posting, 2)

        outcomes = service.bulk_transition(
            application_ids=[a.pk for a in apps], to_status="rejected",
            reason="", actor=_actor(), scope=Application.objects.all())

        assert not any(o.moved for o in outcomes)
        assert {o.code for o in outcomes} == {"reason_required"}

    def test_with_a_reason_the_rejection_goes_through_and_is_stored(
            self, stub_iam, world):
        stub_iam()
        _, posting = world
        apps = submitted(posting, 2)

        service.bulk_transition(
            application_ids=[a.pk for a in apps], to_status="rejected",
            reason="Did not clear the written round", actor=_actor(),
            scope=Application.objects.all())

        assert ApplicationTransition.objects.filter(
            to_status="rejected",
            reason="Did not clear the written round").count() == 2

    def test_a_student_cannot_bulk_move_their_own_applications(self, stub_iam,
                                                              world):
        """`applications_for` returns a student their own rows, so scope alone
        would let this through — the per-item permission check is what stops
        it."""
        stub_iam()
        _, posting = world
        mine = Application.objects.create(posting=posting, user_id=1001,
                                          status="submitted")

        outcomes = service.bulk_transition(
            application_ids=[mine.pk], to_status="shortlisted",
            actor=_actor(uid=1001, kind="student",
                         perms=("placement_cell.application.view_self",)),
            scope=Application.objects.filter(user_id=1001))

        assert outcomes[0].moved is False
        mine.refresh_from_db()
        assert mine.status == "submitted"

    def test_read_only_reporting_staff_cannot_bulk_review(self, stub_iam, world):
        """`report.view` makes them staff for scoping, not for reviewing."""
        stub_iam()
        _, posting = world
        apps = submitted(posting, 2)

        outcomes = service.bulk_transition(
            application_ids=[a.pk for a in apps], to_status="under_review",
            actor=_actor(perms=("placement_cell.report.view",)),
            scope=Application.objects.all())

        assert not any(o.moved for o in outcomes)


# -- HTTP -----------------------------------------------------------------------------
class TestBulkApi:

    def test_the_response_counts_before_it_details(self, stub_iam, world):
        """A partial run must never read as a complete one."""
        _, posting = world
        good = submitted(posting, 2)
        withdrawn = Application.objects.create(
            posting=posting, user_id=3003, status="withdrawn")
        client = _client(stub_iam)

        body = client.post(BULK, {
            "application_ids": [good[0].pk, withdrawn.pk, good[1].pk],
            "to_status": "under_review",
        }, format="json").json()

        assert body["moved"] == 2
        assert body["refused"] == 1
        assert len(body["results"]) == 3

    def test_a_student_is_refused_at_the_endpoint(self, stub_iam, world):
        _, posting = world
        app = Application.objects.create(posting=posting, user_id=1001,
                                        status="submitted")
        client = _client(stub_iam, perms=("placement_cell.application.view_self",),
                         uid=1001, kind="student")

        body = client.post(BULK, {
            "application_ids": [app.pk], "to_status": "shortlisted",
        }, format="json").json()

        assert body["moved"] == 0
        app.refresh_from_db()
        assert app.status == "submitted"

    def test_more_than_the_cap_is_refused_by_the_serializer(self, stub_iam,
                                                           world):
        client = _client(stub_iam)
        response = client.post(BULK, {
            "application_ids": list(range(1, 502)), "to_status": "under_review",
        }, format="json")
        assert response.status_code == 400
