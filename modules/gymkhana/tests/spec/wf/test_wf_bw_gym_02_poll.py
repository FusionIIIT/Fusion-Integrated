"""A8 WF tests - BW-GYM-02 voting poll workflow.

Generated from the frozen WF_DESIGN.json. Every case is NOT_AUTOMATED because
the A8_BASE backend has no Gymkhana functionality to drive (see each skip reason).
"""
import pytest


@pytest.mark.skip(reason="NOT_AUTOMATED: A8_BASE contains no Gymkhana module (INSTALLED_APPS has only modules.directory, modules.accesscontrol, modules.placement; config/urls.py mounts no gymkhana routes; registry/permissions.json defines no gymkhana permissions or roles); specifically no Poll / poll-choice / target-group / vote model, no UC-GYM-006 (Create Voting Poll) or UC-GYM-007 (Vote in Poll) service or endpoint, and no 'Club Head' role. The specified action cannot be executed through any existing backend interface.")
def test_wf_t08_positive():
    """WF-T08 | source_id: BW-GYM-02 transition 1 (Poll Not Available → Poll Open / Target Audience Defined / Student Not Yet Voted) via UC-GYM-006

    purpose: Verify that the applicable Club Head can create a poll with at least two choices and valid target groups, moving the workflow to the open poll state.
    test_type: positive
    preconditions: No poll exists. The acting user is the applicable Club Head. At least one valid student target group exists.
    action_or_input: The Club Head creates a poll with two or more choices and valid selected target groups (UC-GYM-006 / Create Voting Poll).
    expected_result: Poll creation succeeds. The poll is open, its target audience is the selected groups, and no student in the target audience has yet voted.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: A8_BASE contains no Gymkhana module (INSTALLED_APPS has only modules.directory, modules.accesscontrol, modules.placement; config/urls.py mounts no gymkhana routes; registry/permissions.json defines no gymkhana permissions or roles); specifically no Poll / poll-choice / target-group / vote model, no UC-GYM-006 (Create Voting Poll) or UC-GYM-007 (Vote in Poll) service or endpoint, and no 'Club Head' role. The specified action cannot be executed through any existing backend interface.")
def test_wf_t09_positive():
    """WF-T09 | source_id: BW-GYM-02 transition 2 (Student Not Yet Voted → Student Vote Recorded) via UC-GYM-007

    purpose: Verify that an eligible targeted student can record one vote in an active poll.
    test_type: positive
    preconditions: A poll is open, active/unexpired, with a defined target audience. The student belongs to the target audience and has not voted.
    action_or_input: The student votes for one of the poll choices (UC-GYM-007 / Vote in Poll).
    expected_result: The vote is accepted and recorded for that student. The poll remains open with the target audience defined, and the student's state becomes 'Student Vote Recorded'.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: A8_BASE contains no Gymkhana module (INSTALLED_APPS has only modules.directory, modules.accesscontrol, modules.placement; config/urls.py mounts no gymkhana routes; registry/permissions.json defines no gymkhana permissions or roles); specifically no Poll / poll-choice / target-group / vote model, no UC-GYM-006 (Create Voting Poll) or UC-GYM-007 (Vote in Poll) service or endpoint, and no 'Club Head' role. The specified action cannot be executed through any existing backend interface.")
def test_wf_t10_positive():
    """WF-T10 | source_id: BW-GYM-02 end-to-end path (transitions 1→2)

    purpose: Verify the complete finite path from poll creation by a Club Head to one eligible targeted student recording one vote.
    test_type: positive
    preconditions: An applicable Club Head and a student belonging to a valid target group exist. No poll exists.
    action_or_input: Step 1: the Club Head creates a poll with at least two choices targeting the student's group (UC-GYM-006). Step 2: the targeted student votes (UC-GYM-007).
    expected_result: After step 1: 'Poll Open / Target Audience Defined / Student Not Yet Voted'. After step 2: 'Poll Open / Target Audience Defined / Student Vote Recorded'. The states occur in this order.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: A8_BASE contains no Gymkhana module (INSTALLED_APPS has only modules.directory, modules.accesscontrol, modules.placement; config/urls.py mounts no gymkhana routes; registry/permissions.json defines no gymkhana permissions or roles); specifically no Poll / poll-choice / target-group / vote model, no UC-GYM-006 (Create Voting Poll) or UC-GYM-007 (Vote in Poll) service or endpoint, and no 'Club Head' role. The specified action cannot be executed through any existing backend interface.")
def test_wf_t11_negative():
    """WF-T11 | source_id: BW-GYM-02 transition 1 guard: at least two choices (negative)

    purpose: Verify that poll creation fails when fewer than two choices are supplied.
    test_type: negative
    preconditions: The acting user is the applicable Club Head. A valid target group exists.
    action_or_input: The Club Head attempts to create a poll with only one choice (UC-GYM-006).
    expected_result: Creation is rejected. No poll is created and the workflow remains at 'Poll Not Available'.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: A8_BASE contains no Gymkhana module (INSTALLED_APPS has only modules.directory, modules.accesscontrol, modules.placement; config/urls.py mounts no gymkhana routes; registry/permissions.json defines no gymkhana permissions or roles); specifically no Poll / poll-choice / target-group / vote model, no UC-GYM-006 (Create Voting Poll) or UC-GYM-007 (Vote in Poll) service or endpoint, and no 'Club Head' role. The specified action cannot be executed through any existing backend interface.")
def test_wf_t12_negative():
    """WF-T12 | source_id: BW-GYM-02 transition 1 guard: valid target groups (negative)

    purpose: Verify that poll creation fails when the target groups are invalid.
    test_type: negative
    preconditions: The acting user is the applicable Club Head.
    action_or_input: The Club Head attempts to create a poll with at least two choices but with an invalid target group (UC-GYM-006). (Ambiguity: the specification does not define what makes a group invalid or whether an empty target selection counts as invalid; the test uses a group identifier that does not exist.)
    expected_result: Creation is rejected. No poll is created and the workflow remains at 'Poll Not Available'.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: A8_BASE contains no Gymkhana module (INSTALLED_APPS has only modules.directory, modules.accesscontrol, modules.placement; config/urls.py mounts no gymkhana routes; registry/permissions.json defines no gymkhana permissions or roles); specifically no Poll / poll-choice / target-group / vote model, no UC-GYM-006 (Create Voting Poll) or UC-GYM-007 (Vote in Poll) service or endpoint, and no 'Club Head' role. The specified action cannot be executed through any existing backend interface.")
def test_wf_t13_negative():
    """WF-T13 | source_id: BW-GYM-02 transition 1 guard: actor is applicable Club Head (negative)

    purpose: Verify that a user who is not the applicable Club Head cannot create a poll.
    test_type: negative
    preconditions: The acting user is not an applicable Club Head (e.g., an ordinary student).
    action_or_input: The user attempts to create a poll with at least two choices and valid target groups (UC-GYM-006).
    expected_result: Creation is rejected. No poll is created and the workflow remains at 'Poll Not Available'.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: A8_BASE contains no Gymkhana module (INSTALLED_APPS has only modules.directory, modules.accesscontrol, modules.placement; config/urls.py mounts no gymkhana routes; registry/permissions.json defines no gymkhana permissions or roles); specifically no Poll / poll-choice / target-group / vote model, no UC-GYM-006 (Create Voting Poll) or UC-GYM-007 (Vote in Poll) service or endpoint, and no 'Club Head' role. The specified action cannot be executed through any existing backend interface.")
def test_wf_t14_negative():
    """WF-T14 | source_id: BW-GYM-02 transition 2 guard: poll active/unexpired (negative)

    purpose: Verify that a targeted student cannot vote in an expired poll.
    test_type: negative
    preconditions: A poll exists whose active period has expired. The student belongs to the target audience and has not voted.
    action_or_input: The student attempts to vote (UC-GYM-007).
    expected_result: The vote is rejected. No vote is recorded and the student's state remains 'Student Not Yet Voted'.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: A8_BASE contains no Gymkhana module (INSTALLED_APPS has only modules.directory, modules.accesscontrol, modules.placement; config/urls.py mounts no gymkhana routes; registry/permissions.json defines no gymkhana permissions or roles); specifically no Poll / poll-choice / target-group / vote model, no UC-GYM-006 (Create Voting Poll) or UC-GYM-007 (Vote in Poll) service or endpoint, and no 'Club Head' role. The specified action cannot be executed through any existing backend interface.")
def test_wf_t15_negative():
    """WF-T15 | source_id: BW-GYM-02 transition 2 guard: student belongs to target audience (negative)

    purpose: Verify that a student outside the target audience cannot vote.
    test_type: negative
    preconditions: A poll is open and active, targeted at specific groups. The student does not belong to any targeted group.
    action_or_input: The non-targeted student attempts to vote (UC-GYM-007).
    expected_result: The vote is rejected. No vote is recorded for that student.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: A8_BASE contains no Gymkhana module (INSTALLED_APPS has only modules.directory, modules.accesscontrol, modules.placement; config/urls.py mounts no gymkhana routes; registry/permissions.json defines no gymkhana permissions or roles); specifically no Poll / poll-choice / target-group / vote model, no UC-GYM-006 (Create Voting Poll) or UC-GYM-007 (Vote in Poll) service or endpoint, and no 'Club Head' role. The specified action cannot be executed through any existing backend interface.")
def test_wf_t16_negative():
    """WF-T16 | source_id: BW-GYM-02 transition 2 guard: student has not voted (negative)

    purpose: Verify that a student who has already voted cannot vote a second time.
    test_type: negative
    preconditions: A poll is open and active. The targeted student's state is 'Student Vote Recorded'.
    action_or_input: The same student attempts to vote again (UC-GYM-007).
    expected_result: The second vote is rejected. Only the original vote remains recorded and the student's state remains 'Student Vote Recorded'.
    """
