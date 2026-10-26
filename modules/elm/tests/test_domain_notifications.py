"""Tests for notification composition (BR-EL-035, and the message bodies
issued under BR-EL-032 / BR-EL-033).

Pure-domain tests: no database. What is asserted here is that every task kind
produces an addressable, actionable message, and that a suppressed SLA
decision cannot produce a message at all.
"""
import unittest

from modules.elm.domain.notifications import (
    TASK_LABELS,
    TASK_LINKS,
    NotificationKind,
    compose_assignment,
    compose_escalation,
    compose_for_decision,
    compose_reminder,
    task_label,
    task_link,
)
from modules.elm.domain.sla import SlaAction, SlaDecision, SlaReason, TaskKind


class TestCoverage(unittest.TestCase):

    def test_every_task_kind_has_a_label(self):
        """A kind without a label would notify people in enum case."""
        self.assertEqual(set(TASK_LABELS), set(TaskKind))

    def test_every_task_kind_has_a_link(self):
        """A notification with nowhere to go cannot be acted on."""
        self.assertEqual(set(TASK_LINKS), set(TaskKind))

    def test_unknown_kind_degrades_instead_of_raising(self):
        """A new task kind must not break a workflow transition.

        These composers are called inside the transaction that moves an
        application between statuses. A KeyError there would roll back a
        legitimate approval over a missing dictionary entry.
        """
        self.assertEqual(task_label("SOME_NEW_THING"), "some new thing")
        self.assertEqual(task_link("SOME_NEW_THING"), "/leave/mine")


class TestAssignment(unittest.TestCase):
    """BR-EL-035 / AFR-EL-030.1."""

    def test_assignment_is_addressed_and_actionable(self):
        m = compose_assignment(
            recipient_id=42,
            task_kind=TaskKind.UNIT_HEAD_REVIEW,
            application_ref="EL request #7 (2026-04-01 to 2026-04-03)",
            applicant_name="A. Sharma",
        )
        self.assertIs(m.kind, NotificationKind.TASK_ASSIGNED)
        self.assertEqual(m.recipient_id, 42)
        self.assertEqual(m.link, "/leave/approvals")
        self.assertIn("#7", m.body)
        self.assertIn("A. Sharma", m.body)
        self.assertTrue(m.subject)

    def test_assignment_without_an_application_reference_is_still_readable(self):
        m = compose_assignment(recipient_id=42, task_kind=TaskKind.SUBSTITUTE_RESPONSE)
        self.assertIn("substitute responsibility request", m.body)


class TestReminderMessage(unittest.TestCase):

    def test_reminder_states_the_wait_and_that_it_is_pending(self):
        m = compose_reminder(
            recipient_id=42, task_kind=TaskKind.SANCTION_DECISION, hours_elapsed=73.4
        )
        self.assertIs(m.kind, NotificationKind.SLA_REMINDER)
        self.assertIn("73", m.body)
        self.assertIn("still pending", m.body)


class TestEscalationMessage(unittest.TestCase):

    def test_notification_only_escalation_says_so(self):
        """BR-EL-033: a notice must not read as a handover of responsibility."""
        m = compose_escalation(
            recipient_id=99,
            task_kind=TaskKind.UNIT_HEAD_REVIEW,
            hours_elapsed=100,
            changes_routing=False,
        )
        self.assertIn("not been reassigned", m.body)

    def test_routing_escalation_says_responsibility_moved(self):
        m = compose_escalation(
            recipient_id=99,
            task_kind=TaskKind.UNIT_HEAD_REVIEW,
            hours_elapsed=100,
            changes_routing=True,
        )
        self.assertIn("routed to you", m.body)

    def test_escalation_names_the_original_holder(self):
        m = compose_escalation(
            recipient_id=99,
            task_kind=TaskKind.UNIT_HEAD_REVIEW,
            hours_elapsed=100,
            original_assignee_ref="user 7",
        )
        self.assertIn("user 7", m.body)


class TestComposeForDecision(unittest.TestCase):

    def _decision(self, action, reason, **kw):
        return SlaDecision(
            task_id=1,
            task_kind=TaskKind.UNIT_HEAD_REVIEW,
            action=action,
            reason=reason,
            hours_elapsed=kw.pop("hours", 50.0),
            **kw,
        )

    def test_remind_decision_yields_a_reminder(self):
        m = compose_for_decision(
            self._decision(SlaAction.REMIND, SlaReason.REMINDER_DUE), recipient_id=7
        )
        self.assertIsNotNone(m)
        self.assertIs(m.kind, NotificationKind.SLA_REMINDER)

    def test_escalate_decision_yields_an_escalation(self):
        m = compose_for_decision(
            self._decision(SlaAction.ESCALATE, SlaReason.ESCALATION_DUE, changes_routing=True),
            recipient_id=99,
        )
        self.assertIsNotNone(m)
        self.assertIs(m.kind, NotificationKind.SLA_ESCALATION)

    def test_suppressed_decision_yields_nothing(self):
        """This is the pending-only guard holding end to end.

        A suppressed evaluation must not be able to produce a message
        downstream, whatever the reason code (BR-EL-032, BR-EL-033).
        """
        for reason in (
            SlaReason.NOT_PENDING,
            SlaReason.NOT_CONFIGURED,
            SlaReason.CONFIG_INACTIVE,
            SlaReason.BELOW_REMINDER,
            SlaReason.REMINDER_ALREADY_SENT,
            SlaReason.ESCALATION_ALREADY_SENT,
        ):
            with self.subTest(reason=reason):
                m = compose_for_decision(
                    self._decision(SlaAction.NONE, reason), recipient_id=7
                )
                self.assertIsNone(m)


if __name__ == "__main__":
    unittest.main()
