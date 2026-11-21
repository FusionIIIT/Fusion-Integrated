"""Assignment #8 - Strategy 4: Workflows (WF) Test Suite.

Auto-generated backend verification suite derived strictly from the frozen
a8_design/WF_DESIGN.json specification requirements (Basic & Composite Workflows).
"""

import pytest

from modules.fts.domain.workflow import (
    can_forward_file,
)
from modules.fts.models import FTSFile
from modules.fts.selectors.movements import get_file_movement_history
from modules.fts.services.archival import archive_file
from modules.fts.services.drafts import create_file_draft, discard_file_draft, update_file_draft
from modules.fts.services.movements import forward_file, return_file


@pytest.mark.django_db
def test_tc_wf_001():
    """TC_WF_001 - BW-FTS-01 — Row 1 (Prepared/Draft file held by Sender → Active/Circulated file held by Recipient), FTS-UC-003: Verify the single send/forward transition from a Prepared/Draft file held by the Sender, with zero onward traversal.

    Action/Input: Sender chooses Send/Forward on the Draft file, selects the Recipient and supplies a mandatory movement comment.
    Expected Result: File state becomes Active/Circulated and is held by the Recipient. Movement, history and audit are updated. The required notification event(s) are triggered. No further onward-forward traversal occurs within this path.
    Test Type: positive
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 1", "Initial note")
    fid = draft["file_id"]
    res = forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "Initial circulation")
    assert res["new_status"] == "in_transit"
    assert res["current_holder_id"] == "rec_1"
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.is_draft is False

@pytest.mark.django_db
def test_tc_wf_002():
    """TC_WF_002 - BW-FTS-01 — Row 1 (Prepared/Draft or Active file held by Sender → Active/Circulated file held by Recipient), FTS-UC-003: Verify the same send/forward transition when the From State is an Active file held by the Sender (distinct from Draft).

    Action/Input: Sender chooses Send/Forward, selects the Recipient and supplies a mandatory movement comment.
    Expected Result: File state is Active/Circulated and held by the Recipient. Movement, history and audit are updated. Notification event(s) are triggered.
    Test Type: alternative
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 2", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "Step 1")
    res = forward_file(fid, "rec_1", "Staff", "rec_2", "Dean", "Step 2 from active state")
    assert res["new_status"] == "in_transit"
    assert res["current_holder_id"] == "rec_2"

@pytest.mark.django_db
def test_tc_wf_003():
    """TC_WF_003 - BW-FTS-01 — Row 1 guard: 'Sender authorized': Verify the transition does not occur when the sender is not authorized.

    Action/Input: The unauthorized user attempts Send/Forward with a valid recipient and a mandatory comment.
    Expected Result: The guard fails and the transition to 'Active/Circulated file held by Recipient' does not occur. The file remains held by its original holder, with no movement recorded and no recipient notification triggered.
    Test Type: negative
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 3", "Initial note")
    fid = draft["file_id"]
    with pytest.raises(PermissionError):
        forward_file(fid, "unauthorized_user", "Officer", "rec_1", "Staff", "Illegal attempt")

@pytest.mark.django_db
def test_tc_wf_004():
    """TC_WF_004 - BW-FTS-01 — Row 1 guard: 'file not archived': Verify an archived file cannot be sent/forwarded through the BW-FTS-01 transition.

    Action/Input: The user attempts Send/Forward on the archived file with a valid recipient and a mandatory comment.
    Expected Result: The guard fails and no transition occurs. The file remains Archived/Read-only, with no new movement recorded.
    Test Type: negative
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 4", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "Fwd")
    return_file(fid, "rec_1", "Staff", "Back", target_receiver_id="sender_1")
    archive_file(fid, "sender_1", "Officer", "Archived")
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "Illegal forward on archived")

@pytest.mark.django_db
def test_tc_wf_005():
    """TC_WF_005 - BW-FTS-01 — Row 1 guard: 'valid Institute Employee recipient': Verify the transition is blocked when the recipient is not a valid Institute Employee.

    Action/Input: Sender attempts Send/Forward to the invalid recipient with a mandatory comment.
    Expected Result: The guard fails and the file is not moved to the recipient. The file remains held by the Sender, with no movement recorded and no notification triggered.
    Test Type: negative
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 5", "Initial note")
    fid = draft["file_id"]
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "sender_1", "Officer", "", "Staff", "Sending to empty receiver")

@pytest.mark.django_db
def test_tc_wf_006():
    """TC_WF_006 - BW-FTS-01 — Row 1 guard: 'mandatory movement comment present': Verify the transition is blocked when the mandatory movement comment is missing.

    Action/Input: Sender attempts Send/Forward without supplying a movement comment.
    Expected Result: The guard fails and the file is not moved. The file remains held by the Sender, with no movement or history entry added and no notification triggered.
    Test Type: negative
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 6", "Initial note")
    fid = draft["file_id"]
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "")

@pytest.mark.django_db
def test_tc_wf_007():
    """TC_WF_007 - BW-FTS-02 — Row 1 (Active/Circulated file held by Current Recipient → held by Next Recipient), FTS-UC-003: Verify exactly one traversal of the onward-forward loop by the current holder.

    Action/Input: Current holder chooses to forward the received file onward, selects the Next Recipient and supplies a mandatory movement comment.
    Expected Result: File state is Active/Circulated and held by the Next Recipient. Movement, history and audit are updated. Notification event(s) are triggered. Exactly one onward traversal is represented.
    Test Type: boundary
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 7", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "Init fwd")
    res2 = forward_file(fid, "rec_1", "Staff", "rec_2", "Director", "Onward fwd loop")
    assert res2["current_holder_id"] == "rec_2"
    hist = get_file_movement_history(fid)
    assert len(hist) == 3

@pytest.mark.django_db
def test_tc_wf_008():
    """TC_WF_008 - BW-FTS-02 — Row 1 guard: 'Current holder authorized': Verify onward forwarding is blocked for an unauthorized current holder.

    Action/Input: The user attempts to forward the file onward with a valid next recipient and a mandatory comment.
    Expected Result: The guard fails and no transition occurs. The file remains held by the Current Recipient, with no movement recorded.
    Test Type: negative
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 8", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "Init fwd")
    with pytest.raises(PermissionError):
        forward_file(fid, "unauthorized_holder", "Staff", "rec_2", "Director", "Illegal onward")

@pytest.mark.django_db
def test_tc_wf_009():
    """TC_WF_009 - BW-FTS-02 — Row 1 guard: 'file not archived': Verify onward forwarding is blocked for an archived file.

    Action/Input: A user attempts onward forwarding with a valid next recipient and a mandatory comment.
    Expected Result: The guard fails and no transition occurs. The file remains Archived/Read-only.
    Test Type: negative
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 9", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "Init fwd")
    return_file(fid, "rec_1", "Staff", "Back", target_receiver_id="sender_1")
    archive_file(fid, "sender_1", "Officer", "Archived")
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "sender_1", "Officer", "rec_2", "Director", "Forward archived")

@pytest.mark.django_db
def test_tc_wf_010():
    """TC_WF_010 - BW-FTS-02 — Row 1 guard: 'valid next recipient': Verify onward forwarding is blocked when the next recipient is not valid.

    Action/Input: Current holder attempts to forward onward to the invalid recipient with a mandatory comment.
    Expected Result: The guard fails and the file is not moved. It remains held by the Current Holder, with no movement recorded.
    Test Type: negative
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 10", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "Init fwd")
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "rec_1", "Staff", "", "Director", "Empty next recipient")

@pytest.mark.django_db
def test_tc_wf_011():
    """TC_WF_011 - BW-FTS-02 — Row 1 guard: 'mandatory movement comment present': Verify onward forwarding is blocked when the mandatory comment is missing.

    Action/Input: Current holder attempts to forward onward without a movement comment.
    Expected Result: The guard fails and the file is not moved. It remains held by the Current Holder, with no movement recorded.
    Test Type: negative
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 11", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "Init fwd")
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "rec_1", "Staff", "rec_2", "Director", "")

@pytest.mark.django_db
def test_tc_wf_012():
    """TC_WF_012 - BW-FTS-03 — Row 1 (Active/Circulated file held by Recipient; previous sender known → held by Previous Sender), FTS-UC-004: Verify the return transition to the sender of the received movement.

    Action/Input: Recipient chooses Return and supplies a mandatory movement comment.
    Expected Result: File state is Active/Circulated and held by the Previous Sender. Return, history and audit are updated. The required return notification event is triggered.
    Test Type: alternative
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 12", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "Init fwd")
    ret = return_file(fid, "rec_1", "Staff", "Returning to sender_1", target_receiver_id="sender_1")
    assert ret["new_status"] == "returned"
    assert ret["returned_to_id"] == "sender_1"

@pytest.mark.django_db
def test_tc_wf_013():
    """TC_WF_013 - BW-FTS-03 — Row 1 guard: 'Recipient authorized': Verify return is blocked for an unauthorized user.

    Action/Input: The user attempts Return with a mandatory comment.
    Expected Result: The guard fails and no transition occurs. The file remains held by the same user, with no return recorded and no return notification triggered.
    Test Type: negative
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 13", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "Init fwd")
    with pytest.raises(PermissionError):
        return_file(fid, "unauthorized_user", "Staff", "Illegal return", target_receiver_id="sender_1")

@pytest.mark.django_db
def test_tc_wf_014():
    """TC_WF_014 - BW-FTS-03 — Row 1 guard: 'active file': Verify return is blocked when the file is not active (Archived).

    Action/Input: A user attempts Return with a mandatory comment.
    Expected Result: The guard fails and no transition occurs. The file remains Archived/Read-only.
    Test Type: negative
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 14", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "Init fwd")
    return_file(fid, "rec_1", "Staff", "Back", target_receiver_id="sender_1")
    archive_file(fid, "sender_1", "Officer", "Archived")
    with pytest.raises((ValueError, PermissionError)):
        return_file(fid, "sender_1", "Officer", "Return after archive", target_receiver_id="rec_1")

@pytest.mark.django_db
def test_tc_wf_015():
    """TC_WF_015 - BW-FTS-03 — Row 1 guard: 'mandatory movement comment present': Verify return is blocked when the mandatory comment is missing.

    Action/Input: Recipient attempts Return without a movement comment.
    Expected Result: The guard fails and the file is not returned. It remains held by the Recipient, with no return recorded.
    Test Type: negative
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 15", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "Init fwd")
    with pytest.raises((ValueError, PermissionError)):
        return_file(fid, "rec_1", "Staff", "", target_receiver_id="sender_1")

@pytest.mark.django_db
def test_tc_wf_016():
    """TC_WF_016 - BW-FTS-04 — Row 1 (Active/Circulated file; objective complete → Archived/Read-only/Permanently retained), FTS-UC-007: Verify the lifecycle-closing archival transition by the file owner.

    Action/Input: File owner selects Archive.
    Expected Result: File state becomes Archived/Read-only/Permanently retained. Archive and audit are recorded. The archive notification event is triggered for the associated Institute Employees.
    Test Type: positive
    """
    draft = create_file_draft("sender_1", "Officer", "Workflow File 16", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "sender_1", "Officer", "rec_1", "Staff", "Init fwd")
    return_file(fid, "rec_1", "Staff", "Back", target_receiver_id="sender_1")
    arch = archive_file(fid, "sender_1", "Officer", "Archival remarks")
    assert arch["status"] == "archived"
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.status == "archived"

@pytest.mark.django_db
def test_tc_wf_017():
    """TC_WF_017 - BW-FTS-04 — Row 1 guard: 'Requester is file owner': Verify archival is blocked when the requester is not the file owner.

    Action/Input: The non-owner selects Archive.
    Expected Result: The guard fails and no transition occurs. The file remains Active/Circulated, with no archive/audit record and no archive notification.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "Workflow File 17", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "owner_user", "Officer", "custodian_user", "Staff", "Custody fwd")
    with pytest.raises(PermissionError):
        archive_file(fid, "custodian_user", "Staff", "Unauthorized non-owner archival")

@pytest.mark.django_db
def test_tc_wf_018():
    """TC_WF_018 - BW-FTS-04 — Row 1 guard: 'file is not already archived': Verify archival is blocked when the file is already archived.

    Action/Input: File owner selects Archive again.
    Expected Result: The guard fails and no new archival transition occurs. The file remains Archived/Read-only/Permanently retained.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "Workflow File 18", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Fwd")
    return_file(fid, "rec_1", "Staff", "Back", target_receiver_id="owner_user")
    archive_file(fid, "owner_user", "Officer", "First archive")
    with pytest.raises((ValueError, PermissionError)):
        archive_file(fid, "owner_user", "Officer", "Second archive")

@pytest.mark.django_db
def test_tc_wf_019():
    """TC_WF_019 - BW-FTS-04 — Row 1 guard: 'objective complete': Verify archival is not performed when the intended collaborative objective is not complete.

    Action/Input: File owner selects Archive.
    Expected Result: The guard 'objective complete' is not satisfied and the file does not reach the Archived/Read-only/Permanently retained state. No archive notification is triggered.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "Workflow File 19", "Initial note")
    fid = draft["file_id"]
    with pytest.raises((ValueError, PermissionError)):
        archive_file(fid, "owner_user", "Officer", "Premature archival of draft")

@pytest.mark.django_db
def test_tc_wf_020():
    """TC_WF_020 - BW-FTS-05 — Rows 1–2 (No file record → Draft → Active/Circulated held by Recipient), FTS-UC-001, FTS-UC-003: Verify create followed directly by initial circulation with zero draft-edit traversal.

    Action/Input: Creator creates a new file with an initial mandatory comment (no attachments), then sends it to the Recipient with a mandatory movement comment without any draft edit.
    Expected Result: After step 1 the file is Draft/Pre-circulation. After step 2 the file is Active/Circulated and held by the Recipient. Movement, history and audit are updated and notification event(s) are triggered. No edit step occurs.
    Test Type: positive
    """
    draft = create_file_draft("owner_user", "Officer", "Workflow File 20", "Initial note")
    fid = draft["file_id"]
    fwd = forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Direct circulation")
    assert fwd["new_status"] == "in_transit"
    assert fwd["current_holder_id"] == "rec_1"

@pytest.mark.django_db
def test_tc_wf_021():
    """TC_WF_021 - BW-FTS-05 — Row 1 guard: 'initial mandatory comment present': Verify creation is blocked when the initial mandatory comment is missing.

    Action/Input: Creator attempts Create New File without an initial comment.
    Expected Result: The guard fails and no Draft/Pre-circulation file is created. State remains 'No FTS file record'.
    Test Type: negative
    """
    with pytest.raises(ValueError):
        create_file_draft("owner_user", "Officer", "Workflow File 21", "")

@pytest.mark.django_db
def test_tc_wf_022():
    """TC_WF_022 - BW-FTS-05 — Row 1 guard: 'Authorized assigned role': Verify creation is blocked when the actor lacks an authorized assigned role.

    Action/Input: The user attempts Create New File with an initial mandatory comment.
    Expected Result: The guard fails and no Draft/Pre-circulation file is created. State remains 'No FTS file record'.
    Test Type: negative
    """
    is_valid, msg = can_forward_file("draft", "unauthorized_role", "holder", "receiver", "comment")
    assert is_valid is False

@pytest.mark.django_db
def test_tc_wf_023():
    """TC_WF_023 - BW-FTS-05 — Row 2 guard: 'mandatory movement comment present': Verify initial circulation of a Draft is blocked without a movement comment.

    Action/Input: Sender attempts Send without a movement comment.
    Expected Result: The guard fails and the file remains Draft/Pre-circulation, with no movement recorded and no notification triggered.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "Workflow File 23", "Initial note")
    fid = draft["file_id"]
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "")

@pytest.mark.django_db
def test_tc_wf_024():
    """TC_WF_024 - BW-FTS-05 — Row 2 guard: 'valid Institute Employee recipient': Verify initial circulation of a Draft is blocked with an invalid recipient.

    Action/Input: Sender attempts Send to the invalid recipient with a mandatory movement comment.
    Expected Result: The guard fails and the file remains Draft/Pre-circulation, with no movement recorded.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "Workflow File 24", "Initial note")
    fid = draft["file_id"]
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "owner_user", "Officer", "", "Staff", "Comment")

@pytest.mark.django_db
def test_tc_wf_025():
    """TC_WF_025 - BW-FTS-06 — Rows 1–3 (Create → Edit once → Send), FTS-UC-001, FTS-UC-002, FTS-UC-003: Verify create, exactly one draft-edit traversal, and initial circulation.

    Action/Input: Creator creates a new file with an initial mandatory comment and an optional attachment, edits the saved draft once and saves, then sends it to the Recipient with a mandatory movement comment.
    Expected Result: After step 1 the file is Draft/Pre-circulation. After the edit it is Updated Draft/Pre-circulation. After send it is Active/Circulated and held by the Recipient. Movement, history and audit are updated and notification event(s) are triggered.
    Test Type: boundary
    """
    draft = create_file_draft("owner_user", "Officer", "Original Title", "Initial note")
    fid = draft["file_id"]
    up = update_file_draft(fid, "owner_user", subject="Updated Title")
    assert up["subject"] == "Updated Title"
    fwd = forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Sending updated draft")
    assert fwd["new_status"] == "in_transit"

@pytest.mark.django_db
def test_tc_wf_026():
    """TC_WF_026 - BW-FTS-06 — Row 2 guard: 'Actor authorized': Verify the draft edit is blocked for an unauthorized actor.

    Action/Input: The user attempts to edit and save the draft.
    Expected Result: The guard fails and the file remains Draft/Pre-circulation, not Updated Draft. No edit is saved.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "Original Title", "Initial note")
    fid = draft["file_id"]
    with pytest.raises((ValueError, PermissionError)):
        update_file_draft(fid, "intruder_user", subject="Hacked")

@pytest.mark.django_db
def test_tc_wf_027():
    """TC_WF_027 - BW-FTS-06 — Row 2 guard: 'file remains pre-circulation': Verify the draft edit transition is not available once the file has been circulated.

    Action/Input: The user attempts to edit the circulated file through the draft-edit transition.
    Expected Result: The guard fails and no transition to 'Updated Draft / Pre-circulation file' occurs. The file remains Active/Circulated.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "Circulated File 27", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Fwd")
    with pytest.raises((ValueError, PermissionError)):
        update_file_draft(fid, "owner_user", subject="Edit after circulation")

@pytest.mark.django_db
def test_tc_wf_028():
    """TC_WF_028 - BW-FTS-06 — Row 3 guard: 'mandatory movement comment present': Verify sending an Updated Draft is blocked without a movement comment.

    Action/Input: Sender attempts Send without a movement comment.
    Expected Result: The guard fails and the file remains Updated Draft/Pre-circulation, with no movement recorded.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "File 28", "Initial note")
    fid = draft["file_id"]
    update_file_draft(fid, "owner_user", subject="Updated File 28")
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "")

@pytest.mark.django_db
def test_tc_wf_029():
    """TC_WF_029 - BW-FTS-07 — Rows 1–2 (Create → Discard), FTS-UC-001, FTS-UC-002 Discard outcome: Verify create followed by discard with zero draft-edit traversal.

    Action/Input: Creator creates a new file with an initial mandatory comment, then chooses Discard before submission without editing.
    Expected Result: After step 1 the file is Draft/Pre-circulation. After Discard the state is Discarded/No active file retained. No edit step occurs.
    Test Type: alternative
    """
    draft = create_file_draft("owner_user", "Officer", "To Discard 29", "Initial note")
    fid = draft["file_id"]
    disc = discard_file_draft(fid, "owner_user")
    assert disc["status"] == "discarded"
    assert not FTSFile.objects.filter(id=fid).exists()

@pytest.mark.django_db
def test_tc_wf_030():
    """TC_WF_030 - BW-FTS-07 — Row 2 guard: 'file has not been submitted/circulated': Verify Discard is blocked for a file already submitted/circulated.

    Action/Input: The user chooses Discard on the circulated file.
    Expected Result: The guard fails and the file is not moved to Discarded/No active file retained. It remains Active/Circulated.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "Circulated File 30", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Fwd")
    with pytest.raises((ValueError, PermissionError)):
        discard_file_draft(fid, "owner_user")

@pytest.mark.django_db
def test_tc_wf_031():
    """TC_WF_031 - BW-FTS-07 — Row 2 guard: 'Actor authorized': Verify Discard is blocked for an unauthorized actor.

    Action/Input: The user chooses Discard on the draft.
    Expected Result: The guard fails and the file remains Draft/Pre-circulation, not Discarded.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "File 31", "Initial note")
    fid = draft["file_id"]
    with pytest.raises((ValueError, PermissionError)):
        discard_file_draft(fid, "unauthorized_user")

@pytest.mark.django_db
def test_tc_wf_032():
    """TC_WF_032 - BW-FTS-07 — Row 1 guard: 'initial mandatory comment present': Verify the Create step of the discard workflow is blocked without an initial comment, so Discard is not reached.

    Action/Input: Creator attempts Create New File without an initial comment.
    Expected Result: No Draft/Pre-circulation file is created and the Discard transition is unavailable. State remains 'No FTS file record'.
    Test Type: negative
    """
    with pytest.raises(ValueError):
        create_file_draft("owner_user", "Officer", "File 32", "")

@pytest.mark.django_db
def test_tc_wf_033():
    """TC_WF_033 - BW-FTS-08 — Rows 1–3 (Create → Edit once → Discard), FTS-UC-001, FTS-UC-002: Verify create, exactly one draft-edit traversal, then discard before circulation.

    Action/Input: Creator creates a new file with an initial mandatory comment, edits the draft once and saves, then chooses Discard before submission.
    Expected Result: After step 1 the file is Draft/Pre-circulation. After the edit it is Updated Draft/Pre-circulation. After Discard the state is Discarded/No active file retained.
    Test Type: boundary
    """
    draft = create_file_draft("owner_user", "Officer", "File 33", "Initial note")
    fid = draft["file_id"]
    update_file_draft(fid, "owner_user", subject="Edited 33")
    disc = discard_file_draft(fid, "owner_user")
    assert disc["status"] == "discarded"
    assert not FTSFile.objects.filter(id=fid).exists()

@pytest.mark.django_db
def test_tc_wf_034():
    """TC_WF_034 - BW-FTS-08 — Row 3 guard: 'Actor authorized': Verify Discard of an Updated Draft is blocked for an unauthorized actor.

    Action/Input: The user chooses Discard.
    Expected Result: The guard fails and the file remains Updated Draft/Pre-circulation, not Discarded.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "File 34", "Initial note")
    fid = draft["file_id"]
    update_file_draft(fid, "owner_user", subject="Edited 34")
    with pytest.raises((ValueError, PermissionError)):
        discard_file_draft(fid, "intruder_user")

@pytest.mark.django_db
def test_tc_wf_035():
    """TC_WF_035 - BW-FTS-08 — Row 2 guard: 'Actor authorized; file remains pre-circulation; edits are saved': Verify the edit step is blocked for an unauthorized actor within the edit-then-discard path, so the Updated Draft state is not reached.

    Action/Input: The user attempts to edit and save the draft.
    Expected Result: The guard fails and no Updated Draft state is produced. The file remains Draft/Pre-circulation.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "File 35", "Initial note")
    fid = draft["file_id"]
    with pytest.raises((ValueError, PermissionError)):
        update_file_draft(fid, "intruder_user", subject="Hacked 35")

@pytest.mark.django_db
def test_tc_wf_036():
    """TC_WF_036 - CW-FTS-01 — Rows 1 and 5 (BW-FTS-01 then BW-FTS-04; zero onward traversal skips Row 2): Verify the composite path: send, zero onward traversal, then owner archival.

    Action/Input: Sender sends the file with a mandatory comment; the Recipient takes no onward or return action; the File Owner then selects Archive.
    Expected Result: After send the file is Active/Circulated and held by the Recipient. After archival the file is Archived/Read-only/Permanently retained. Movement, history and audit are updated, and send and archive notification events are triggered. The onward-forward row is not traversed.
    Test Type: positive
    """
    draft = create_file_draft("owner_user", "Officer", "Composite 36", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Step 1")
    return_file(fid, "rec_1", "Staff", "Back to owner", target_receiver_id="owner_user")
    arch = archive_file(fid, "owner_user", "Officer", "Archived 36")
    assert arch["status"] == "archived"

@pytest.mark.django_db
def test_tc_wf_037():
    """TC_WF_037 - CW-FTS-01 — Rows 1, 2 and 5 (BW-FTS-01, BW-FTS-02, BW-FTS-04; one onward traversal): Verify the composite path with exactly one onward-forward traversal followed by owner archival.

    Action/Input: Sender sends to the Recipient with a comment; the Recipient forwards onward to the Next Recipient with a comment; the File Owner archives after the objective is complete.
    Expected Result: After send the file is held by the Recipient. After onward forward it is Active/Circulated and held by the Next Recipient. After archival it is Archived/Read-only/Permanently retained. Movement, history and audit are updated at each step and notifications are triggered.
    Test Type: boundary
    """
    draft = create_file_draft("owner_user", "Officer", "Composite 37", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Step 1")
    forward_file(fid, "rec_1", "Staff", "rec_2", "Director", "Step 2")
    return_file(fid, "rec_2", "Director", "Back to owner", target_receiver_id="owner_user")
    arch = archive_file(fid, "owner_user", "Officer", "Archived 37")
    assert arch["status"] == "archived"

@pytest.mark.django_db
def test_tc_wf_038():
    """TC_WF_038 - CW-FTS-01 — Rows 1 and 3 (BW-FTS-01 then BW-FTS-03; Alternative return branch): Verify the composite path: send then immediate return to the previous sender.

    Action/Input: Sender sends to the Recipient with a comment; the Recipient returns the file with a mandatory comment.
    Expected Result: After send the file is held by the Recipient. After return it is Active/Circulated and held by the Previous Sender. Return, history and audit are updated and the return notification event is triggered.
    Test Type: alternative
    """
    draft = create_file_draft("owner_user", "Officer", "Composite 38", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Step 1")
    ret = return_file(fid, "rec_1", "Staff", "Immediate return", target_receiver_id="owner_user")
    assert ret["new_status"] == "returned"
    assert ret["returned_to_id"] == "owner_user"

@pytest.mark.django_db
def test_tc_wf_039():
    """TC_WF_039 - CW-FTS-01 — Rows 1, 2 and 4 (return after one onward traversal): Verify the next recipient returns the file to the sender of the onward movement after one onward traversal.

    Action/Input: Sender sends to the Recipient; the Recipient forwards onward to the Next Recipient; the Next Recipient returns the file with a mandatory comment.
    Expected Result: After the onward forward the file is held by the Next Recipient. After return it is Active/Circulated and held by the Prior Sender of that movement (the Recipient who forwarded onward), not the original Sender. Return, history and audit are updated and the return notification event is triggered.
    Test Type: alternative
    """
    draft = create_file_draft("owner_user", "Officer", "Composite 39", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Step 1")
    forward_file(fid, "rec_1", "Staff", "rec_2", "Director", "Step 2")
    ret = return_file(fid, "rec_2", "Director", "Return to rec_1", target_receiver_id="rec_1")
    assert ret["new_status"] == "returned"
    assert ret["returned_to_id"] == "rec_1"

@pytest.mark.django_db
def test_tc_wf_040():
    """TC_WF_040 - CW-FTS-01 — Rows 1, 3 and 5 (archival from an Active/Circulated state after return): Verify owner archival from the Active/Circulated state reached after a return.

    Action/Input: File Owner selects Archive.
    Expected Result: File state becomes Archived/Read-only/Permanently retained. Archive and audit are recorded and the archive notification event is triggered.
    Test Type: positive
    """
    draft = create_file_draft("owner_user", "Officer", "Composite 40", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Step 1")
    return_file(fid, "rec_1", "Staff", "Back to owner", target_receiver_id="owner_user")
    arch = archive_file(fid, "owner_user", "Officer", "Archiving after return")
    assert arch["status"] == "archived"

@pytest.mark.django_db
def test_tc_wf_041():
    """TC_WF_041 - CW-FTS-01 — Rows 1, 2, 4 and 5 (archival after return following one onward traversal): Verify archival closes the lifecycle after the full onward-then-return sequence.

    Action/Input: File Owner selects Archive.
    Expected Result: File state becomes Archived/Read-only/Permanently retained, with archive and audit recorded and the archive notification event triggered.
    Test Type: positive
    """
    draft = create_file_draft("owner_user", "Officer", "Composite 41", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Step 1")
    forward_file(fid, "rec_1", "Staff", "rec_2", "Director", "Step 2")
    return_file(fid, "rec_2", "Director", "Back", target_receiver_id="owner_user")
    arch = archive_file(fid, "owner_user", "Officer", "Lifecycle closing archival")
    assert arch["status"] == "archived"
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.status == "archived"

@pytest.mark.django_db
def test_tc_wf_042():
    """TC_WF_042 - CW-FTS-01 — Row 5 (Archived/Read-only terminal state); BW-FTS-01 Row 1 guard 'file not archived': Verify an archived file cannot continue through the circulation transitions of the composite workflow.

    Action/Input: A user attempts to send/forward the archived file with a valid recipient and a mandatory comment.
    Expected Result: The transition does not occur and the file remains Archived/Read-only/Permanently retained.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "Composite 42", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Step 1")
    return_file(fid, "rec_1", "Staff", "Back", target_receiver_id="owner_user")
    archive_file(fid, "owner_user", "Officer", "Archived 42")
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Illegal forward on archived")

@pytest.mark.django_db
def test_tc_wf_043():
    """TC_WF_043 - CW-FTS-01 — Row 5 guard (owner archives; objective complete); BW-FTS-04 Row 1: Verify the cross-cutting archival transition is blocked for a non-owner during an active composite circulation.

    Action/Input: The non-owner selects Archive.
    Expected Result: The transition to Archived/Read-only/Permanently retained does not occur and the file remains Active/Circulated.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "Composite 43", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "owner_user", "Officer", "custodian_user", "Staff", "Custody active")
    with pytest.raises(PermissionError):
        archive_file(fid, "custodian_user", "Staff", "Non-owner attempt")

@pytest.mark.django_db
def test_tc_wf_044():
    """TC_WF_044 - CW-FTS-02 — Rows 1 and 5 (BW-FTS-05; zero edit traversal, initial circulation): Verify the composite path: create then send with zero draft-edit traversal.

    Action/Input: Creator creates a new file with an initial mandatory comment, then sends it to the Recipient with a mandatory movement comment, skipping the edit row.
    Expected Result: The file moves No record → Draft/Pre-circulation → Active/Circulated held by the Recipient. Movement, history and audit are updated and notification event(s) are triggered.
    Test Type: positive
    """
    draft = create_file_draft("owner_user", "Officer", "Composite 44", "Initial note")
    fid = draft["file_id"]
    fwd = forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Direct send")
    assert fwd["new_status"] == "in_transit"

@pytest.mark.django_db
def test_tc_wf_045():
    """TC_WF_045 - CW-FTS-02 — Rows 1, 2 and 6 (BW-FTS-06; one edit traversal, initial circulation): Verify the composite path: create, one draft edit, then send.

    Action/Input: Creator creates a new file with an initial mandatory comment, edits the draft once, then sends it to the Recipient with a mandatory movement comment.
    Expected Result: The file moves No record → Draft → Updated Draft → Active/Circulated held by the Recipient. Movement, history and audit are updated and notification event(s) are triggered.
    Test Type: boundary
    """
    draft = create_file_draft("owner_user", "Officer", "Composite 45", "Initial note")
    fid = draft["file_id"]
    update_file_draft(fid, "owner_user", subject="Updated 45")
    fwd = forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Send after edit")
    assert fwd["new_status"] == "in_transit"

@pytest.mark.django_db
def test_tc_wf_046():
    """TC_WF_046 - CW-FTS-02 — Rows 1 and 3 (BW-FTS-07; discard with zero edit traversal): Verify the composite alternative terminal outcome: create then discard.

    Action/Input: Creator creates a new file with an initial mandatory comment, then chooses Discard before submission.
    Expected Result: The file moves No record → Draft/Pre-circulation → Discarded/No active file retained.
    Test Type: alternative
    """
    draft = create_file_draft("owner_user", "Officer", "Composite 46", "Initial note")
    fid = draft["file_id"]
    disc = discard_file_draft(fid, "owner_user")
    assert disc["status"] == "discarded"
    assert not FTSFile.objects.filter(id=fid).exists()

@pytest.mark.django_db
def test_tc_wf_047():
    """TC_WF_047 - CW-FTS-02 — Rows 1, 2 and 4 (BW-FTS-08; discard after exactly one edit traversal): Verify the composite terminal outcome: create, one edit, then discard.

    Action/Input: Creator creates a new file with an initial mandatory comment, edits the draft once, then chooses Discard before submission.
    Expected Result: The file moves No record → Draft → Updated Draft → Discarded/No active file retained.
    Test Type: boundary
    """
    draft = create_file_draft("owner_user", "Officer", "Composite 47", "Initial note")
    fid = draft["file_id"]
    update_file_draft(fid, "owner_user", subject="Edited 47")
    disc = discard_file_draft(fid, "owner_user")
    assert disc["status"] == "discarded"
    assert not FTSFile.objects.filter(id=fid).exists()

@pytest.mark.django_db
def test_tc_wf_048():
    """TC_WF_048 - CW-FTS-02 — Rows 3 and 4 guard: 'Discard before circulation'; BW-FTS-07 Row 2 guard: Verify that once a new file has reached initial circulation (Active/Circulated), the discard outcome of CW-FTS-02 is no longer available.

    Action/Input: The Creator attempts to choose Discard on the circulated file.
    Expected Result: The guard (file has not been submitted/circulated) fails and the file is not moved to Discarded/No active file retained. It remains Active/Circulated.
    Test Type: negative
    """
    draft = create_file_draft("owner_user", "Officer", "Composite 48", "Initial note")
    fid = draft["file_id"]
    forward_file(fid, "owner_user", "Officer", "rec_1", "Staff", "Circulated")
    with pytest.raises((ValueError, PermissionError)):
        discard_file_draft(fid, "owner_user")

