"""Pure-Python rules: no database."""
import pytest

from modules.dept.domain import state_machine as sm
from modules.dept.domain.visibility import (
    IncompleteAnnouncement,
    Viewer,
    is_visible,
    validate_publication,
)


# -- stock lifecycle -------------------------------------------------------------
def test_hod_can_approve_or_reject_pending():
    for to in (sm.APPROVED, sm.REJECTED):
        sm.validate_transition(sm.STOCK_TRANSITIONS, sm.PENDING_HOD, to,
                               {"dept.stock_request.decide"})


def test_dept_admin_cannot_approve():                      # BR-DEPT-006
    with pytest.raises(sm.ActorNotAllowed):
        sm.validate_transition(sm.STOCK_TRANSITIONS, sm.PENDING_HOD, sm.APPROVED,
                               {"dept.stock_request.issue"})


def test_cannot_issue_unapproved_request():                # BR-DEPT-007
    with pytest.raises(sm.InvalidTransition):
        sm.validate_transition(sm.STOCK_TRANSITIONS, sm.PENDING_HOD, sm.ISSUED,
                               {"dept.stock_request.issue"})


def test_approved_request_can_be_issued_by_dept_admin():
    sm.validate_transition(sm.STOCK_TRANSITIONS, sm.APPROVED, sm.ISSUED,
                           {"dept.stock_request.issue"})


@pytest.mark.parametrize("status", sorted(sm.STOCK_TERMINAL))
def test_terminal_stock_states_have_no_exit(status):
    assert not [t for t in sm.STOCK_TRANSITIONS if t.frm == status]


# -- feedback lifecycle ----------------------------------------------------------
def test_feedback_must_be_reviewed_before_disposal():      # BR-DEPT-018
    with pytest.raises(sm.InvalidTransition):
        sm.validate_transition(sm.FEEDBACK_TRANSITIONS, sm.NEW, sm.CLOSED,
                               {"dept.feedback.review"})


@pytest.mark.parametrize("perm", ["dept.feedback.review",
                                  "dept.feedback.resolve"])
@pytest.mark.parametrize("to", [sm.RESOLVED, sm.CLOSED])
def test_dept_admin_or_hod_can_dispose(perm, to):          # BR-DEPT-009
    sm.validate_transition(sm.FEEDBACK_TRANSITIONS, sm.UNDER_REVIEW, to, {perm})


def test_hod_cannot_do_the_initial_review():
    with pytest.raises(sm.ActorNotAllowed):
        sm.validate_transition(sm.FEEDBACK_TRANSITIONS, sm.NEW, sm.UNDER_REVIEW,
                               {"dept.feedback.resolve"})


@pytest.mark.parametrize("status", sorted(sm.FEEDBACK_TERMINAL))
def test_terminal_feedback_states_have_no_exit(status):
    assert not [t for t in sm.FEEDBACK_TRANSITIONS if t.frm == status]


# -- announcement targeting ------------------------------------------------------
def test_untargeted_announcement_reaches_everyone():
    assert is_visible(roles=[], programmes=[], years=[],
                      viewer=Viewer(role="student"))


def test_role_targeting():
    kw = {"programmes": [], "years": []}
    assert is_visible(roles=["faculty"], viewer=Viewer(role="faculty"), **kw)
    assert not is_visible(roles=["faculty"], viewer=Viewer(role="student"), **kw)


def test_all_three_axes_must_match():                      # BR-DEPT-002
    ann = {"roles": ["student"], "programmes": ["B.Tech"], "years": [2024]}
    assert is_visible(viewer=Viewer("student", "B.Tech", 2024), **ann)
    assert not is_visible(viewer=Viewer("student", "M.Tech", 2024), **ann)
    assert not is_visible(viewer=Viewer("student", "B.Tech", 2023), **ann)


def test_year_targeted_notice_hidden_from_viewer_without_batch():
    assert not is_visible(roles=[], programmes=[], years=[2024],
                          viewer=Viewer("faculty"))


@pytest.mark.parametrize("title,body,roles,years", [
    ("", "body", [], []), ("t", "  ", [], []),
    ("t", "b", ["janitor"], []), ("t", "b", [], [24]),
])
def test_incomplete_announcement_is_blocked(title, body, roles, years):  # BR-003
    with pytest.raises(IncompleteAnnouncement):
        validate_publication(title, body, roles, [], years)
