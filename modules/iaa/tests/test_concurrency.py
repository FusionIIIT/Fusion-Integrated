"""Things that must happen once, raced for real: threads on separate connections, released
together on a barrier. A single-threaded test cannot see these.
"""
import threading
from datetime import timedelta

import pytest
from django.db import IntegrityError, connection
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.iaa.models import (
    Anomaly,
    ApprovalStep,
    BudgetEntry,
    FinancialRecord,
    ObservationResponse,
    TrailEntry,
)
from modules.iaa.services import anomalies, decisions, observations, processing, records, review
from modules.iaa.tests.helpers import DOC, new_expense

pytestmark = pytest.mark.django_db(transaction=True)

LOST = (ConflictError, NotFoundError, IntegrityError)


def race(*calls):
    """Run each callable on its own thread and connection, all released at the same instant."""
    gate = threading.Barrier(len(calls), timeout=15)
    outcomes = [None] * len(calls)

    def runner(index, call):
        try:
            gate.wait()
            outcomes[index] = ("won", call())
        except LOST as exc:                              # the loser's refusal is the result
            outcomes[index] = ("lost", exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=runner, args=(i, c)) for i, c in enumerate(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert all(outcomes), "a thread did not finish"
    return outcomes


def one_wins(outcomes):
    won = [o for o in outcomes if o[0] == "won"]
    lost = [o[1] for o in outcomes if o[0] == "lost"]
    assert len(won) == 1, outcomes
    assert all(isinstance(exc, LOST) for exc in lost), lost


def test_two_submissions_of_one_draft_submit_it_once(people, configured):
    draft = new_expense(people.creator, submit=False)
    one_wins(race(lambda: records.submit(people.creator, draft.pk),
                  lambda: records.submit(people.creator, draft.pk)))
    assert TrailEntry.objects.filter(entity_id=draft.pk, action="submit").count() == 1
    assert FinancialRecord.objects.get(pk=draft.pk).status == "submitted"


def test_two_validations_of_one_request_validate_it_once(people, configured):
    rec = new_expense(people.creator)
    one_wins(race(lambda: review.validate(people.finance, rec.pk),
                  lambda: review.validate(people.finance, rec.pk)))
    assert ApprovalStep.objects.filter(record=rec).count() == 1
    assert TrailEntry.objects.filter(entity_id=rec.pk, to_status="finance_validated").count() == 1


def test_two_approvals_of_one_step_decide_it_once(people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    one_wins(race(
        lambda: decisions.decide(people.hod, rec.pk, decision="approve", remarks="One"),
        lambda: decisions.decide(people.hod, rec.pk, decision="reject", remarks="Two")))
    steps = ApprovalStep.objects.filter(record=rec, status__in=["approved", "rejected"])
    assert steps.count() == 1
    final = FinancialRecord.objects.get(pk=rec.pk).status
    assert final == {"approved": "approved", "rejected": "rejected"}[steps.get().status]


def test_two_recordings_of_one_approved_request_commit_the_budget_once(people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    decisions.decide(people.hod, rec.pk, decision="approve", remarks="OK")
    one_wins(race(lambda: processing.record(people.finance, rec.pk, reference="R-1"),
                  lambda: processing.record(people.finance, rec.pk, reference="R-2")))
    assert BudgetEntry.objects.filter(record=rec, kind="commitment").count() == 1
    assert FinancialRecord.objects.get(pk=rec.pk).status == "recorded"


def test_two_sweeps_at_once_escalate_an_overdue_approval_once(people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    at = timezone.now() + timedelta(hours=49)
    outcomes = race(lambda: decisions.escalate_overdue(at=at),
                    lambda: decisions.escalate_overdue(at=at))
    assert [o[0] for o in outcomes] == ["won", "won"]
    assert sum(o[1].escalated for o in outcomes) == 1
    assert ApprovalStep.objects.filter(record=rec, via_escalation=True).count() == 1
    assert TrailEntry.objects.filter(entity_id=rec.pk, action="escalate").count() == 1


def test_two_resolutions_of_one_anomaly_resolve_it_once(people, configured):
    anomaly = anomalies.flag(people.finance, category="budget", description="Overspend")
    one_wins(race(
        lambda: anomalies.resolve(people.finance, anomaly.pk, resolution="First"),
        lambda: anomalies.resolve(people.finance, anomaly.pk, resolution="Second")))
    assert Anomaly.objects.get(pk=anomaly.pk).status == "resolved"
    assert TrailEntry.objects.filter(entity="anomaly", entity_id=anomaly.pk,
                                     to_status="resolved").count() == 1


def test_two_responses_to_one_observation_record_one_response(people, configured):
    rec = new_expense(people.creator)
    obs = observations.raise_observation(people.auditor, title="t", detail="d", record_id=rec.pk)
    one_wins(race(
        lambda: observations.respond(people.creator, obs.pk, corrective_action="One"),
        lambda: observations.respond(people.creator, obs.pk, corrective_action="Two")))
    assert ObservationResponse.objects.filter(observation=obs).count() == 1


def test_a_document_added_while_submitting_is_not_lost_or_duplicated(people, configured):
    draft = new_expense(people.creator, submit=False)
    race(lambda: records.add_document(people.creator, draft.pk, **DOC),
         lambda: records.add_document(people.creator, draft.pk, **DOC))
    assert FinancialRecord.objects.get(pk=draft.pk).documents.count() == 3
