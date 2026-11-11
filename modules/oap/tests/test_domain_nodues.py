import pytest

from modules.oap.domain import nodues
from modules.oap.domain.errors import InvalidTransition


def _results(default=nodues.RESULT_CLEAR, **overrides):
    results = dict.fromkeys(nodues.DOMAIN_CODES, default)
    results.update(overrides)
    return results


def test_authorities_has_exactly_seven_entries():
    assert len(nodues.AUTHORITIES) == 7
    assert nodues.DOMAIN_CODES == [
        "library",
        "hostel",
        "mess",
        "department",
        "lab",
        "academic_section",
        "student_section",
    ]


def test_submit_from_no_case():
    assert nodues.submit(nodues.NO_CASE) == nodues.IN_PROGRESS


def test_submit_from_in_progress_raises():
    with pytest.raises(InvalidTransition):
        nodues.submit(nodues.IN_PROGRESS)


def test_pending_results_stay_in_progress():
    results = _results(lab=nodues.RESULT_PENDING)
    assert nodues.state_after_results(nodues.IN_PROGRESS, results) == nodues.IN_PROGRESS


def test_all_pending_stays_in_progress():
    results = _results(default=nodues.RESULT_PENDING)
    assert nodues.state_after_results(nodues.IN_PROGRESS, results) == nodues.IN_PROGRESS


def test_pending_with_dues_stays_in_progress():
    results = _results(
        library=nodues.RESULT_DUES, mess=nodues.RESULT_PENDING
    )
    assert nodues.state_after_results(nodues.IN_PROGRESS, results) == nodues.IN_PROGRESS


def test_all_clear():
    assert (
        nodues.state_after_results(nodues.IN_PROGRESS, _results())
        == nodues.ALL_CLEAR
    )


@pytest.mark.parametrize("code", ["library", "lab", "student_section"])
def test_one_dues_outstanding(code):
    results = _results(**{code: nodues.RESULT_DUES})
    assert (
        nodues.state_after_results(nodues.IN_PROGRESS, results)
        == nodues.DUES_OUTSTANDING
    )


@pytest.mark.parametrize(
    "state",
    [nodues.ALL_CLEAR, nodues.DUES_OUTSTANDING, nodues.FINALIZED],
)
def test_recording_results_outside_in_progress_raises(state):
    with pytest.raises(InvalidTransition):
        nodues.state_after_results(state, _results())


def test_recording_results_from_no_case_raises():
    with pytest.raises(InvalidTransition):
        nodues.state_after_results(nodues.NO_CASE, _results())


def test_finalize_from_all_clear():
    assert nodues.finalize(nodues.ALL_CLEAR, _results()) == nodues.FINALIZED


@pytest.mark.parametrize(
    "state",
    [nodues.IN_PROGRESS, nodues.DUES_OUTSTANDING, nodues.FINALIZED],
)
def test_finalize_from_other_states_raises(state):
    with pytest.raises(InvalidTransition):
        nodues.finalize(state, _results())


def test_finalize_requires_all_results_clear():
    with pytest.raises(InvalidTransition):
        nodues.finalize(
            nodues.ALL_CLEAR, _results(hostel=nodues.RESULT_DUES)
        )


def test_state_choices_exclude_start_state():
    assert nodues.START_STATE not in [v for v, _ in nodues.STATE_CHOICES]
    assert len(nodues.STATE_CHOICES) == 4


def test_terminal_states():
    assert {nodues.DUES_OUTSTANDING, nodues.FINALIZED} == nodues.TERMINAL_STATES


def test_verify_permission():
    assert nodues.verify_permission("lab") == "oap.nodues.verify_lab"


def test_verify_permission_unknown_code_raises():
    with pytest.raises(ValueError):
        nodues.verify_permission("canteen")
