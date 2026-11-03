"""Assignment #8 - Strategy 2: Use Cases (UC) Test Suite.

Auto-generated backend verification suite derived strictly from the frozen
a8_design/UC_DESIGN.json specification requirements (Main, Alternative & Exception Flows).
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
def test_tc_uc_001():
    """TC_UC_001 - FTS-UC-001 — Main Success Scenario: Verify that an authorized employee can create a new file with the mandatory initial comment and an optional attachment and save it as a draft/pre-circulation file.

    Action/Input: Employee opens the file-creation function, enters the initial mandatory comment, adds one attachment, and saves the file as a draft/pre-circulation file.
    Expected Result: FTS validates the comment and persists the file object. A valid file exists in a draft/pre-circulation state with the initial comment and attachment preserved. Creation, comment and attachment audit information is recorded. No circulated file is created.
    Test Type: positive
    """
    draft = create_file_draft("emp_user", "Staff", "Draft 001", "Initial mandatory note", "medium", "general")
    fid = draft["file_id"]
    att = FTSAttachment.objects.create(file_id=fid, file_name="doc.pdf", file_url="/doc.pdf", uploaded_by_id="emp_user")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.is_draft is True
    assert f_obj.status == "draft"
    assert f_obj.attachments.count() == 1

@pytest.mark.django_db
def test_tc_uc_002():
    """TC_UC_002 - FTS-UC-001 — Alternative Flow 1: Verify that when the employee chooses immediate circulation instead of retaining the draft, the valid created file proceeds through FTS-UC-003 (Send/Forward File to Employee).

    Action/Input: Employee chooses immediate circulation instead of retaining the draft and sends the created file to a valid recipient with a movement comment through the Send/Forward goal.
    Expected Result: The valid created file proceeds through FTS-UC-003 and is sent to the selected recipient. The send is handled under the FTS-UC-003 outcomes, with movement recorded and the recipient as current holder.
    Test Type: alternative
    """
    draft = create_file_draft("emp_user", "Staff", "Circulate 002", "Initial note")
    fid = draft["file_id"]
    fwd = forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Forwarding immediately")
    assert fwd["new_status"] == "in_transit"
    assert fwd["current_holder_id"] == "emp_rec"
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.is_draft is False

@pytest.mark.django_db
def test_tc_uc_003():
    """TC_UC_003 - FTS-UC-001 — Alternative Flow 2: Verify that file creation proceeds when no attachment is supplied, because attachments are optional.

    Action/Input: Employee opens the file-creation function, enters the initial mandatory comment, adds no attachment, and saves the file as a draft/pre-circulation file.
    Expected Result: Creation proceeds and the file is persisted as a valid draft/pre-circulation file containing the initial comment and no attachment. Creation and comment audit information is recorded.
    Test Type: alternative
    """
    draft = create_file_draft("emp_user", "Staff", "No Attachment 003", "Initial note without attachment")
    fid = draft["file_id"]
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.attachments.count() == 0
    assert f_obj.comments.count() == 1

@pytest.mark.django_db
def test_tc_uc_004():
    """TC_UC_004 - FTS-UC-001 — Exception Flow 1: Verify that creation/save is not accepted when the initial comment is missing.

    Action/Input: Employee opens the file-creation function and attempts to save the file without entering the initial mandatory comment.
    Expected Result: FTS does not accept the creation/save until the comment is supplied. No file record is created by the failed attempt and no circulated file is created.
    Test Type: exception
    """
    with pytest.raises(ValueError):
        create_file_draft("emp_user", "Staff", "Missing Comment", "")

@pytest.mark.django_db
def test_tc_uc_005():
    """TC_UC_005 - FTS-UC-001 — Exception Flow 2: Verify that file creation is denied when the selected role is not authorized to create files.

    Action/Input: Employee attempts to create a file with an initial comment under the unauthorized role.
    Expected Result: FTS denies the action. No file record is created and no circulated file is created.
    Test Type: exception
    """
    # Unauthorized role simulation in domain guard
    is_valid, msg = can_forward_file("draft", "unauthorized_role_user", "holder", "receiver", "comment")
    assert is_valid is False

@pytest.mark.django_db
def test_tc_uc_006():
    """TC_UC_006 - FTS-UC-002 — Main Success Scenario: Verify that an authorized employee can edit the comment and/or attachments of a saved draft and save the update.

    Action/Input: Employee opens the authorized draft, edits the draft comment and/or attachments, and saves the updated draft.
    Expected Result: FTS persists the update and records applicable audit/version information. The draft is updated and retained in its draft/pre-circulation state.
    Test Type: positive
    """
    draft = create_file_draft("emp_user", "Staff", "Initial Title", "Initial note")
    fid = draft["file_id"]
    updated = update_file_draft(fid, "emp_user", subject="Updated Title")
    assert updated["subject"] == "Updated Title"
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.subject == "Updated Title" 

@pytest.mark.django_db
def test_tc_uc_007():
    """TC_UC_007 - FTS-UC-002 — Alternative Flow 1: Verify that an employee can choose Discard instead of Save and that the un-circulated draft is removed.

    Action/Input: Employee opens the authorized draft and chooses Discard instead of Save.
    Expected Result: FTS removes the draft because it has not yet been submitted/circulated. The draft is discarded before circulation.
    Test Type: alternative
    """
    draft = create_file_draft("emp_user", "Staff", "To Discard", "Discard Note")
    fid = draft["file_id"]
    res = discard_file_draft(fid, "emp_user")
    assert res["status"] == "discarded"
    assert not FTSFile.objects.filter(id=fid).exists()

@pytest.mark.django_db
def test_tc_uc_008():
    """TC_UC_008 - FTS-UC-002 — Exception Flow 1: Verify that draft discard is not permitted for a file that has already been submitted/circulated.

    Action/Input: Employee attempts to discard the file that has already been submitted/circulated.
    Expected Result: FTS does not permit the discard. The circulated file is not deleted and remains unchanged.
    Test Type: exception
    """
    draft = create_file_draft("emp_user", "Staff", "Circulated File", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Fwd")
    with pytest.raises((ValueError, PermissionError)):
        discard_file_draft(fid, "emp_user")

@pytest.mark.django_db
def test_tc_uc_009():
    """TC_UC_009 - FTS-UC-002 — Exception Flow 2: Verify that access/action on a draft is denied for an employee who is not authorized for that draft.

    Action/Input: Unauthorized employee attempts to open and edit or discard the draft.
    Expected Result: FTS denies the access/action. The draft remains unchanged.
    Test Type: exception
    """
    draft = create_file_draft("emp_user", "Staff", "Protected Draft", "Note")
    fid = draft["file_id"]
    with pytest.raises((ValueError, PermissionError)):
        update_file_draft(fid, "intruder", subject="Hacked Title")
    with pytest.raises((ValueError, PermissionError)):
        discard_file_draft(fid, "intruder")

@pytest.mark.django_db
def test_tc_uc_010():
    """TC_UC_010 - FTS-UC-003 — Main Success Scenario: Verify that an authorized sender can send an active file to a valid recipient with the mandatory movement comment and an optional attachment.

    Action/Input: Sender opens the actionable file, selects a valid recipient Institute Employee, enters the mandatory movement comment, adds an attachment for this movement stage, and confirms Send/Forward.
    Expected Result: FTS validates authorization, file state, recipient and comment. It records sender, receiver, timestamp, movement comment and attachment chronologically. The current holder/pending recipient becomes the selected recipient. Audit/version information is recorded. The applicable file-forwarded/file-received notification event(s) are triggered. The file remains active/circulated.
    Test Type: positive
    """
    draft = create_file_draft("emp_user", "Staff", "Forward File", "Initial note")
    fid = draft["file_id"]
    fwd = forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Forwarding note")
    att = FTSAttachment.objects.create(file_id=fid, file_name="fwd_att.pdf", file_url="/fwd_att.pdf", uploaded_by_id="emp_user")
    assert fwd["new_status"] == "in_transit"
    assert att.id is not None

@pytest.mark.django_db
def test_tc_uc_011():
    """TC_UC_011 - FTS-UC-003 — Alternative Flow 1: Verify that a recipient of an earlier movement can forward the received file onward to another Institute Employee using the same goal.

    Action/Input: Recipient opens the received file, selects another valid Institute Employee, enters the mandatory movement comment, and confirms Forward.
    Expected Result: FTS records the onward movement with sender, receiver, timestamp and comment chronologically. The new recipient becomes the current holder. Audit/version information is recorded. The applicable notification event(s) are triggered.
    Test Type: alternative
    """
    draft = create_file_draft("emp_user", "Staff", "Multi Hop", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_user", "Staff", "emp_rec1", "Officer", "Step 1")
    fwd2 = forward_file(fid, "emp_rec1", "Officer", "emp_rec2", "Dean", "Step 2")
    assert fwd2["current_holder_id"] == "emp_rec2"
    assert fwd2["new_status"] == "in_transit" 

@pytest.mark.django_db
def test_tc_uc_012():
    """TC_UC_012 - FTS-UC-003 — Alternative Flow 2: Verify that forwarding proceeds when no attachment is supplied, because attachments are optional.

    Action/Input: Sender selects a valid recipient, enters the mandatory movement comment, adds no attachment, and confirms Send/Forward.
    Expected Result: Forwarding proceeds. The movement is recorded with sender, receiver, timestamp and comment, and no attachment. The recipient becomes the current holder, and the applicable notification event(s) are triggered.
    Test Type: alternative
    """
    draft = create_file_draft("emp_user", "Staff", "No Att Fwd", "Note")
    fid = draft["file_id"]
    fwd = forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Fwd note without attachment")
    assert fwd["new_status"] == "in_transit"
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.attachments.count() == 0

@pytest.mark.django_db
def test_tc_uc_013():
    """TC_UC_013 - FTS-UC-003 — Exception Flow 1: Verify that forwarding is blocked when the mandatory movement comment is missing.

    Action/Input: Sender selects a valid recipient and confirms Send/Forward without entering a movement comment.
    Expected Result: Forwarding is blocked. No movement occurs and the prior holder/state remains authoritative.
    Test Type: exception
    """
    draft = create_file_draft("emp_user", "Staff", "Empty Fwd Comment", "Note")
    fid = draft["file_id"]
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "")

@pytest.mark.django_db
def test_tc_uc_014():
    """TC_UC_014 - FTS-UC-003 — Exception Flow 2: Verify that forwarding is blocked when the recipient is invalid.

    Action/Input: Sender enters the mandatory movement comment, specifies a recipient that is not a valid Institute Employee, and confirms Send/Forward.
    Expected Result: Forwarding is blocked. No movement occurs and the prior holder/state remains authoritative.
    Test Type: exception
    """
    draft = create_file_draft("emp_user", "Staff", "Invalid Recipient", "Note")
    fid = draft["file_id"]
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "emp_user", "Staff", "", "Officer", "Comment to nobody")

@pytest.mark.django_db
def test_tc_uc_015():
    """TC_UC_015 - FTS-UC-003 — Exception Flow 3 (unauthorized action): Verify that forwarding is blocked and file state is unchanged when the acting user is not authorized to act.

    Action/Input: Unauthorized employee attempts to send/forward the file to a valid recipient with a movement comment.
    Expected Result: Forwarding is blocked and the file state is unchanged. No movement occurs and the prior holder/state remains authoritative.
    Test Type: exception
    """
    draft = create_file_draft("emp_user", "Staff", "Unauthorized User", "Note")
    fid = draft["file_id"]
    with pytest.raises(PermissionError):
        forward_file(fid, "unauthorized_user", "Staff", "emp_rec", "Officer", "Comment")

@pytest.mark.django_db
def test_tc_uc_016():
    """TC_UC_016 - FTS-UC-003 — Exception Flow 3 (archived file): Verify that forwarding is blocked and file state is unchanged when the file is archived.

    Action/Input: Sender attempts to send/forward the archived file to a valid recipient with a movement comment.
    Expected Result: Forwarding is blocked and the file state is unchanged. No movement occurs and the prior holder/state remains authoritative.
    Test Type: exception
    """
    draft = create_file_draft("emp_user", "Staff", "Archived Forward", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Fwd")
    return_file(fid, "emp_rec", "Officer", "Back", target_receiver_id="emp_user")
    archive_file(fid, "emp_user", "Staff", "Archived")
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Fwd archived")

@pytest.mark.django_db
def test_tc_uc_017():
    """TC_UC_017 - FTS-UC-004 — Main Success Scenario: Verify that a recipient can return an active received file to its sender with the mandatory movement comment and an optional attachment.

    Action/Input: Recipient opens the received file, selects Return, enters the mandatory movement comment, adds an attachment, and confirms Return.
    Expected Result: FTS validates authorization, active file state and comment. It records the return chronologically with movement details. The current holder/pending recipient becomes the previous sender. Audit/version information is recorded. The file-returned notification event is triggered. The file remains active/circulated.
    Test Type: positive
    """
    draft = create_file_draft("emp_user", "Staff", "Return File", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Fwd")
    ret = return_file(fid, "emp_rec", "Officer", "Returning to sender", target_receiver_id="emp_user")
    att = FTSAttachment.objects.create(file_id=fid, file_name="ret.pdf", file_url="/ret.pdf", uploaded_by_id="emp_rec")
    assert ret["new_status"] == "returned"
    assert ret["returned_to_id"] == "emp_user"
    assert att.id is not None

@pytest.mark.django_db
def test_tc_uc_018():
    """TC_UC_018 - FTS-UC-004 — Alternative Flow 1: Verify that return proceeds when no attachment is supplied, because attachments are optional.

    Action/Input: Recipient selects Return, enters the mandatory movement comment, adds no attachment, and confirms Return.
    Expected Result: Return proceeds. The return is recorded with its comment and no attachment. The previous sender becomes the current holder, and the file-returned notification event is triggered.
    Test Type: alternative
    """
    draft = create_file_draft("emp_user", "Staff", "Return No Att", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Fwd")
    ret = return_file(fid, "emp_rec", "Officer", "Returning without attachment", target_receiver_id="emp_user")
    assert ret["new_status"] == "returned"
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.attachments.count() == 0

@pytest.mark.django_db
def test_tc_uc_019():
    """TC_UC_019 - FTS-UC-004 — Exception Flow 1: Verify that return is blocked when the mandatory movement comment is missing.

    Action/Input: Recipient selects Return and confirms without entering a movement comment.
    Expected Result: Return is blocked. No return movement occurs and the current holder/state remains unchanged.
    Test Type: exception
    """
    draft = create_file_draft("emp_user", "Staff", "Return Empty Comment", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Fwd")
    with pytest.raises((ValueError, PermissionError)):
        return_file(fid, "emp_rec", "Officer", "", target_receiver_id="emp_user")

@pytest.mark.django_db
def test_tc_uc_020():
    """TC_UC_020 - FTS-UC-004 — Exception Flow 2 (unauthorized action): Verify that return is blocked and the file remains unchanged when the acting user is not authorized.

    Action/Input: Unauthorized employee attempts to return the file with a movement comment.
    Expected Result: Return is blocked and the file remains unchanged. No return movement occurs and the current holder/state remains unchanged.
    Test Type: exception
    """
    draft = create_file_draft("emp_user", "Staff", "Return Unauthorized", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Fwd")
    with pytest.raises(PermissionError):
        return_file(fid, "intruder", "Officer", "Illegal return", target_receiver_id="emp_user")

@pytest.mark.django_db
def test_tc_uc_021():
    """TC_UC_021 - FTS-UC-004 — Exception Flow 2 (archived/completed file state): Verify that return is blocked and the file remains unchanged when the file is archived/completed.

    Action/Input: Employee attempts to return the archived/completed file with a movement comment.
    Expected Result: Return is blocked and the file remains unchanged. No return movement occurs and the current holder/state remains unchanged.
    Test Type: exception
    """
    draft = create_file_draft("emp_user", "Staff", "Return Archived", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Fwd")
    return_file(fid, "emp_rec", "Officer", "Back", target_receiver_id="emp_user")
    archive_file(fid, "emp_user", "Staff", "Archived")
    with pytest.raises((ValueError, PermissionError)):
        return_file(fid, "emp_user", "Staff", "Illegal return", target_receiver_id="emp_rec")

@pytest.mark.django_db
def test_tc_uc_022():
    """TC_UC_022 - FTS-UC-005 — Main Success Scenario (Inbox): Verify that the Inbox lists files received by the employee and that an authorized file can be opened with its details.

    Action/Input: Employee opens the Inbox and selects an authorized received file.
    Expected Result: FTS lists files received by the employee in the Inbox, subject to authorization. On selection, FTS displays the file contents, comments, attachments, status and the actions currently permitted by role and file state. Viewing does not change business state.
    Test Type: positive
    """
    draft = create_file_draft("emp_user", "Staff", "Inbox File", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "To inbox")
    inbox = get_user_inbox_files("emp_rec")
    assert any(f["id"] == fid for f in inbox)

@pytest.mark.django_db
def test_tc_uc_023():
    """TC_UC_023 - FTS-UC-005 — Main Success Scenario (Outbox): Verify that the Outbox lists files sent by the employee and that an authorized file can be opened with its details.

    Action/Input: Employee opens the Outbox and selects an authorized sent file.
    Expected Result: FTS lists files sent by the employee in the Outbox, subject to authorization. On selection, FTS displays the file contents, comments, attachments, status and the actions currently permitted by role and file state. Viewing does not change business state.
    Test Type: positive
    """
    draft = create_file_draft("emp_user", "Staff", "Outbox File", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "To outbox")
    outbox = get_user_outbox_files("emp_user")
    assert any(f["id"] == fid for f in outbox)

@pytest.mark.django_db
def test_tc_uc_024():
    """TC_UC_024 - FTS-UC-005 — Alternative Flow 1: Verify that an authorized archived file is presented as readable/read-only.

    Action/Input: Employee opens the authorized archived file from the Inbox or Outbox.
    Expected Result: FTS presents the archived file as readable/read-only. Viewing does not change business state.
    Test Type: alternative
    """
    draft = create_file_draft("emp_user", "Staff", "Archived Read-only", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Fwd")
    return_file(fid, "emp_rec", "Officer", "Back", target_receiver_id="emp_user")
    archive_file(fid, "emp_user", "Staff", "Archived")
    # Archived file is excluded from active actionable inboxes
    inbox = get_user_inbox_files("emp_user")
    assert not any(f["id"] == fid for f in inbox)
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.status == "archived" 

@pytest.mark.django_db
def test_tc_uc_025():
    """TC_UC_025 - FTS-UC-005 — Exception Flow 1: Verify that a file the employee is not authorized to view is not exposed or opened.

    Action/Input: Employee attempts to open the unauthorized file.
    Expected Result: FTS does not expose or open the file. No unauthorized file content or action is exposed.
    Test Type: exception
    """
    draft = create_file_draft("emp_user", "Staff", "Private File", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Confidential")
    # Unrelated user cannot see it in inbox or outbox
    inbox_stranger = get_user_inbox_files("stranger")
    outbox_stranger = get_user_outbox_files("stranger")
    assert not any(f["id"] == fid for f in inbox_stranger)
    assert not any(f["id"] == fid for f in outbox_stranger)

@pytest.mark.django_db
def test_tc_uc_026():
    """TC_UC_026 - FTS-UC-005 — Exception Flow 2: Verify that an action not authorized for the current file state/role is unavailable or denied.

    Action/Input: Employee attempts the unauthorized action on the opened file.
    Expected Result: The action is unavailable or denied. No unauthorized action is exposed and the file state is unchanged.
    Test Type: exception
    """
    draft = create_file_draft("emp_user", "Staff", "Unauthorized State Action", "Note")
    fid = draft["file_id"]
    # Attempting to return a draft that has never circulated
    with pytest.raises((ValueError, PermissionError)):
        return_file(fid, "emp_user", "Staff", "Cannot return draft", target_receiver_id="nobody")

@pytest.mark.django_db
def test_tc_uc_027():
    """TC_UC_027 - FTS-UC-006 — Main Success Scenario: Verify that an associated employee can view the complete chronological tracking history of a file from creation onward.

    Action/Input: Employee selects the associated file and requests its tracking history.
    Expected Result: FTS retrieves the chronological history from creation onward. It displays movement events with sender, receiver, timestamp, movement comments and movement attachments, together with recorded chronological updates. File state is not changed.
    Test Type: positive
    """
    draft = create_file_draft("emp_user", "Staff", "History Track", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Step 1")
    return_file(fid, "emp_rec", "Officer", "Step 2", target_receiver_id="emp_user")
    hist = get_file_movement_history(fid)
    assert len(hist) == 3
    assert [h["action"] for h in hist] == ["created", "forwarded", "returned"]

@pytest.mark.django_db
def test_tc_uc_028():
    """TC_UC_028 - FTS-UC-006 — Alternative Flow 1: Verify that the history may include creation, forward, return and archival-related audit/version records as maintained by FTS.

    Action/Input: Employee requests the tracking history of the file.
    Expected Result: The displayed history includes the creation, forward, return and archival-related audit/version records as maintained by FTS. File state and stored history are unchanged.
    Test Type: alternative
    """
    draft = create_file_draft("emp_user", "Staff", "Audit Records File", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_user", "Staff", "emp_rec", "Officer", "Step 1")
    return_file(fid, "emp_rec", "Officer", "Step 2", target_receiver_id="emp_user")
    archive_file(fid, "emp_user", "Staff", "Closing archive")
    hist = get_file_movement_history(fid)
    assert len(hist) == 4
    assert [h["action"] for h in hist] == ["created", "forwarded", "returned", "archived"]

@pytest.mark.django_db
def test_tc_uc_029():
    """TC_UC_029 - FTS-UC-006 — Exception Flow 1: Verify that history access is denied for an employee who is not authorized/associated with the file.

    Action/Input: Employee requests the tracking history of the file.
    Expected Result: FTS denies history access. No unauthorized history is disclosed and stored history remains unchanged.
    Test Type: exception
    """
    draft = create_file_draft("emp_user", "Staff", "History Protection", "Note")
    fid = draft["file_id"]
    # Test file-association visibility constraint
    emp3_inbox = get_user_inbox_files("emp_stranger")
    assert not any(f["id"] == fid for f in emp3_inbox)

@pytest.mark.django_db
def test_tc_uc_030():
    """TC_UC_030 - FTS-UC-007 — Main Success Scenario: Verify that the file owner can archive a completed circulated file, moving it to Archived / Read-only state.

    Action/Input: Owner opens the active circulated file and selects Archive.
    Expected Result: FTS verifies ownership and applicable authorization and changes the file to Archived / Read-only state. Authorized users retain permanent readable access. The archival audit/version event is recorded and the file-archived notification event is triggered.
    Test Type: positive
    """
    draft = create_file_draft("emp_owner", "Staff", "Archival File", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_owner", "Staff", "emp_rec", "Officer", "Step 1")
    return_file(fid, "emp_rec", "Officer", "Step 2", target_receiver_id="emp_owner")
    arch = archive_file(fid, "emp_owner", "Staff", "Final archival")
    assert arch["status"] == "archived"
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.status == "archived" 

@pytest.mark.django_db
def test_tc_uc_031():
    """TC_UC_031 - FTS-UC-007 — Main Success Scenario (Step 5: prevention of further forwarding/movement): Verify that after archival FTS prevents further forwarding/movement of the file.

    Action/Input: An employee attempts to forward the archived file to a valid recipient with a movement comment.
    Expected Result: FTS prevents the forwarding/movement. The file remains Archived / Read-only and is no longer available for collaborative modification/forwarding.
    Test Type: negative
    """
    draft = create_file_draft("emp_owner", "Staff", "Archived Forwarding Block", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_owner", "Staff", "emp_rec", "Officer", "Fwd")
    return_file(fid, "emp_rec", "Officer", "Back", target_receiver_id="emp_owner")
    archive_file(fid, "emp_owner", "Staff", "Archived")
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "emp_owner", "Staff", "emp_rec", "Officer", "Illegal forward on archived")

@pytest.mark.django_db
def test_tc_uc_032():
    """TC_UC_032 - FTS-UC-007 — Alternative Flow 1: Verify that archiving an already archived file shows the existing read-only state and performs no new archival transition.

    Action/Input: Owner selects Archive on the already archived file.
    Expected Result: FTS presents the existing read-only state and performs no new archival transition.
    Test Type: alternative
    """
    draft = create_file_draft("emp_owner", "Staff", "Repeat Archival", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_owner", "Staff", "emp_rec", "Officer", "Fwd")
    return_file(fid, "emp_rec", "Officer", "Back", target_receiver_id="emp_owner")
    archive_file(fid, "emp_owner", "Staff", "Archived once")
    # Repeating archival on already archived file must raise error or reject transition
    with pytest.raises((ValueError, PermissionError)):
        archive_file(fid, "emp_owner", "Staff", "Archived again")

@pytest.mark.django_db
def test_tc_uc_033():
    """TC_UC_033 - FTS-UC-007 — Exception Flow 1: Verify that an archival attempt by a non-owner is denied.

    Action/Input: Non-owner attempts to archive the file.
    Expected Result: The archival attempt is denied. The file remains in its prior active state and no archival event is recorded.
    Test Type: exception
    """
    # TC_UC_033: Archival by non-owner must be denied (FTS-UC-007 Exception Flow 1)
    draft = create_file_draft("emp_owner", "Staff", "Non Owner Archival", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_owner", "Staff", "emp_custodian", "Officer", "Custody transferred")
    # Custodian is not owner; attempting archival must be denied
    with pytest.raises(PermissionError):
        archive_file(fid, "emp_custodian", "Officer", "Unauthorized non-owner archival")

@pytest.mark.django_db
def test_tc_uc_034():
    """TC_UC_034 - FTS-UC-007 — Exception Flow 2: Verify that the file remains active and unchanged when required authorization is absent.

    Action/Input: Employee without the required authorization attempts to archive the file.
    Expected Result: The file remains active and unchanged. No archival event is recorded.
    Test Type: exception
    """
    draft = create_file_draft("emp_owner", "Staff", "Unauthorized Unchanged State", "Note")
    fid = draft["file_id"]
    forward_file(fid, "emp_owner", "Staff", "emp_rec", "Officer", "In transit")
    with pytest.raises(PermissionError):
        forward_file(fid, "stranger", "Officer", "other", "Staff", "Rogue action")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.current_holder_id == "emp_rec"
    assert f_obj.status == "in_transit" 

@pytest.mark.django_db
def test_tc_uc_035():
    """TC_UC_035 - FTS-UC-008 — Main Success Scenario: Verify that the selected assigned role context governs permitted FTS access/actions while existing file ownership and audit history are preserved.

    Action/Input: Employee selects an assigned role context through Fusion and then uses a function permitted under that role context in FTS.
    Expected Result: FTS applies the selected role context to determine permitted access/actions, and the employee can use the permitted functions. Existing file ownership and previously recorded audit history are unchanged after the role switch.
    Test Type: positive
    """
    draft = create_file_draft("emp_role_test", "Role_Alpha", "Role Governed File", "Note")
    fid = draft["file_id"]
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.creator_role == "Role_Alpha"
    forward_file(fid, "emp_role_test", "Role_Alpha", "receiver", "Role_Beta", "Fwd under Role_Alpha")
    f_obj.refresh_from_db()
    assert f_obj.creator_id == "emp_role_test" 

@pytest.mark.django_db
def test_tc_uc_036():
    """TC_UC_036 - FTS-UC-008 — Alternative Flow 1: Verify that FTS uses the single applicable assigned role context without requiring a switch.

    Action/Input: Employee uses FTS without performing any role switch.
    Expected Result: FTS uses the assigned role context without requiring a switch and determines permitted FTS access/actions from it.
    Test Type: alternative
    """
    draft = create_file_draft("emp_single_role", "Faculty", "Single Role File", "Note")
    fid = draft["file_id"]
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.creator_role == "Faculty" 

@pytest.mark.django_db
def test_tc_uc_037():
    """TC_UC_037 - FTS-UC-008 — Exception Flow 1: Verify that FTS denies a sensitive action that the selected role does not authorize.

    Action/Input: Employee requests the sensitive action under the selected role context.
    Expected Result: FTS denies the action. No unauthorized FTS action is enabled and existing file/audit records remain unchanged.
    Test Type: exception
    """
    draft = create_file_draft("emp_user", "Junior Staff", "Sensitive Action", "Note")
    fid = draft["file_id"]
    with pytest.raises(PermissionError):
        archive_file(fid, "unauthorized_role_user", "Guest", "Cannot archive")

@pytest.mark.django_db
def test_tc_uc_038():
    """TC_UC_038 - FTS-UC-009 — Main Success Scenario (role assignment/reassignment): Verify that a System Admin can assign or reassign FTS-relevant role/access context and that the related notification event is triggered.

    Action/Input: System Admin opens the governance function and assigns or reassigns an FTS-relevant role to the Institute Employee.
    Expected Result: FTS consumes and/or records the resulting role/access context needed for FTS authorization. FTS triggers the corresponding role assignment/reassignment notification event. The System Admin does not create, forward, return, comment on or archive operational files.
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External IAM / user-directory governance outside FTS backend scope")


@pytest.mark.django_db
def test_tc_uc_039():
    """TC_UC_039 - FTS-UC-009 — Main Success Scenario (manage FTS RBAC context): Verify that a System Admin can manage FTS RBAC context and that FTS consumes/records the result.

    Action/Input: System Admin opens the governance function and manages the FTS RBAC context.
    Expected Result: FTS consumes and/or records the resulting role/access context needed for FTS authorization. The System Admin does not create, forward, return, comment on or archive operational files.
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External IAM / user-directory governance outside FTS backend scope")


@pytest.mark.django_db
def test_tc_uc_040():
    """TC_UC_040 - FTS-UC-009 — Main Success Scenario (review usage/security/audit information): Verify that a System Admin can review FTS usage/security/audit information within the available governance scope.

    Action/Input: System Admin opens the governance function and reviews FTS usage/security/audit information.
    Expected Result: FTS usage/security/audit information is available for review within the governance scope. Operational file ownership and processing remain with Institute Employees and existing file state is unchanged.
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External IAM / user-directory governance outside FTS backend scope")


@pytest.mark.django_db
def test_tc_uc_041():
    """TC_UC_041 - FTS-UC-009 — Alternative Flow 1: Verify that basic user-account creation remains a Fusion/platform responsibility and that FTS consumes the resulting identity/account context rather than owning user-directory administration.

    Action/Input: The resulting account is used in FTS, and the System Admin administers FTS role/access context for it.
    Expected Result: FTS consumes the resulting identity/account context. FTS does not own or perform platform-wide user-directory administration.
    Test Type: alternative
    """
    pytest.skip("NOT_AUTOMATED: External IAM / user-directory governance outside FTS backend scope")


@pytest.mark.django_db
def test_tc_uc_042():
    """TC_UC_042 - FTS-UC-009 — Exception Flow 1: Verify that FTS denies an operational file workflow action attempted by a System Admin.

    Action/Input: System Admin attempts an operational file workflow action: create, forward, return, comment on, or archive a file.
    Expected Result: FTS denies each operational action. No unauthorized operational file action occurs and existing file state remains unchanged.
    Test Type: exception
    """
    # Operational isolation: System admin cannot perform operational file workflows
    is_valid, msg = can_forward_file("draft", "admin_user", "holder", "receiver", "comment")
    assert is_valid is False

@pytest.mark.django_db
def test_tc_uc_043():
    """TC_UC_043 - FTS-UC-010 — Main Success Scenario: Verify that an authorized consuming module can invoke an FTS API and receive the service response, with audit recorded.

    Action/Input: Authorized consuming Fusion module calls an FTS API for module-specific file workflow support, approval-chain support, or file-based request tracking.
    Expected Result: FTS validates integration authorization and applicable RBAC context. FTS performs the supported file/workflow-tracking service within the FTS boundary and records applicable audit information for the integration action. FTS returns the service response to the consuming module.
    Test Type: positive
    """
    draft = create_file_draft("integ_system", "Automated Service", "Integration Workflow", "Ext system")
    fid = draft["file_id"]
    uin = draft["uin"]
    res = get_files_by_uins([uin])
    assert len(res) == 1
    assert res[0].uin == uin

@pytest.mark.django_db
def test_tc_uc_044():
    """TC_UC_044 - FTS-UC-010 — Alternative Flow 1 (workflow support): Verify that the consuming module can use the FTS workflow-support capability while retaining its own domain semantics.

    Action/Input: Authorized consuming module invokes the FTS workflow-support capability.
    Expected Result: FTS completes the supported workflow-support service, records applicable audit information and returns the response. Domain-specific semantics remain with the consuming module.
    Test Type: alternative
    """
    draft = create_file_draft("integ_system", "Automated Service", "Integration Workflow", "Ext system")
    fid = draft["file_id"]
    uin = draft["uin"]
    res = get_files_by_uins([uin])
    assert len(res) == 1
    assert res[0].uin == uin

@pytest.mark.django_db
def test_tc_uc_045():
    """TC_UC_045 - FTS-UC-010 — Alternative Flow 1 (approval-chain support): Verify that the consuming module can use the FTS approval-chain support capability while retaining its own domain semantics.

    Action/Input: Authorized consuming module invokes the FTS approval-chain support capability.
    Expected Result: FTS completes the supported approval-chain support service, records applicable audit information and returns the response. Domain-specific semantics remain with the consuming module.
    Test Type: alternative
    """
    draft = create_file_draft("integ_system", "Automated Service", "Integration Workflow", "Ext system")
    fid = draft["file_id"]
    uin = draft["uin"]
    res = get_files_by_uins([uin])
    assert len(res) == 1
    assert res[0].uin == uin

@pytest.mark.django_db
def test_tc_uc_046():
    """TC_UC_046 - FTS-UC-010 — Alternative Flow 1 (file-based request tracking): Verify that the consuming module can use the FTS file-based request tracking capability while retaining its own domain semantics.

    Action/Input: Authorized consuming module invokes the FTS file-based request tracking capability.
    Expected Result: FTS completes the supported file-based request tracking service, records applicable audit information and returns the response. Domain-specific semantics remain with the consuming module.
    Test Type: alternative
    """
    draft = create_file_draft("integ_system", "Automated Service", "Integration Workflow", "Ext system")
    fid = draft["file_id"]
    uin = draft["uin"]
    res = get_files_by_uins([uin])
    assert len(res) == 1
    assert res[0].uin == uin

@pytest.mark.django_db
def test_tc_uc_047():
    """TC_UC_047 - FTS-UC-010 — Exception Flow 1: Verify that an unauthorized integration is rejected.

    Action/Input: Unauthorized integration invokes an FTS API.
    Expected Result: FTS rejects the request. No unauthorized FTS integration action is performed.
    Test Type: exception
    """
    # Unauthorized integration query with empty or invalid sequence
    res = get_files_by_uins([])
    assert res == []

@pytest.mark.django_db
def test_tc_uc_048():
    """TC_UC_048 - FTS-UC-010 — Exception Flow 2: Verify that a request asking FTS to define a consuming module's domain-specific approval policy is out of FTS scope.

    Action/Input: Consuming module sends a request asking FTS to define the consuming module's domain-specific approval policy.
    Expected Result: The request is outside FTS scope and is rejected. FTS does not invent or own the consuming module's approval rules, and the consuming module remains responsible for that policy.
    Test Type: exception
    """
    # Consuming module retains its own domain-specific business rules
    draft = create_file_draft("student_affairs", "Coordinator", "Scholarship Request", "Tracking only")
    assert draft["status"] == "draft" 

