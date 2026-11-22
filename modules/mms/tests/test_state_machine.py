"""Unit tests for MMS declarative state machine and transitions.

Covers:
- Registration state machine (BW-MMS-01, BW-MMS-02, CW-MMS-01)
- Deregistration state machine (BW-MMS-03, BW-MMS-04, CW-MMS-02)
- Rebate state machine (BW-MMS-05, BW-MMS-06, BW-MMS-07, CW-MMS-03)
- Vacation survey state machine (BW-MMS-08, BW-MMS-09, BW-MMS-10, CW-MMS-04)
- Special food state machine (BW-MMS-11..15, CW-MMS-05)
- Monthly billing state machine (BW-MMS-16)
- Actor authorization enforcement
- Terminal state refusal and illegal transition rejection
"""

import pytest

from modules.mms.domain import state_machine as sm
from modules.mms.domain.exceptions import ActorNotAllowed, InvalidTransition


class TestStateMachineTransitions:
    def test_registration_transitions(self):
        # Caretaker opens window
        t1 = sm.resolve("window_closed", "window_open", sm.CARETAKER)
        assert t1.permission == "mms.registration.window.manage"

        # Student submits registration
        t2 = sm.resolve("window_open", "registration_pending", sm.STUDENT)
        assert t2.permission == "mms.registration.create"

        # Caretaker approves
        t3 = sm.resolve("registration_pending", "registration_approved", sm.CARETAKER)
        assert t3.permission == "mms.registration.review"

        # Caretaker rejects
        t4 = sm.resolve("registration_pending", "registration_rejected", sm.CARETAKER)
        assert t4.permission == "mms.registration.review"

    def test_deregistration_transitions(self):
        # Student submits deregistration
        t1 = sm.resolve("student_registered", "deregistration_pending", sm.STUDENT)
        assert t1.permission == "mms.deregistration.create"

        # Caretaker approves (awaiting date)
        t2 = sm.resolve(
            "deregistration_pending", "deregistration_approved_awaiting_date", sm.CARETAKER
        )
        assert t2.permission == "mms.deregistration.review"

        # System activates next calendar day
        t3 = sm.resolve("deregistration_approved_awaiting_date", "student_deregistered", sm.SYSTEM)
        assert t3.permission == "mms.deregistration.manage"

        # Caretaker rejects
        t4 = sm.resolve("deregistration_pending", "deregistration_rejected", sm.CARETAKER)
        assert t4.permission == "mms.deregistration.review"

    def test_rebate_transitions(self):
        # Student submits
        t1 = sm.resolve("no_rebate", "rebate_pending", sm.STUDENT)
        assert t1.permission == "mms.rebate.create"

        # Caretaker approves
        t2 = sm.resolve("rebate_pending", "rebate_approved", sm.CARETAKER)
        assert t2.permission == "mms.rebate.review"

        # Caretaker approves with modified dates
        t3 = sm.resolve("rebate_pending", "rebate_approved_modified_dates", sm.CARETAKER)
        assert t3.permission == "mms.rebate.review"

        # Caretaker rejects
        t4 = sm.resolve("rebate_pending", "rebate_rejected", sm.CARETAKER)
        assert t4.permission == "mms.rebate.review"

    def test_vacation_survey_transitions(self):
        # Caretaker / Student creates survey
        t1 = sm.resolve("survey_not_created", "survey_open", sm.STUDENT)
        assert t1.permission == "mms.survey.create"

        # Student responds Yes
        t2 = sm.resolve("survey_open", "response_yes", sm.STUDENT)
        assert t2.permission == "mms.survey_response.create"

        # Student responds No
        t3 = sm.resolve("survey_open", "response_no", sm.STUDENT)
        assert t3.permission == "mms.survey_response.create"

        # System default-No
        t4 = sm.resolve("survey_open", "response_default_no", sm.SYSTEM)
        assert t4.permission == "mms.survey.manage"

    def test_special_food_transitions(self):
        # Student requests
        t1 = sm.resolve("no_request", "requested", sm.STUDENT)
        assert t1.permission == "mms.special_food.create"

        # Caretaker approves
        t2 = sm.resolve("requested", "approved", sm.CARETAKER)
        assert t2.permission == "mms.special_food.review"

        # Caretaker rejects
        t3 = sm.resolve("requested", "rejected", sm.CARETAKER)
        assert t3.permission == "mms.special_food.review"

        # System default rejection on decision period expiration
        t4 = sm.resolve("requested", "rejected_default", sm.SYSTEM)
        assert t4.permission == "mms.special_food.manage"

        # Caretaker records Served
        t5 = sm.resolve("approved", "served", sm.CARETAKER)
        assert t5.permission == "mms.special_food.update"

        # Caretaker records Cancelled
        t6 = sm.resolve("approved", "cancelled", sm.CARETAKER)
        assert t6.permission == "mms.special_food.update"

    def test_billing_transitions(self):
        # System generates bill
        t1 = sm.resolve("bill_not_generated", "bill_generated", sm.SYSTEM)
        assert t1.permission == "mms.billing.manage"

        # Caretaker finalizes bill
        t2 = sm.resolve("bill_generated", "bill_finalized", sm.CARETAKER)
        assert t2.permission == "mms.billing.approve"

        # Caretaker publishes bill
        t3 = sm.resolve("bill_finalized", "bill_published", sm.CARETAKER)
        assert t3.permission == "mms.billing.publish"


class TestStateMachineSecurityAndErrors:
    def test_actor_not_allowed(self):
        # Student cannot approve registration
        with pytest.raises(ActorNotAllowed) as exc:
            sm.resolve("registration_pending", "registration_approved", sm.STUDENT)
        assert exc.value.actor_kind == "student"
        assert exc.value.frm == "registration_pending"
        assert exc.value.to == "registration_approved"

        # Caretaker cannot submit registration
        with pytest.raises(ActorNotAllowed) as exc:
            sm.resolve("window_open", "registration_pending", sm.CARETAKER)
        assert exc.value.actor_kind == "caretaker"

        # Student cannot finalize bills
        with pytest.raises(ActorNotAllowed) as exc:
            sm.resolve("bill_generated", "bill_finalized", sm.STUDENT)
        assert exc.value.actor_kind == "student"

    def test_invalid_transitions(self):
        # Cannot jump from no_request to served directly
        with pytest.raises(InvalidTransition) as exc:
            sm.resolve("no_request", "served", sm.CARETAKER)
        assert exc.value.frm == "no_request"
        assert exc.value.to == "served"

        # Cannot move backwards from published bill
        with pytest.raises(InvalidTransition):
            sm.resolve("bill_published", "bill_generated", sm.CARETAKER)

        # Nonexistent states
        assert not sm.is_legal("nonexistent", "state")

    def test_allowed_targets(self):
        targets = sm.allowed_targets("requested", sm.CARETAKER)
        assert "approved" in targets
        assert "rejected" in targets
        assert "served" not in targets
