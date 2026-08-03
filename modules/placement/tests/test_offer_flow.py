"""The offer lifecycle end to end, under Placement Policy 2026-27.

Where test_offer_policy.py checks the rules in isolation, this checks that the
service actually wires them up: the right counters move, the category locks,
switches are counted, and the database backstop still holds when everything
else is bypassed.
"""
from datetime import timedelta
from decimal import Decimal as D

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from conftest import make_principal, make_session
from core.api.exceptions import ConflictError, NotFoundError
from fusion_auth.client import UserRef
from modules.placement.domain import offer_policy as pol
from modules.placement.models import (
    Application,
    Company,
    JobPosting,
    Offer,
    PlacementPolicy,
    PlacementRecord,
    PlacementRegistration,
    PolicyCategory,
)
from modules.placement.services import offers as offer_service

pytestmark = pytest.mark.django_db

STUDENT = 1001

#: The discipline selects the policy group, so tests vary it per case.
_SET_DISCIPLINE = {"fn": None}


@pytest.fixture(autouse=True)
def directory(stub_iam):
    """The policy is per discipline group, so the directory must answer for
    know the student's.

    Going through the IAM stub rather than writing a UserRef directly keeps the
    module boundary intact — placement may only reach directory through its
    contract, and the import-linter contract enforces that even in tests.
    """
    def install(discipline="CSE"):
        stub_iam(make_session(user_id=STUDENT), users={
            STUDENT: UserRef(user_id=STUDENT, username="21BCS001",
                             display_name="Test Student", kind="student",
                             discipline=discipline)})
    _SET_DISCIPLINE["fn"] = install
    install()
    return install


def make_world(discipline="CSE"):
    """The signed 2026-27 categories, plus one registered student whose
    discipline the policy can map."""
    policy = PlacementPolicy.objects.create(
        season="2026-27", discipline_groups=dict(pol.DEFAULT_GROUP_MAP))
    for c in pol.default_categories():
        PolicyCategory.objects.create(
            policy=policy, group=c.group, number=c.number,
            ctc_min=c.ctc_min, ctc_max=c.ctc_max,
            switch_multiplier=c.switch_multiplier,
            switch_floor=c.switch_floor, exit_above=c.exit_above,
            max_switches=c.max_switches)
    PlacementRegistration.objects.create(policy=policy, user_id=STUDENT,
                                         status="registered",
                                         registered_at=timezone.now())
    # The stub captures users at install time; without re-install, Core runs as CSE.
    _SET_DISCIPLINE["fn"](discipline)
    return policy


def make_offer(name, ctc, *, marquee=False, sector="it", dream=False,
               status="selected"):
    company = Company.objects.create(
        name=name, slug=name.lower(), status="active",
        approval_status="approved", approved_by_user_id=9,
        is_marquee=marquee, sector_kind=sector)
    posting = JobPosting.objects.create(
        company=company, title=f"{name} role", placement_year="2026-27",
        description="Work.", status="published",
        closes_at=timezone.now() + timedelta(days=7),
        eligibility_rule={}, eligibility_rule_locked_at=timezone.now(),
        ctc_lpa=D(str(ctc)), is_dream_slot=dream)
    app = Application.objects.create(posting=posting, user_id=STUDENT,
                                     status=status)
    staff = make_principal(user_id=9, kind="staff",
                           permissions=("placement_cell.offer.issue",
                                        "placement_cell.application.review"))
    return offer_service.issue(application_id=app.pk, actor=staff)


def student_principal():
    return make_principal(user_id=STUDENT, kind="student",
                          permissions=("placement_cell.offer.respond",))


def reopen(offer):
    """Re-open an offer that the auto-withdraw sweep closed, so a later test
    can exercise the POLICY rather than the state machine."""
    Offer.objects.filter(pk=offer.pk).update(status="issued")
    Application.objects.filter(pk=offer.application_id).update(
        status="offer_issued")


class TestFirstAcceptance:

    def test_accepting_creates_a_placement_record(self):
        make_world()
        offer = make_offer("Acme", 8)
        offer_service.respond(offer_id=offer.pk, accept=True,
                              actor=student_principal())
        record = PlacementRecord.objects.get(user_id=STUDENT)
        assert record.is_active
        assert record.ctc_lpa == D("8.00")

    def test_it_locks_the_category_from_the_band(self):
        """Rule 2.A — chosen once, by the company they accepted."""
        policy = make_world()
        offer_service.respond(offer_id=make_offer("Acme", 8).pk, accept=True,
                              actor=student_principal())
        reg = PlacementRegistration.objects.get(policy=policy, user_id=STUDENT)
        assert reg.category_number == 1
        assert reg.category_locked_at is not None
        assert reg.switches_used == 0        # a first offer is not a switch

    def test_a_higher_band_locks_category_two(self):
        policy = make_world()
        offer_service.respond(offer_id=make_offer("Acme", 14).pk, accept=True,
                              actor=student_principal())
        assert PlacementRegistration.objects.get(
            policy=policy, user_id=STUDENT).category_number == 2

    def test_the_held_company_shape_is_recorded(self):
        policy = make_world()
        offer_service.respond(
            offer_id=make_offer("Acme", 8, marquee=True, sector="core").pk,
            accept=True, actor=student_principal())
        reg = PlacementRegistration.objects.get(policy=policy, user_id=STUDENT)
        assert reg.held_is_marquee is True
        assert reg.held_sector_kind == "core"

    def test_declining_records_the_decision(self):
        make_world()
        offer = make_offer("Acme", 8)
        result = offer_service.respond(offer_id=offer.pk, accept=False,
                                       actor=student_principal())
        assert result.status == "declined"
        assert not PlacementRecord.objects.filter(user_id=STUDENT).exists()


class TestSwitching:

    def test_a_switch_below_the_multiple_is_refused_and_recorded(self):
        make_world()
        first = make_offer("Acme", 8)
        second = make_offer("Borg", 10)          # 1.5 x 8 = 12, so short
        offer_service.respond(offer_id=first.pk, accept=True,
                              actor=student_principal())
        reopen(second)

        with pytest.raises(ConflictError) as exc:
            offer_service.respond(offer_id=second.pk, accept=True,
                                  actor=student_principal())
        assert exc.value.code == "below_switch_multiple"

        second.refresh_from_db()
        assert second.policy_decision["allowed"] is False
        assert second.policy_decision["facts"]["required_ctc_lpa"] == "12"

    def test_a_switch_clearing_the_multiple_supersedes_and_counts(self):
        policy = make_world()
        first = make_offer("Acme", 8)
        second = make_offer("Borg", 12)
        offer_service.respond(offer_id=first.pk, accept=True,
                              actor=student_principal())
        reopen(second)
        offer_service.respond(offer_id=second.pk, accept=True,
                              actor=student_principal())

        first.refresh_from_db()
        assert first.status == "superseded"
        reg = PlacementRegistration.objects.get(policy=policy, user_id=STUDENT)
        assert reg.switches_used == 1
        assert reg.best_accepted_ctc_lpa == D("12.00")
        # Exactly one active placement, as the partial index demands.
        assert PlacementRecord.objects.filter(user_id=STUDENT,
                                              is_active=True).count() == 1

    def test_the_allowance_is_spent_after_one_switch(self):
        make_world()
        first = make_offer("Acme", 8)
        second = make_offer("Borg", 12)
        third = make_offer("Initech", 40)
        offer_service.respond(offer_id=first.pk, accept=True,
                              actor=student_principal())
        reopen(second)
        offer_service.respond(offer_id=second.pk, accept=True,
                              actor=student_principal())
        reopen(third)

        with pytest.raises(ConflictError) as exc:
            offer_service.respond(offer_id=third.pk, accept=True,
                                  actor=student_principal())
        assert exc.value.code == "switch_allowance_used"

    def test_a_marquee_placement_cannot_be_switched(self):
        """Rule 8, whatever is offered."""
        make_world()
        first = make_offer("Marquee Co", 8, marquee=True)
        second = make_offer("Borg", 60)
        offer_service.respond(offer_id=first.pk, accept=True,
                              actor=student_principal())
        reopen(second)

        with pytest.raises(ConflictError) as exc:
            offer_service.respond(offer_id=second.pk, accept=True,
                                  actor=student_principal())
        assert exc.value.code == "marquee_no_switch"

    def test_a_core_placement_cannot_move_to_it(self):
        """Rule 2.B."""
        make_world(discipline="ME")
        first = make_offer("CoreCo", 8, sector="core")
        second = make_offer("BigIT", 40, sector="it")
        offer_service.respond(offer_id=first.pk, accept=True,
                              actor=student_principal())
        reopen(second)

        with pytest.raises(ConflictError) as exc:
            offer_service.respond(offer_id=second.pk, accept=True,
                                  actor=student_principal())
        assert exc.value.code == "no_core_to_it"


class TestAutoWithdraw:

    def test_applications_close_only_when_the_student_is_out(self):
        """A Marquee placement ends the season (rule 8), so everything else
        closes. Being merely placed does NOT — rule 9 keeps parallel processes
        open while a switch allowance remains."""
        make_world()
        offer = make_offer("Marquee Co", 8, marquee=True)
        other = make_offer("Borg", 40).application
        offer_service.respond(offer_id=offer.pk, accept=True,
                              actor=student_principal())
        other.refresh_from_db()
        assert other.status == "auto_withdrawn"

    def test_a_reachable_application_is_left_alone(self):
        """The sweep is not a blanket close. Rule 9 allows parallel processes,
        and a student with a switch left is still in the running — closing
        their applications would be the platform overriding the policy."""
        make_world()
        offer = make_offer("Acme", 8)
        reachable = make_offer("Borg", 20).application
        offer_service.respond(offer_id=offer.pk, accept=True,
                              actor=student_principal())
        reachable.refresh_from_db()
        assert reachable.status == "offer_issued"

    def test_a_dream_slot_application_survives(self):
        """Rule 7 — open to placed students."""
        make_world()
        offer = make_offer("Acme", 8)
        dream = make_offer("DreamCo", 9, dream=True).application
        offer_service.respond(offer_id=offer.pk, accept=True,
                              actor=student_principal())
        dream.refresh_from_db()
        assert dream.status == "offer_issued"

    def test_the_closure_records_the_specific_policy_reason(self):
        make_world()
        from modules.placement.models import ApplicationTransition
        offer = make_offer("Marquee Co", 8, marquee=True)
        other = make_offer("Borg", 40).application
        offer_service.respond(offer_id=offer.pk, accept=True,
                              actor=student_principal())
        t = ApplicationTransition.objects.filter(
            application=other, to_status="auto_withdrawn").get()
        assert t.actor_label == "system"
        # The rule that closed it, not a generic sentence.
        assert "Marquee" in t.reason


class TestDatabaseBackstop:

    def test_the_database_refuses_two_active_placements(self):
        """The layer that still holds when the service is bypassed."""
        policy = make_world()
        first = make_offer("Acme", 8)
        offer_service.respond(offer_id=first.pk, accept=True,
                              actor=student_principal())
        second = make_offer("Borg", 30)

        with pytest.raises(IntegrityError), transaction.atomic():
            PlacementRecord.objects.create(
                policy=policy, offer=second, company=second.posting.company,
                posting=second.posting, user_id=STUDENT,
                ctc_lpa=D("30"), is_active=True)

    def test_an_inactive_record_does_not_collide(self):
        """Superseding works precisely because the index is partial."""
        policy = make_world()
        first = make_offer("Acme", 8)
        offer_service.respond(offer_id=first.pk, accept=True,
                              actor=student_principal())
        PlacementRecord.objects.filter(user_id=STUDENT).update(is_active=False)
        second = make_offer("Borg", 30)
        PlacementRecord.objects.create(
            policy=policy, offer=second, company=second.posting.company,
            posting=second.posting, user_id=STUDENT, ctc_lpa=D("30"),
            is_active=True)
        assert PlacementRecord.objects.filter(user_id=STUDENT).count() == 2


class TestDeadlines:

    def test_an_offer_always_carries_a_deadline(self):
        make_world()
        assert make_offer("Acme", 8).respond_by > timezone.now()

    def test_responding_after_the_deadline_is_refused(self):
        make_world()
        offer = make_offer("Acme", 8)
        Offer.objects.filter(pk=offer.pk).update(
            respond_by=timezone.now() - timedelta(seconds=1))
        with pytest.raises(ConflictError) as exc:
            offer_service.respond(offer_id=offer.pk, accept=True,
                                  actor=student_principal())
        assert exc.value.code == "offer_expired"

    def test_the_expiry_sweep_is_idempotent(self):
        make_world()
        offer = make_offer("Acme", 8)
        Offer.objects.filter(pk=offer.pk).update(
            respond_by=timezone.now() - timedelta(seconds=1))
        assert offer_service.expire_overdue() == 1
        assert offer_service.expire_overdue() == 0
        offer.refresh_from_db()
        assert offer.status == "expired"

    def test_an_answered_offer_is_not_expired_by_the_sweep(self):
        make_world()
        offer = make_offer("Acme", 8)
        offer_service.respond(offer_id=offer.pk, accept=True,
                              actor=student_principal())
        Offer.objects.filter(pk=offer.pk).update(
            respond_by=timezone.now() - timedelta(seconds=1))
        assert offer_service.expire_overdue() == 0
        offer.refresh_from_db()
        assert offer.status == "accepted"


class TestOwnership:

    def test_another_students_offer_is_not_found(self):
        make_world()
        offer = make_offer("Acme", 8)
        intruder = make_principal(user_id=9999, kind="student",
                                  permissions=("placement_cell.offer.respond",))
        with pytest.raises(NotFoundError):
            offer_service.respond(offer_id=offer.pk, accept=True, actor=intruder)


class TestNotifications:

    def test_issuing_an_offer_queues_exactly_one_notification(self):
        from modules.placement.models import NotificationOutbox
        make_world()
        offer = make_offer("Acme", 8)
        rows = NotificationOutbox.objects.filter(topic="offer.issued")
        assert rows.count() == 1
        assert rows.first().recipient_user_id == STUDENT
        assert rows.first().payload["offer_id"] == offer.pk

    def test_the_outbox_is_idempotent(self):
        from modules.placement.services import notifications
        make_world()
        offer = make_offer("Acme", 8)
        again = notifications.enqueue(
            topic="offer.issued", dedupe_key=f"offer.issued:{offer.pk}",
            recipient_user_id=STUDENT, subject="dup", body="dup")
        assert again is None
