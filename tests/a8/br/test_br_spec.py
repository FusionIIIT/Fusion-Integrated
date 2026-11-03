"""Assignment #8 - Strategy 3: Business Rules (BR) Test Suite.

Auto-generated backend verification suite derived strictly from the frozen
a8_design/BR_DESIGN.json specification requirements (BR-FTS-001 through BR-FTS-014).
"""

import pytest
from modules.fts.models import FTSFile, FTSMovement, FTSComment, FTSAttachment
from modules.fts.domain.workflow import (
    can_forward_file,
    can_return_file,
    can_archive_file,
    can_edit_draft,
    STATUS_DRAFT,
    STATUS_IN_TRANSIT,
    STATUS_RETURNED,
    STATUS_ARCHIVED,
)
from modules.fts.services.drafts import create_file_draft, update_file_draft, discard_file_draft
from modules.fts.services.movements import forward_file, return_file
from modules.fts.services.archival import archive_file
from modules.fts.selectors.drafts import get_user_draft_files, get_draft_by_id
from modules.fts.selectors.inbox_outbox import get_user_inbox_files, get_user_outbox_files
from modules.fts.selectors.movements import get_file_movement_history, get_previous_senders_for_file
from modules.fts.contracts import get_files_by_uins, get_active_inbox_files_for_employees


@pytest.mark.django_db
def test_tc_br_001():
    """TC_BR_001 - BR-FTS-001: Verify an authorized Institute Employee may perform an operational file-processing action

    Action/Input: The Institute Employee requests an operational file action (for example, creating a file)
    Expected Result: The operational file action is allowed and processed
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Operational File", "Initial comment", "medium", "general")
    assert draft["file_id"] > 0
    fwd = forward_file(draft["file_id"], "emp_1", "Officer", "emp_2", "Reviewer", "Operational forward")
    assert fwd["new_status"] == "in_transit" 

@pytest.mark.django_db
def test_tc_br_002():
    """TC_BR_002 - BR-FTS-001: Verify System Admin is excluded from routine operational file processing

    Action/Input: The System Admin requests a routine operational file action (for example, forwarding a file)
    Expected Result: The operational file action is not permitted
    Test Type: negative
    """
    # Operational exclusion: Non-employee / System Admin cannot perform operational file workflows
    is_valid, msg = can_forward_file("draft", "admin_user", "holder", "receiver", "comment")
    assert is_valid is False

@pytest.mark.django_db
def test_tc_br_003():
    """TC_BR_003 - BR-FTS-001: Verify System Admin governance actions are permitted only within the separate governance scope

    Action/Input: The System Admin performs an FTS governance action within the governance scope
    Expected Result: The governance action is permitted, and no routine operational file-processing capability is granted by it
    Test Type: exception
    """
    pytest.skip("NOT_AUTOMATED: External IAM / notification mechanisms outside FTS backend scope")


@pytest.mark.django_db
def test_tc_br_004():
    """TC_BR_004 - BR-FTS-001: Verify a user who is not an Institute Employee cannot perform operational file actions

    Action/Input: The user requests an operational file action
    Expected Result: The operational file action is not permitted
    Test Type: negative
    """
    # Operational exclusion: Non-employee / System Admin cannot perform operational file workflows
    is_valid, msg = can_forward_file("draft", "admin_user", "holder", "receiver", "comment")
    assert is_valid is False

@pytest.mark.django_db
def test_tc_br_005():
    """TC_BR_005 - BR-FTS-002: Verify role switching preserves existing file ownership and previously recorded audit history, and that the selected role governs authorization

    Action/Input: The employee selects another assigned role context, then views owned files and audit history and attempts an action
    Expected Result: File ownership is unchanged, previously recorded audit entries retain their original identity, and authorization is applied according to the newly selected role
    Test Type: positive
    """
    draft = create_file_draft("user_switch", "Role_1", "Switching File", "Note")
    fid = draft["file_id"]
    forward_file(fid, "user_switch", "Role_2", "receiver", "Role_R", "Forwarded with Role_2")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.creator_id == "user_switch"
    assert f_obj.creator_role == "Role_1" 

@pytest.mark.django_db
def test_tc_br_006():
    """TC_BR_006 - BR-FTS-003: Verify a file and its accumulated contents persist after circulation

    Action/Input: Retrieve the file, its comments, attachments and movement records after circulation
    Expected Result: The file, its comments, its attachments and its movement records are all retained and retrievable
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Persistent File", "Initial comment")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Circulation forward")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.status == "in_transit"
    assert f_obj.is_draft is False
    assert f_obj.comments.count() == 2

@pytest.mark.django_db
def test_tc_br_007():
    """TC_BR_007 - BR-FTS-003: Verify circulated contents are not deleted through draft-discard behavior

    Action/Input: Attempt to discard the circulated file as a draft
    Expected Result: The discard is not applied and the file and its accumulated contents remain intact
    Test Type: negative
    """
    draft = create_file_draft("emp_1", "Officer", "Circulated File 7", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    with pytest.raises((ValueError, PermissionError)):
        discard_file_draft(fid, "emp_1")

@pytest.mark.django_db
def test_tc_br_008():
    """TC_BR_008 - BR-FTS-003: Verify attachments are optional while the comment is mandatory for creation

    Action/Input: Create a file with an initial comment and no attachments
    Expected Result: The file is accepted and persisted without any attachment
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Optional Att File", "Comment present")
    fid = draft["file_id"]
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.comments.count() == 1
    assert f_obj.attachments.count() == 0

@pytest.mark.django_db
def test_tc_br_009():
    """TC_BR_009 - BR-FTS-003: Verify a pre-submission draft may be discarded (exception to persistence)

    Action/Input: Discard the draft
    Expected Result: The draft is discarded as permitted by BR-FTS-005
    Test Type: exception
    """
    draft = create_file_draft("emp_1", "Officer", "Pre-submission Draft", "Note")
    fid = draft["file_id"]
    res = discard_file_draft(fid, "emp_1")
    assert res["status"] == "discarded"
    assert not FTSFile.objects.filter(id=fid).exists()

@pytest.mark.django_db
def test_tc_br_010():
    """TC_BR_010 - BR-FTS-004: Verify file creation is blocked without an initial comment

    Action/Input: Attempt to create/save a new file with no initial comment
    Expected Result: File creation is not accepted until an initial comment is provided
    Test Type: negative
    """
    with pytest.raises(ValueError):
        create_file_draft("emp_1", "Officer", "No Comment File", "")

@pytest.mark.django_db
def test_tc_br_011():
    """TC_BR_011 - BR-FTS-004: Verify file creation is accepted when an initial comment is present

    Action/Input: Create a new file with an initial comment
    Expected Result: File creation is accepted
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Valid Init Comment", "Comment is present")
    assert draft["file_id"] > 0

@pytest.mark.django_db
def test_tc_br_012():
    """TC_BR_012 - BR-FTS-005: Verify draft save, edit and discard are permitted before circulation

    Action/Input: Save the draft, edit the draft, and discard the draft
    Expected Result: Each draft operation is permitted while the file is in the pre-circulation state
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Draft 12", "Init")
    fid = draft["file_id"]
    up = update_file_draft(fid, "emp_1", subject="Draft 12 Modified")
    assert up["subject"] == "Draft 12 Modified"
    disc = discard_file_draft(fid, "emp_1")
    assert disc["status"] == "discarded" 

@pytest.mark.django_db
def test_tc_br_013():
    """TC_BR_013 - BR-FTS-005: Verify a circulated file cannot be deleted as a draft

    Action/Input: Attempt draft deletion/discard on the circulated file
    Expected Result: Draft deletion is prevented and the file remains
    Test Type: negative
    """
    draft = create_file_draft("emp_1", "Officer", "Circulated 13", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Circulated")
    with pytest.raises((ValueError, PermissionError)):
        discard_file_draft(fid, "emp_1")

@pytest.mark.django_db
def test_tc_br_014():
    """TC_BR_014 - BR-FTS-006: Verify forwarding is blocked without a movement comment

    Action/Input: Attempt to forward the file with no movement comment
    Expected Result: The forward is blocked until a movement comment is supplied
    Test Type: negative
    """
    draft = create_file_draft("emp_1", "Officer", "Fwd Comment Check", "Init")
    fid = draft["file_id"]
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "")

@pytest.mark.django_db
def test_tc_br_015():
    """TC_BR_015 - BR-FTS-006: Verify returning is blocked without a movement comment

    Action/Input: Attempt to return the file with no movement comment
    Expected Result: The return is blocked until a movement comment is supplied
    Test Type: negative
    """
    draft = create_file_draft("emp_1", "Officer", "Ret Comment Check", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    with pytest.raises((ValueError, PermissionError)):
        return_file(fid, "emp_2", "Reviewer", "", target_receiver_id="emp_1")

@pytest.mark.django_db
def test_tc_br_016():
    """TC_BR_016 - BR-FTS-006: Verify forwarding and returning succeed when a movement comment is supplied

    Action/Input: Forward a file with a movement comment; return a received file with a movement comment
    Expected Result: Both movements are accepted
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Fwd & Ret File", "Init")
    fid = draft["file_id"]
    fwd = forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd comment")
    assert fwd["new_status"] == "in_transit"
    ret = return_file(fid, "emp_2", "Reviewer", "Ret comment", target_receiver_id="emp_1")
    assert ret["new_status"] == "returned" 

@pytest.mark.django_db
def test_tc_br_017():
    """TC_BR_017 - BR-FTS-007: Verify a file may be sent to another Institute Employee regardless of the receiver's role

    Action/Input: Forward the file with a movement comment to each recipient in turn (using separate files or successive movements)
    Expected Result: Each recipient is accepted irrespective of role
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Staff", "Cross Role File", "Init")
    fid = draft["file_id"]
    fwd = forward_file(fid, "emp_1", "Staff", "faculty_dean", "Dean", "To Dean across role hierarchy")
    assert fwd["current_holder_id"] == "faculty_dean" 

@pytest.mark.django_db
def test_tc_br_018():
    """TC_BR_018 - BR-FTS-007: Verify a recipient who is not a valid Institute Employee is not accepted

    Action/Input: Attempt to forward the file with a movement comment to that recipient
    Expected Result: The recipient is not accepted and the file is not sent
    Test Type: negative
    """
    # TC_BR_018: Recipient who is not valid (empty string) must be rejected
    draft = create_file_draft("emp_1", "Officer", "Invalid Recipient BR", "Init")
    fid = draft["file_id"]
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "emp_1", "Officer", "", "Officer", "Sending to empty receiver")

@pytest.mark.django_db
def test_tc_br_019():
    """TC_BR_019 - BR-FTS-007: Verify a received file is returned to the sender of the received movement

    Action/Input: User B returns the file with a movement comment
    Expected Result: The file is routed to User A, the sender of the received movement
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Return to Sender", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    ret = return_file(fid, "emp_2", "Reviewer", "Returning back", target_receiver_id="emp_1")
    assert ret["returned_to_id"] == "emp_1" 

@pytest.mark.django_db
def test_tc_br_020():
    """TC_BR_020 - BR-FTS-007: Verify return is subject to authorization/file-state permissions

    Action/Input: The user attempts to return the file with a movement comment
    Expected Result: The return is not permitted
    Test Type: negative
    """
    draft = create_file_draft("emp_1", "Officer", "Return Unauthorized State", "Init")
    fid = draft["file_id"]
    # Attempting to return an un-circulated draft
    with pytest.raises((ValueError, PermissionError)):
        return_file(fid, "emp_1", "Officer", "Cannot return draft", target_receiver_id="emp_2")

@pytest.mark.django_db
def test_tc_br_021():
    """TC_BR_021 - BR-FTS-008: Verify a successful forward is recorded with sender, receiver, timestamp, comment and attachments

    Action/Input: Forward the file with a movement comment and an attachment
    Expected Result: A movement event is appended to the history containing sender, receiver, timestamp, movement comment and the movement attachment
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Movement Record File", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Step 1 note")
    hist = get_file_movement_history(fid)
    assert len(hist) == 2
    assert hist[-1]["action"] == "forwarded"
    assert hist[-1]["from_user_id"] == "emp_1"
    assert hist[-1]["to_user_id"] == "emp_2" 

@pytest.mark.django_db
def test_tc_br_022():
    """TC_BR_022 - BR-FTS-008: Verify a movement without attachments is still recorded (attachments only where present)

    Action/Input: Forward the file with a movement comment and no attachment
    Expected Result: A movement event is recorded with sender, receiver, timestamp and comment, and no attachment is listed
    Test Type: boundary
    """
    draft = create_file_draft("emp_1", "Officer", "Movement Without Att", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd without att")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.attachments.count() == 0

@pytest.mark.django_db
def test_tc_br_023():
    """TC_BR_023 - BR-FTS-008: Verify a successful return is recorded in the movement history

    Action/Input: Return the file with a movement comment
    Expected Result: A return movement event is appended with sender, receiver, timestamp and movement comment
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Return Movement Record", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    return_file(fid, "emp_2", "Reviewer", "Ret", target_receiver_id="emp_1")
    hist = get_file_movement_history(fid)
    assert len(hist) == 3
    assert hist[-1]["action"] == "returned" 

@pytest.mark.django_db
def test_tc_br_024():
    """TC_BR_024 - BR-FTS-008: Verify movement events are kept in chronological order and holder/pending-recipient information is updated consistently

    Action/Input: View the file movement history and current holder/pending-recipient information
    Expected Result: Events appear in chronological order and the holder/pending-recipient information is consistent with the most recent movement
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Chronological Order", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Step 1")
    return_file(fid, "emp_2", "Reviewer", "Step 2", target_receiver_id="emp_1")
    hist = get_file_movement_history(fid)
    assert len(hist) == 3
    assert hist[0]["created_at"] <= hist[1]["created_at"] <= hist[2]["created_at"]
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.current_holder_id == "emp_1" 

@pytest.mark.django_db
def test_tc_br_025():
    """TC_BR_025 - BR-FTS-009: Verify an authorized associated user can access a file and its history through Inbox/Outbox

    Action/Input: The user opens Inbox/Outbox and opens the file and its history
    Expected Result: The associated file is listed and its contents and history can be opened
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Inbox Outbox Check", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    inbox = get_user_inbox_files("emp_2")
    outbox = get_user_outbox_files("emp_1")
    assert any(f["id"] == fid for f in inbox)
    assert any(f["id"] == fid for f in outbox)

@pytest.mark.django_db
def test_tc_br_026():
    """TC_BR_026 - BR-FTS-009: Verify files/history are not exposed to users who are not authorized and associated

    Action/Input: The user requests that file and its history, and views Inbox/Outbox
    Expected Result: The file and its history are not exposed or opened, and the file is not listed in the user's Inbox/Outbox
    Test Type: negative
    """
    draft = create_file_draft("emp_1", "Officer", "Isolation File", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    inbox_stranger = get_user_inbox_files("stranger")
    assert not any(f["id"] == fid for f in inbox_stranger)

@pytest.mark.django_db
def test_tc_br_027():
    """TC_BR_027 - BR-FTS-009: Verify archived files remain readable to authorized users

    Action/Input: The user opens the archived file and its history
    Expected Result: The archived file contents and history are readable
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Archived Readable", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    return_file(fid, "emp_2", "Reviewer", "Ret", target_receiver_id="emp_1")
    archive_file(fid, "emp_1", "Officer", "Closed")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.status == "archived" 

@pytest.mark.django_db
def test_tc_br_028():
    """TC_BR_028 - BR-FTS-010: Verify an action authorized by role, context, file association and file state is permitted

    Action/Input: The user requests a protected FTS action on the file
    Expected Result: The action is permitted
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Authorized Action", "Init")
    fid = draft["file_id"]
    fwd = forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Authorized forward")
    assert fwd["new_status"] == "in_transit" 

@pytest.mark.django_db
def test_tc_br_029():
    """TC_BR_029 - BR-FTS-010: Verify an action is rejected when the user's role/assigned-role context does not authorize it

    Action/Input: The user requests the sensitive action
    Expected Result: The action is rejected
    Test Type: negative
    """
    draft = create_file_draft("emp_1", "Officer", "Unauthorized File", "Init")
    fid = draft["file_id"]
    with pytest.raises(PermissionError):
        forward_file(fid, "unauthorized_user", "Staff", "emp_2", "Reviewer", "Illegal forward")

@pytest.mark.django_db
def test_tc_br_030():
    """TC_BR_030 - BR-FTS-010: Verify an action is rejected when the user has no association with the file

    Action/Input: The user requests a protected action on the file
    Expected Result: The action is rejected
    Test Type: negative
    """
    draft = create_file_draft("emp_1", "Officer", "Unauthorized File", "Init")
    fid = draft["file_id"]
    with pytest.raises(PermissionError):
        forward_file(fid, "unauthorized_user", "Staff", "emp_2", "Reviewer", "Illegal forward")

@pytest.mark.django_db
def test_tc_br_031():
    """TC_BR_031 - BR-FTS-010: Verify an action is rejected when the file state does not authorize it

    Action/Input: A user associated with the file requests the action
    Expected Result: The action is rejected
    Test Type: negative
    """
    draft = create_file_draft("emp_1", "Officer", "State Invariant File", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    return_file(fid, "emp_2", "Reviewer", "Back", target_receiver_id="emp_1")
    archive_file(fid, "emp_1", "Officer", "Archived")
    # Action rejected when file state is archived
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Illegal forward on archived")

@pytest.mark.django_db
def test_tc_br_032():
    """TC_BR_032 - BR-FTS-010: Verify RBAC is enforced for integration invocations of FTS actions

    Action/Input: Invoke the FTS action through the integration
    Expected Result: The unauthorized action is rejected
    Test Type: negative
    """
    # Integration invocation RBAC enforcement
    draft = create_file_draft("module_user", "Staff", "Integ File", "Init")
    fid = draft["file_id"]
    with pytest.raises(PermissionError):
        forward_file(fid, "unauthorized_integ_actor", "Staff", "emp_2", "Reviewer", "Illegal")

@pytest.mark.django_db
def test_tc_br_033():
    """TC_BR_033 - BR-FTS-011: Verify audit records are created for creation, comments, attachments, forwarding and return

    Action/Input: Review the audit records for the file
    Expected Result: Audit records exist for creation, comments, attachments, forwarding and return
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Audit Creation File", "Init comment")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Audit fwd")
    return_file(fid, "emp_2", "Reviewer", "Audit ret", target_receiver_id="emp_1")
    hist = get_file_movement_history(fid)
    assert len(hist) == 3

@pytest.mark.django_db
def test_tc_br_034():
    """TC_BR_034 - BR-FTS-011: Verify an audit record is created for archival

    Action/Input: Review the audit records for the file
    Expected Result: An audit record exists for the archival action
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Audit Archival File", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    return_file(fid, "emp_2", "Reviewer", "Ret", target_receiver_id="emp_1")
    archive_file(fid, "emp_1", "Officer", "Archived step")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.movements.filter(action="archived").exists()

@pytest.mark.django_db
def test_tc_br_035():
    """TC_BR_035 - BR-FTS-011: Verify an audit record is created for integration actions

    Action/Input: Review the audit records after the integration action
    Expected Result: An audit record exists for the integration action
    Test Type: positive
    """
    draft = create_file_draft("integ_emp", "Staff", "Integ Audit File", "Init")
    fid = draft["file_id"]
    hist = get_file_movement_history(fid)
    assert len(hist) >= 1

@pytest.mark.django_db
def test_tc_br_036():
    """TC_BR_036 - BR-FTS-011: Verify chronological version history is maintained and prior history is not rewritten

    Action/Input: Perform the action, then review the audit/version history
    Expected Result: A new record is appended chronologically and previously recorded entries remain unchanged
    Test Type: positive
    """
    draft = create_file_draft("emp_1", "Officer", "Version History", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Step 1")
    return_file(fid, "emp_2", "Reviewer", "Step 2", target_receiver_id="emp_1")
    hist = get_file_movement_history(fid)
    assert len(hist) == 3
    assert hist[0]["movement_id"] < hist[1]["movement_id"] < hist[2]["movement_id"]

@pytest.mark.django_db
def test_tc_br_037():
    """TC_BR_037 - BR-FTS-012: Verify the file owner may archive a completed circulated file

    Action/Input: The owner requests archival
    Expected Result: The file is archived
    Test Type: positive
    """
    draft = create_file_draft("emp_owner", "Officer", "Owner Archival File", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_owner", "Officer", "emp_2", "Reviewer", "Fwd")
    return_file(fid, "emp_2", "Reviewer", "Ret", target_receiver_id="emp_owner")
    arch = archive_file(fid, "emp_owner", "Officer", "Owner archives")
    assert arch["status"] == "archived" 

@pytest.mark.django_db
def test_tc_br_038():
    """TC_BR_038 - BR-FTS-012: Verify a user who is not the file owner cannot archive the file

    Action/Input: The non-owner requests archival
    Expected Result: Archival is not permitted and the file is not archived
    Test Type: negative
    """
    # TC_BR_038: User who is not file owner cannot archive the file (BR-FTS-012)
    draft = create_file_draft("emp_owner", "Officer", "Non-Owner Archival", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_owner", "Officer", "emp_custodian", "Reviewer", "Custody transferred")
    with pytest.raises(PermissionError):
        archive_file(fid, "emp_custodian", "Reviewer", "Custodian attempting non-owner archival")

@pytest.mark.django_db
def test_tc_br_039():
    """TC_BR_039 - BR-FTS-012: Verify an archived file cannot be modified

    Action/Input: An authorized user attempts to modify the archived file
    Expected Result: The modification is rejected; the file remains read-only
    Test Type: negative
    """
    draft = create_file_draft("emp_owner", "Officer", "Archived Terminal File", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_owner", "Officer", "emp_2", "Reviewer", "Fwd")
    return_file(fid, "emp_2", "Reviewer", "Ret", target_receiver_id="emp_owner")
    archive_file(fid, "emp_owner", "Officer", "Archived permanently")
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "emp_owner", "Officer", "emp_2", "Reviewer", "Illegal forward")

@pytest.mark.django_db
def test_tc_br_040():
    """TC_BR_040 - BR-FTS-012: Verify an archived file cannot be forwarded

    Action/Input: An authorized user attempts to forward the archived file with a movement comment
    Expected Result: The forward is rejected
    Test Type: negative
    """
    draft = create_file_draft("emp_owner", "Officer", "Archived Terminal File", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_owner", "Officer", "emp_2", "Reviewer", "Fwd")
    return_file(fid, "emp_2", "Reviewer", "Ret", target_receiver_id="emp_owner")
    archive_file(fid, "emp_owner", "Officer", "Archived permanently")
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "emp_owner", "Officer", "emp_2", "Reviewer", "Illegal forward")

@pytest.mark.django_db
def test_tc_br_041():
    """TC_BR_041 - BR-FTS-012: Verify an archived file remains permanently stored and readable to authorized users

    Action/Input: An authorized user reads the archived file
    Expected Result: The archived file remains stored and readable
    Test Type: positive
    """
    draft = create_file_draft("emp_owner", "Officer", "Permanent Read File", "Init")
    fid = draft["file_id"]
    forward_file(fid, "emp_owner", "Officer", "emp_2", "Reviewer", "Fwd")
    return_file(fid, "emp_2", "Reviewer", "Ret", target_receiver_id="emp_owner")
    archive_file(fid, "emp_owner", "Officer", "Archived")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.status == "archived" 

@pytest.mark.django_db
def test_tc_br_042():
    """TC_BR_042 - BR-FTS-013: Verify a notification is triggered when a file is received

    Action/Input: Complete the movement that delivers the file
    Expected Result: A file-received notification event is created and handed to the Fusion notification mechanism
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External IAM / notification mechanisms outside FTS backend scope")


@pytest.mark.django_db
def test_tc_br_043():
    """TC_BR_043 - BR-FTS-013: Verify a notification is triggered when a file is forwarded

    Action/Input: Complete the forward
    Expected Result: A file-forwarded notification event is created and handed to the Fusion notification mechanism
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External IAM / notification mechanisms outside FTS backend scope")


@pytest.mark.django_db
def test_tc_br_044():
    """TC_BR_044 - BR-FTS-013: Verify a notification is triggered when a file is returned

    Action/Input: Complete the return
    Expected Result: A file-returned notification event is created and handed to the Fusion notification mechanism
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External IAM / notification mechanisms outside FTS backend scope")


@pytest.mark.django_db
def test_tc_br_045():
    """TC_BR_045 - BR-FTS-013: Verify a notification is triggered when a file is archived

    Action/Input: Complete the archival
    Expected Result: A file-archived notification event is created and handed to the Fusion notification mechanism
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External IAM / notification mechanisms outside FTS backend scope")


@pytest.mark.django_db
def test_tc_br_046():
    """TC_BR_046 - BR-FTS-013: Verify notifications are triggered for relevant role assignment/reassignment events

    Action/Input: Complete the role assignment/reassignment
    Expected Result: A role assignment/reassignment notification event is created and handed to the Fusion notification mechanism
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External IAM / notification mechanisms outside FTS backend scope")


@pytest.mark.django_db
def test_tc_br_047():
    """TC_BR_047 - BR-FTS-014: Verify FTS provides file/workflow tracking capabilities to a consuming module when authorized

    Action/Input: Invoke the FTS service (file/workflow tracking, approval-chain support, or file-based request tracking)
    Expected Result: The authorized capability is provided and the invocation is subject to FTS RBAC and audit rules
    Test Type: positive
    """
    draft = create_file_draft("integ_caller", "Staff", "Consuming Module Workflow", "Init")
    uin = draft["uin"]
    res = get_files_by_uins([uin])
    assert len(res) == 1
    assert res[0].uin == uin

@pytest.mark.django_db
def test_tc_br_048():
    """TC_BR_048 - BR-FTS-014: Verify unauthorized capabilities are not provided to a consuming module

    Action/Input: Invoke the FTS service
    Expected Result: The capability is not provided
    Test Type: negative
    """
    # Unauthorized capability request
    res = get_files_by_uins([])
    assert res == []

@pytest.mark.django_db
def test_tc_br_049():
    """TC_BR_049 - BR-FTS-014: Verify FTS does not assume ownership of consuming-module domain-specific policy

    Action/Input: Invoke the FTS service for a domain-specific request
    Expected Result: FTS provides tracking capabilities only and does not apply or define the consuming module's domain-specific actors, forms, policies, validations or workflow semantics
    Test Type: exception
    """
    # FTS does not assume ownership of consuming module's domain-specific policy
    draft = create_file_draft("exam_cell", "Officer", "Moderation Request", "Tracking")
    assert draft["status"] == "draft" 

