"""Real threads on real connections: what must happen once happens once (Step 5.7)."""
import threading
from datetime import timedelta

import pytest
from django.core import mail
from django.db import connection
from django.utils import timezone

from core.api.exceptions import DomainError
from modules.pms.domain import state_machine as sm
from modules.pms.models import (
    Application,
    AttorneyAssignment,
    Budget,
    DeadlineAlert,
    DocumentVersion,
    Notification,
    ReviewCycle,
)
from modules.pms.services import (
    applications,
    attorneys,
    budget,
    deadlines,
    documents,
    notifications,
    review,
)
from modules.pms.tests.conftest import (
    ATTORNEY,
    ATTORNEY_2,
    DIRECTOR,
    DIRECTOR_2,
    approved_with_attorney,
    make_app,
    pdf,
    with_budget,
    with_cycle,
)

pytestmark = pytest.mark.django_db(transaction=True)


def race(*calls):
    """Start every call at the same instant; return each one's result or DomainError code."""
    barrier = threading.Barrier(len(calls))
    out = [None] * len(calls)

    def run(i, fn):
        try:
            barrier.wait()
            out[i] = ("ok", fn())
        except DomainError as exc:
            out[i] = ("refused", exc.code)
        finally:
            connection.close()

    threads = [threading.Thread(target=run, args=(i, fn)) for i, fn in enumerate(calls)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    return out


# PMS-AFR-044 PMS-AFR-224
def test_two_drafts_submitted_at_once_get_different_references_pms_afr_044(world):
    a, b = make_app(sm.DRAFT), make_app(sm.DRAFT)
    actor = world["applicant"].principal
    world["applicant"]._go()
    results = race(lambda: applications.submit(actor=actor, pk=a.pk),
                   lambda: applications.submit(actor=actor, pk=b.pk))
    assert [r[0] for r in results] == ["ok", "ok"]
    refs = set(Application.objects.values_list("reference", flat=True))
    assert len(refs) == 2


def test_the_same_draft_submitted_twice_at_once_is_submitted_once(world):
    app = make_app(sm.DRAFT)
    actor = world["applicant"].principal
    world["applicant"]._go()
    results = race(*[lambda: applications.submit(actor=actor, pk=app.pk)] * 2)
    assert sorted(r[0] for r in results) == ["ok", "refused"]
    assert Application.objects.get(pk=app.pk).version == 1


def test_two_director_assignments_at_once_open_one_cycle(world):
    app = make_app(sm.SUBMITTED)
    pcc = world["pcc"].principal
    world["pcc"]._go()
    race(lambda: review.assign_director(actor=pcc, pk=app.pk, director_user_id=DIRECTOR),
         lambda: review.assign_director(actor=pcc, pk=app.pk, director_user_id=DIRECTOR_2))
    assert ReviewCycle.objects.filter(application=app, status="open").count() == 1


# BR-PMS-029
def test_two_decisions_at_once_record_one_br_pms_029(world):
    app = make_app(sm.UNDER_REVIEW)
    with_cycle(app, DIRECTOR)
    director = world["director"].principal
    world["director"]._go()
    text = "x" * 60
    results = race(
        lambda: review.decide(actor=director, pk=app.pk, decision="approve", justification=text),
        lambda: review.decide(actor=director, pk=app.pk, decision="reject", justification=text))
    assert sorted(r[0] for r in results) == ["ok", "refused"]
    assert ReviewCycle.objects.filter(application=app, status="decided").count() == 1


# BR-PMS-040
def test_two_attorney_offers_at_once_leave_one_live_br_pms_040(world):
    app = make_app(sm.APPROVED)
    with_cycle(app, status="decided", decision="approve")
    pcc = world["pcc"].principal
    world["pcc"]._go()
    race(lambda: attorneys.assign_attorney(actor=pcc, pk=app.pk, attorney_user_id=ATTORNEY),
         lambda: attorneys.assign_attorney(actor=pcc, pk=app.pk, attorney_user_id=ATTORNEY_2))
    assert AttorneyAssignment.objects.filter(
        application=app, status__in=sorted(sm.LIVE_ASSIGNMENT)).count() == 1


def test_a_budget_decided_twice_at_once_is_decided_once(world):
    app = approved_with_attorney()
    b = with_budget(app, status=sm.PROPOSED)
    director = world["director"].principal
    world["director"]._go()
    results = race(*[lambda: budget.decide(actor=director, budget_id=b.pk, approve=True)] * 2)
    assert sorted(r[0] for r in results) == ["ok", "refused"]
    assert Budget.objects.get(pk=b.pk).financial_records.count() == 1


# BR-PMS-082
def test_two_new_versions_at_once_get_different_numbers_br_pms_082(world, scanner):
    app = make_app(sm.DRAFT)
    doc = app.documents.get()
    actor = world["applicant"].principal
    world["applicant"]._go()
    race(*[lambda: documents.upload(actor=actor, pk=app.pk, uploaded=pdf(),
                                    document_id=doc.pk)] * 2)
    numbers = sorted(DocumentVersion.objects.filter(document=doc)
                     .values_list("number", flat=True))
    assert numbers == [1, 2, 3]
    assert DocumentVersion.objects.filter(document=doc, is_current=True).count() == 1


# BR-PMS-038
def test_the_deadline_sweep_twice_at_once_alerts_and_expires_once_br_pms_038(world):
    reviewing = make_app(sm.UNDER_REVIEW)
    with_cycle(reviewing, DIRECTOR, due=timezone.localdate() + timedelta(days=4))
    late = make_app(sm.NEEDS_REVISION, revision_due_on=timezone.localdate() - timedelta(1))
    results = race(deadlines.sweep, deadlines.sweep)
    assert all(r[0] == "ok" for r in results)
    assert DeadlineAlert.objects.count() == 1
    assert Application.objects.get(pk=late.pk).status == sm.EXPIRED
    assert Notification.objects.filter(topic="application.expired").count() == 1


def test_delivery_twice_at_once_sends_each_email_once(world):
    world["applicant"]._go()
    for i in range(5):
        notifications.enqueue(topic="t", dedupe_key=f"k{i}", recipient_user_id=1001,
                              subject="s", body="b")
    race(notifications.deliver_pending, notifications.deliver_pending)
    assert len(mail.outbox) == 5
    assert Notification.objects.filter(status="sent").count() == 5
