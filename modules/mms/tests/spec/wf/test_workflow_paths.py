from __future__ import annotations

import pytest

from modules.mms.domain import state_machine as sm

CARETAKER = sm.CARETAKER
STUDENT = sm.STUDENT
SYSTEM = sm.SYSTEM

WORKFLOW_PATHS = [
    pytest.param("WF-BW-MMS-01", "BW-MMS-01 approval path", [("window_closed", "window_open", CARETAKER), ("window_open", "registration_pending", STUDENT), ("registration_pending", "registration_approved", CARETAKER)], id="WF-BW-MMS-01__BW-MMS-01"),
    pytest.param("WF-BW-MMS-02", "BW-MMS-02 rejection path", [("window_closed", "window_open", CARETAKER), ("window_open", "registration_pending", STUDENT), ("registration_pending", "registration_rejected", CARETAKER)], id="WF-BW-MMS-02__BW-MMS-02"),
    pytest.param("WF-CW-MMS-01", "CW-MMS-01 registration lifecycle", [("window_closed", "window_open", CARETAKER), ("window_open", "registration_pending", STUDENT), ("registration_pending", "registration_approved", CARETAKER), ("window_closed", "window_open", CARETAKER), ("window_open", "registration_pending", STUDENT), ("registration_pending", "registration_rejected", CARETAKER)], id="WF-CW-MMS-01__CW-MMS-01"),
    pytest.param("WF-BW-MMS-03", "BW-MMS-03 approved deregistration path", [("student_registered", "deregistration_pending", STUDENT), ("deregistration_pending", "deregistration_approved_awaiting_date", CARETAKER), ("deregistration_approved_awaiting_date", "student_deregistered", SYSTEM)], id="WF-BW-MMS-03__BW-MMS-03"),
    pytest.param("WF-BW-MMS-04", "BW-MMS-04 rejected deregistration path", [("student_registered", "deregistration_pending", STUDENT), ("deregistration_pending", "deregistration_rejected", CARETAKER)], id="WF-BW-MMS-04__BW-MMS-04"),
    pytest.param("WF-CW-MMS-02", "CW-MMS-02 deregistration lifecycle", [("student_registered", "deregistration_pending", STUDENT), ("deregistration_pending", "deregistration_approved_awaiting_date", CARETAKER), ("deregistration_approved_awaiting_date", "student_deregistered", SYSTEM), ("student_registered", "deregistration_pending", STUDENT), ("deregistration_pending", "deregistration_rejected", CARETAKER)], id="WF-CW-MMS-02__CW-MMS-02"),
    pytest.param("WF-BW-MMS-05", "BW-MMS-05 rebate approved as submitted", [("no_rebate", "rebate_pending", STUDENT), ("rebate_pending", "rebate_approved", CARETAKER)], id="WF-BW-MMS-05__BW-MMS-05"),
    pytest.param("WF-BW-MMS-06", "BW-MMS-06 rebate approved with modified dates", [("no_rebate", "rebate_pending", STUDENT), ("rebate_pending", "rebate_approved_modified_dates", CARETAKER)], id="WF-BW-MMS-06__BW-MMS-06"),
    pytest.param("WF-BW-MMS-07", "BW-MMS-07 rebate rejected", [("no_rebate", "rebate_pending", STUDENT), ("rebate_pending", "rebate_rejected", CARETAKER)], id="WF-BW-MMS-07__BW-MMS-07"),
    pytest.param("WF-CW-MMS-03", "CW-MMS-03 rebate lifecycle", [("no_rebate", "rebate_pending", STUDENT), ("rebate_pending", "rebate_approved", CARETAKER), ("no_rebate", "rebate_pending", STUDENT), ("rebate_pending", "rebate_approved_modified_dates", CARETAKER), ("no_rebate", "rebate_pending", STUDENT), ("rebate_pending", "rebate_rejected", CARETAKER)], id="WF-CW-MMS-03__CW-MMS-03"),
    pytest.param("WF-BW-MMS-08", "BW-MMS-08 vacation Yes response", [("survey_not_created", "survey_open", CARETAKER), ("survey_open", "response_yes", STUDENT)], id="WF-BW-MMS-08__BW-MMS-08"),
    pytest.param("WF-BW-MMS-09", "BW-MMS-09 vacation No response", [("survey_not_created", "survey_open", CARETAKER), ("survey_open", "response_no", STUDENT)], id="WF-BW-MMS-09__BW-MMS-09"),
    pytest.param("WF-BW-MMS-10", "BW-MMS-10 vacation default No", [("survey_not_created", "survey_open", CARETAKER), ("survey_open", "response_default_no", SYSTEM)], id="WF-BW-MMS-10__BW-MMS-10"),
    pytest.param("WF-CW-MMS-04", "CW-MMS-04 vacation response lifecycle", [("survey_not_created", "survey_open", CARETAKER), ("survey_open", "response_yes", STUDENT), ("survey_not_created", "survey_open", CARETAKER), ("survey_open", "response_no", STUDENT), ("survey_not_created", "survey_open", CARETAKER), ("survey_open", "response_default_no", SYSTEM)], id="WF-CW-MMS-04__CW-MMS-04"),
    pytest.param("WF-BW-MMS-11", "BW-MMS-11 special-food rejected", [("no_request", "requested", STUDENT), ("requested", "rejected", CARETAKER)], id="WF-BW-MMS-11__BW-MMS-11"),
    pytest.param("WF-BW-MMS-12", "BW-MMS-12 special-food default rejected", [("no_request", "requested", STUDENT), ("requested", "rejected_default", SYSTEM)], id="WF-BW-MMS-12__BW-MMS-12"),
    pytest.param("WF-BW-MMS-13", "BW-MMS-13 special-food approved", [("no_request", "requested", STUDENT), ("requested", "approved", CARETAKER)], id="WF-BW-MMS-13__BW-MMS-13"),
    pytest.param("WF-BW-MMS-14", "BW-MMS-14 special-food served", [("no_request", "requested", STUDENT), ("requested", "approved", CARETAKER), ("approved", "served", CARETAKER)], id="WF-BW-MMS-14__BW-MMS-14"),
    pytest.param("WF-BW-MMS-15", "BW-MMS-15 special-food cancelled", [("no_request", "requested", STUDENT), ("requested", "approved", CARETAKER), ("approved", "cancelled", CARETAKER)], id="WF-BW-MMS-15__BW-MMS-15"),
    pytest.param("WF-CW-MMS-05", "CW-MMS-05 special-food lifecycle", [("no_request", "requested", STUDENT), ("requested", "approved", CARETAKER), ("approved", "served", CARETAKER), ("no_request", "requested", STUDENT), ("requested", "approved", CARETAKER), ("approved", "cancelled", CARETAKER), ("no_request", "requested", STUDENT), ("requested", "rejected", CARETAKER), ("no_request", "requested", STUDENT), ("requested", "rejected_default", SYSTEM)], id="WF-CW-MMS-05__CW-MMS-05"),
    pytest.param("WF-BW-MMS-16", "BW-MMS-16 monthly bills generated to published", [("bill_not_generated", "bill_generated", SYSTEM), ("bill_generated", "bill_finalized", CARETAKER), ("bill_finalized", "bill_published", CARETAKER)], id="WF-BW-MMS-16__BW-MMS-16"),
]


@pytest.mark.parametrize(("test_id", "source_id", "path"), WORKFLOW_PATHS)
def test_specified_workflow_path_accepts_each_transition(test_id, source_id, path):
    """Each test_id and source_id name the frozen workflow design obligation."""
    for from_state, to_state, actor in path:
        sm.resolve(from_state, to_state, actor)
