"""Tests for SLA threshold evaluation (BR-EL-032, BR-EL-033, BR-EL-038).

Pure-domain tests: no database, no Django settings. Every case here maps to an
atomic functional requirement from the FRS, named in the test docstring, so a
failure says which obligation broke.
"""
import datetime
import unittest

from modules.elm.domain.sla import (
    DEFAULT_THRESHOLD_HOURS,
    InvalidSlaThreshold,
    SlaAction,
    SlaReason,
    SlaThresholds,
    TaskKind,
    TaskSnapshot,
    actionable,
    evaluate_task,
    evaluate_tasks,
    hours_between,
)

T0 = datetime.datetime(2026, 3, 2, 9, 0, 0)


def thresholds(reminder=24.0, escalation=48.0, **kw):
    return SlaThresholds(
        task_kind=kw.pop("task_kind", TaskKind.UNIT_HEAD_REVIEW),
        reminder_hours=reminder,
        escalation_hours=escalation,
        **kw,
    )


def task(hours_old=0.0, pending=True, reminded=False, escalated=False, assignee=7):
    return TaskSnapshot(
        task_id=1,
        task_kind=TaskKind.UNIT_HEAD_REVIEW,
        assignee_id=assignee,
        opened_at=T0,
        is_pending=pending,
        reminded_at=T0 + datetime.timedelta(hours=hours_old) if reminded else None,
        escalated_at=T0 + datetime.timedelta(hours=hours_old) if escalated else None,
    )


def at(hours):
    return T0 + datetime.timedelta(hours=hours)


class TestHoursBetween(unittest.TestCase):

    def test_elapsed_hours(self):
        self.assertAlmostEqual(hours_between(T0, at(36)), 36.0)

    def test_negative_interval_floors_at_zero(self):
        """A task stamped in the future must not read as overdue.

        Without the floor, clock skew between an application server and the
        database would make `now - opened_at` negative on one pass and
        wildly positive on the comparison, which is how a whole queue gets
        escalated at once.
        """
        self.assertEqual(hours_between(at(10), T0), 0.0)


class TestPendingOnlyGuard(unittest.TestCase):
    """AFR-EL-031.4 and AFR-EL-032.4: suppression for a non-pending task."""

    def test_non_pending_task_is_not_reminded(self):
        d = evaluate_task(task(pending=False), thresholds(), at(30))
        self.assertIs(d.action, SlaAction.NONE)
        self.assertIs(d.reason, SlaReason.NOT_PENDING)

    def test_non_pending_task_is_not_escalated(self):
        """Even far past the escalation threshold, a closed task is silent."""
        d = evaluate_task(task(pending=False), thresholds(), at(500))
        self.assertIs(d.action, SlaAction.NONE)
        self.assertIs(d.reason, SlaReason.NOT_PENDING)

    def test_pending_check_precedes_threshold_arithmetic(self):
        """A closed task with no configuration still reports NOT_PENDING.

        The order matters for the audit log: 'nobody configured this' and
        'this was already done' are different findings for an administrator.
        """
        d = evaluate_task(task(pending=False), None, at(500))
        self.assertIs(d.reason, SlaReason.NOT_PENDING)


class TestReminder(unittest.TestCase):
    """CFR-EL-031 / BR-EL-032."""

    def test_below_threshold_no_action(self):
        d = evaluate_task(task(), thresholds(reminder=24, escalation=48), at(23.9))
        self.assertIs(d.action, SlaAction.NONE)
        self.assertIs(d.reason, SlaReason.BELOW_REMINDER)

    def test_exactly_at_threshold_reminds(self):
        """'Reaches its configured reminder threshold' is inclusive."""
        d = evaluate_task(task(), thresholds(reminder=24, escalation=48), at(24))
        self.assertIs(d.action, SlaAction.REMIND)
        self.assertIs(d.reason, SlaReason.REMINDER_DUE)

    def test_reminder_addressed_to_the_assignee(self):
        """AFR-EL-031.2: the reminder goes to the responsible user."""
        d = evaluate_task(task(assignee=42), thresholds(), at(30))
        self.assertEqual(d.recipient_id, 42)

    def test_reminder_is_not_repeated(self):
        d = evaluate_task(task(reminded=True), thresholds(), at(30))
        self.assertIs(d.action, SlaAction.NONE)
        self.assertIs(d.reason, SlaReason.REMINDER_ALREADY_SENT)

    def test_elapsed_hours_reported_for_the_message(self):
        d = evaluate_task(task(), thresholds(), at(30))
        self.assertAlmostEqual(d.hours_elapsed, 30.0)


class TestEscalation(unittest.TestCase):
    """CFR-EL-032 / BR-EL-033."""

    def test_past_threshold_escalates(self):
        d = evaluate_task(task(), thresholds(reminder=24, escalation=48), at(49))
        self.assertIs(d.action, SlaAction.ESCALATE)
        self.assertIs(d.reason, SlaReason.ESCALATION_DUE)

    def test_escalation_wins_over_an_unsent_reminder(self):
        """A task old enough to escalate escalates on this pass.

        Emitting the missed reminder first would push the escalation out by a
        whole cycle, which is the opposite of what an overdue task needs.
        """
        d = evaluate_task(task(reminded=False), thresholds(reminder=24, escalation=48), at(100))
        self.assertIs(d.action, SlaAction.ESCALATE)

    def test_escalation_addressed_to_the_configured_authority(self):
        """AFR-EL-032.2: not to the assignee who already failed to act."""
        d = evaluate_task(
            task(assignee=7),
            thresholds(escalation_role="Registrar", escalation_recipient_id=99),
            at(60),
        )
        self.assertEqual(d.recipient_id, 99)
        self.assertEqual(d.original_assignee_id, 7)
        self.assertEqual(d.escalation_role, "Registrar")

    def test_escalation_is_not_repeated(self):
        d = evaluate_task(task(escalated=True), thresholds(), at(60))
        self.assertIs(d.action, SlaAction.NONE)
        self.assertIs(d.reason, SlaReason.ESCALATION_ALREADY_SENT)

    def test_routing_change_flag_is_carried_through(self):
        """BR-EL-033 distinguishes notification-only from routing-changing."""
        notify_only = evaluate_task(task(), thresholds(escalation_recipient_id=99), at(60))
        self.assertFalse(notify_only.changes_routing)

        reroute = evaluate_task(
            task(),
            thresholds(escalation_recipient_id=99, escalation_changes_routing=True),
            at(60),
        )
        self.assertTrue(reroute.changes_routing)


class TestConfigurationGate(unittest.TestCase):
    """BR-EL-038: the thresholds are the administrator's, not the code's."""

    def test_unconfigured_kind_takes_no_action(self):
        d = evaluate_task(task(), None, at(1000))
        self.assertIs(d.action, SlaAction.NONE)
        self.assertIs(d.reason, SlaReason.NOT_CONFIGURED)

    def test_inactive_configuration_takes_no_action(self):
        d = evaluate_task(task(), thresholds(is_active=False), at(1000))
        self.assertIs(d.action, SlaAction.NONE)
        self.assertIs(d.reason, SlaReason.CONFIG_INACTIVE)


class TestThresholdValidation(unittest.TestCase):
    """EL-UC-018 failure guarantee: an invalid configuration is not applied."""

    def test_valid_configuration_passes(self):
        thresholds(reminder=24, escalation=48).validate()

    def test_zero_reminder_rejected(self):
        with self.assertRaises(InvalidSlaThreshold):
            thresholds(reminder=0, escalation=48).validate()

    def test_negative_escalation_rejected(self):
        with self.assertRaises(InvalidSlaThreshold):
            thresholds(reminder=24, escalation=-1).validate()

    def test_escalation_must_be_later_than_reminder(self):
        with self.assertRaises(InvalidSlaThreshold):
            thresholds(reminder=48, escalation=24).validate()

    def test_equal_thresholds_rejected(self):
        """Equal thresholds would make the reminder unreachable.

        Escalation is checked first, so a task crossing both at once would
        escalate and the reminder would never fire for any task.
        """
        with self.assertRaises(InvalidSlaThreshold):
            thresholds(reminder=24, escalation=24).validate()

    def test_rerouting_escalation_needs_a_named_recipient(self):
        with self.assertRaises(InvalidSlaThreshold):
            thresholds(escalation_changes_routing=True, escalation_role="Registrar").validate()

    def test_rerouting_escalation_with_recipient_passes(self):
        thresholds(
            escalation_changes_routing=True,
            escalation_role="Registrar",
            escalation_recipient_id=99,
        ).validate()


class TestBatchEvaluation(unittest.TestCase):

    def _snap(self, tid, kind, pending=True, opened=T0):
        return TaskSnapshot(
            task_id=tid, task_kind=kind, assignee_id=tid, opened_at=opened, is_pending=pending
        )

    def test_each_kind_uses_its_own_configuration(self):
        tasks = [
            self._snap(1, TaskKind.UNIT_HEAD_REVIEW),
            self._snap(2, TaskKind.SANCTION_DECISION),
        ]
        config = {
            TaskKind.UNIT_HEAD_REVIEW.value: thresholds(
                reminder=24, escalation=48, task_kind=TaskKind.UNIT_HEAD_REVIEW
            ),
            TaskKind.SANCTION_DECISION.value: thresholds(
                reminder=72, escalation=144, task_kind=TaskKind.SANCTION_DECISION
            ),
        }
        decisions = {d.task_id: d for d in evaluate_tasks(tasks, config, at(30))}
        self.assertIs(decisions[1].action, SlaAction.REMIND)
        self.assertIs(decisions[2].action, SlaAction.NONE)

    def test_a_decision_is_returned_for_every_task(self):
        """Suppressed evaluations must be reportable, so none are dropped."""
        tasks = [
            self._snap(1, TaskKind.UNIT_HEAD_REVIEW),
            self._snap(2, TaskKind.UNIT_HEAD_REVIEW, pending=False),
            self._snap(3, TaskKind.RESUMPTION_REVIEW),
        ]
        decisions = evaluate_tasks(tasks, {}, at(30))
        self.assertEqual(len(decisions), 3)
        self.assertEqual(actionable(decisions), [])

    def test_actionable_filters_to_outbound_work(self):
        tasks = [
            self._snap(1, TaskKind.UNIT_HEAD_REVIEW),
            self._snap(2, TaskKind.UNIT_HEAD_REVIEW, pending=False),
        ]
        config = {TaskKind.UNIT_HEAD_REVIEW.value: thresholds(reminder=24, escalation=48)}
        todo = actionable(evaluate_tasks(tasks, config, at(30)))
        self.assertEqual([d.task_id for d in todo], [1])


class TestSeedDefaults(unittest.TestCase):

    def test_every_task_kind_has_a_seed_value(self):
        """A task kind with no seed would ship dark on a fresh install."""
        self.assertEqual(set(DEFAULT_THRESHOLD_HOURS), set(TaskKind))

    def test_every_seed_value_is_itself_valid(self):
        for kind, (reminder, escalation) in DEFAULT_THRESHOLD_HOURS.items():
            SlaThresholds(
                task_kind=kind, reminder_hours=reminder, escalation_hours=escalation
            ).validate()


if __name__ == "__main__":
    unittest.main()
