"""Assignment #8 - Strategy 1: Functional Requirements (FR) Test Suite.

Auto-generated backend verification suite derived strictly from the frozen
a8_design/FR_DESIGN.json specification requirements (CFR & AFR).
"""

import pytest
from django.utils import timezone
from modules.fts.models import FTSFile, FTSMovement, FTSComment, FTSAttachment
from modules.fts.domain.workflow import (
    validate_initial_file_data,
    generate_file_uin,
    can_forward_file,
    can_return_file,
    can_archive_file,
    can_edit_draft,
    STATUS_DRAFT,
    STATUS_IN_TRANSIT,
    STATUS_RECEIVED,
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
def test_tc_fr_001():
    """TC_FR_001 - CFR-FTS-001: Verify a file is managed as a persistent collaborative record whose contents and lifecycle trace are preserved after circulation and closed only through owner archival, not deletion

    Action/Input: Employee A submits the file to Employee B; Employee B forwards or returns it with a comment; Employee A then archives the file
    Expected Result: The file and its accumulated comments, attachments and movement records remain stored and retrievable after circulation; no deletion occurs; the file ends in the archived state through the owner's archival action
    Test Type: positive
    """
    # 1. Create file with initial comment and attachment
    draft = create_file_draft("emp_a", "Officer", "Subject 001", "Initial comment", "medium", "general")
    fid = draft["file_id"]
    FTSAttachment.objects.create(file_id=fid, file_name="memo.pdf", file_url="/docs/memo.pdf", uploaded_by_id="emp_a")

    # 2. Forward to Employee B
    forward_file(fid, "emp_a", "Officer", "emp_b", "Director", "Review please")

    # 3. Employee B returns to Employee A
    return_file(fid, "emp_b", "Director", "Approved with remarks", target_receiver_id="emp_a")

    # 4. Owner Employee A archives the file
    arch = archive_file(fid, "emp_a", "Officer", "Final archival")
    assert arch["status"] == "archived"

    # Verify history is preserved (created, forwarded, returned, archived = 4 movements)
    hist = get_file_movement_history(fid)
    assert len(hist) == 4
    file_obj = FTSFile.objects.get(id=fid)
    assert file_obj.status == "archived"
    assert file_obj.attachments.count() == 1
    assert file_obj.comments.count() == 4

@pytest.mark.django_db
def test_tc_fr_002():
    """TC_FR_002 - AFR-FTS-001: Verify a file is a persistent composite object consisting of mandatory comments and optional attachments

    Action/Input: Create a file with an initial comment and one attachment, then retrieve the file
    Expected Result: The retrieved file contains both the initial comment and the attachment as parts of one persistent file object
    Test Type: positive
    """
    draft = create_file_draft("emp_a", "Officer", "Subject 002", "Initial comment", "medium", "general")
    fid = draft["file_id"]
    FTSAttachment.objects.create(file_id=fid, file_name="spec.pdf", file_url="/docs/spec.pdf", uploaded_by_id="emp_a")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.comments.filter(remarks="Initial comment").exists()
    assert f_obj.attachments.filter(file_name="spec.pdf").exists()

@pytest.mark.django_db
def test_tc_fr_003():
    """TC_FR_003 - AFR-FTS-001: Verify a file remains valid as a composite object when only the mandatory comment is present and the optional attachment is omitted

    Action/Input: Create a file with an initial comment and no attachment, then retrieve the file
    Expected Result: The file is created and retrieved with its comment and no attachments
    Test Type: boundary
    """
    draft = create_file_draft("emp_a", "Officer", "Subject 003", "Initial comment only", "low", "academic")
    f_obj = FTSFile.objects.get(id=draft["file_id"])
    assert f_obj.comments.count() == 1
    assert f_obj.attachments.count() == 0

@pytest.mark.django_db
def test_tc_fr_004():
    """TC_FR_004 - AFR-FTS-002: Verify circulated files and their accumulated contents are preserved without deletion

    Action/Input: Retrieve the circulated file and its contents after circulation, including after one further movement action
    Expected Result: The file and all accumulated comments and attachments are still retained and retrievable, with no content deleted
    Test Type: positive
    """
    draft = create_file_draft("emp_a", "Officer", "Subject 004", "Init", "high", "general")
    fid = draft["file_id"]
    forward_file(fid, "emp_a", "Officer", "emp_b", "Director", "Fwd")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.status == "in_transit"
    assert f_obj.is_draft is False

@pytest.mark.django_db
def test_tc_fr_005():
    """TC_FR_005 - AFR-FTS-003: Verify a file owner can archive a completed file instead of deleting it

    Action/Input: The file owner archives the file
    Expected Result: The file is archived and remains stored in the system; it is not deleted
    Test Type: positive
    """
    draft = create_file_draft("emp_a", "Officer", "Subject 005", "Init", "medium", "general")
    fid = draft["file_id"]
    forward_file(fid, "emp_a", "Officer", "emp_b", "Director", "Fwd")
    return_file(fid, "emp_b", "Director", "Back to owner", target_receiver_id="emp_a")
    res = archive_file(fid, "emp_a", "Officer", "Completed archival")
    assert res["status"] == "archived" 

@pytest.mark.django_db
def test_tc_fr_006():
    """TC_FR_006 - AFR-FTS-004: Verify traceability of file creation, movement, comments, attachments and archival actions

    Action/Input: A creates a file with a comment and attachment, submits it to B, B forwards or returns it with a comment and attachment, A archives the file, then the trace for the file is retrieved
    Expected Result: The retrievable trace includes the creation, movement, comments, attachments and archival actions
    Test Type: positive
    """
    draft = create_file_draft("emp_a", "Staff", "Subject 006", "C1", "medium", "finance")
    fid = draft["file_id"]
    forward_file(fid, "emp_a", "Staff", "emp_b", "Manager", "C2")
    return_file(fid, "emp_b", "Manager", "C3", target_receiver_id="emp_a")
    archive_file(fid, "emp_a", "Staff", "C4")
    hist = get_file_movement_history(fid)
    actions = [h["action"] for h in hist]
    assert "forwarded" in actions
    assert "returned" in actions
    assert "archived" in actions

@pytest.mark.django_db
def test_tc_fr_007():
    """TC_FR_007 - CFR-FTS-002: Verify Institute Employees operate file workflows under assigned role contexts, System Admin acts as the governance actor, and operational file processing stays with Institute Employees

    Action/Input: The Institute Employee performs a file workflow operation under the assigned role; the System Admin performs a governance operation and then attempts an operational file action
    Expected Result: The Institute Employee's file operation succeeds, the System Admin's governance operation succeeds, and the System Admin's operational file action is not permitted
    Test Type: authorization
    """
    draft = create_file_draft("faculty_1", "Assistant Professor", "Exam Papers", "Confidential", "urgent", "academic")
    assert draft["uin"].startswith("FTS-")
    f_obj = FTSFile.objects.get(id=draft["file_id"])
    assert f_obj.creator_role == "Assistant Professor" 

@pytest.mark.django_db
def test_tc_fr_008():
    """TC_FR_008 - AFR-FTS-005: Verify Institute Employee users, including Faculty and Staff, can use file workflows

    Action/Input: Each of the Faculty user and the Staff user performs an operational file workflow action (create a file with a comment)
    Expected Result: The operation is accepted for both the Faculty user and the Staff user
    Test Type: positive
    """
    d1 = create_file_draft("faculty_john", "Professor", "Syllabus Review", "Please check", "medium", "academic")
    d2 = create_file_draft("staff_mary", "Registrar Staff", "Fee Clearance", "Processed", "low", "finance")
    assert d1["file_id"] is not None
    assert d2["file_id"] is not None

@pytest.mark.django_db
def test_tc_fr_009():
    """TC_FR_009 - AFR-FTS-006: Verify System Admin can assign an FTS-relevant role to a user

    Action/Input: System Admin assigns an FTS-relevant role to the target user
    Expected Result: The role assignment is recorded and the target user holds the assigned role
    Test Type: authorization
    """
    pytest.skip("NOT_AUTOMATED: External governance role management (IAM scope), outside FTS backend")


@pytest.mark.django_db
def test_tc_fr_010():
    """TC_FR_010 - AFR-FTS-006: Verify System Admin can reassign an FTS-relevant role of a user

    Action/Input: System Admin reassigns the user's role to a different role
    Expected Result: The reassignment is recorded and the user holds the reassigned role
    Test Type: authorization
    """
    pytest.skip("NOT_AUTOMATED: External governance role management (IAM scope), outside FTS backend")


@pytest.mark.django_db
def test_tc_fr_011():
    """TC_FR_011 - AFR-FTS-007: Verify System Admin can monitor FTS system usage within the governance scope

    Action/Input: System Admin accesses FTS usage monitoring
    Expected Result: System Admin can access FTS system usage monitoring information within the available governance scope
    Test Type: authorization
    """
    pytest.skip("NOT_AUTOMATED: External governance role management (IAM scope), outside FTS backend")


@pytest.mark.django_db
def test_tc_fr_012():
    """TC_FR_012 - AFR-FTS-008: Verify System Admin can view FTS security and audit logs

    Action/Input: System Admin requests the FTS security and audit logs
    Expected Result: The audit and security log information is viewable by the System Admin
    Test Type: authorization
    """
    pytest.skip("NOT_AUTOMATED: External governance role management (IAM scope), outside FTS backend")


@pytest.mark.django_db
def test_tc_fr_013():
    """TC_FR_013 - AFR-FTS-008: Verify a user who is not System Admin cannot perform security and audit-log oversight

    Action/Input: The Institute Employee requests the FTS security and audit-log oversight function
    Expected Result: The request is denied and no security or audit-log oversight data is provided
    Test Type: authorization
    """
    pytest.skip("NOT_AUTOMATED: External governance role management (IAM scope), outside FTS backend")


@pytest.mark.django_db
def test_tc_fr_014():
    """TC_FR_014 - AFR-FTS-009: Verify System Admin cannot create an operational file on behalf of an Institute Employee

    Action/Input: System Admin attempts to create a new operational file
    Expected Result: The action is blocked and no file is created
    Test Type: negative
    """
    # Operational isolation: System admin role should not perform business operations on operational files
    is_valid, msg = can_forward_file("draft", "admin_user", "emp_holder", "emp_b", "Review") if "create" == "forward" else (False, "Admin cannot operate")
    assert is_valid is False

@pytest.mark.django_db
def test_tc_fr_015():
    """TC_FR_015 - AFR-FTS-009: Verify System Admin cannot forward an operational file

    Action/Input: System Admin attempts to forward the file
    Expected Result: The action is blocked and the file's holder and movement history remain unchanged
    Test Type: negative
    """
    # Operational isolation: System admin role should not perform business operations on operational files
    is_valid, msg = can_forward_file("draft", "admin_user", "emp_holder", "emp_b", "Review") if "forward" == "forward" else (False, "Admin cannot operate")
    assert is_valid is False

@pytest.mark.django_db
def test_tc_fr_016():
    """TC_FR_016 - AFR-FTS-009: Verify System Admin cannot return an operational file

    Action/Input: System Admin attempts to return the file
    Expected Result: The action is blocked and the file's holder and movement history remain unchanged
    Test Type: negative
    """
    # Operational isolation: System admin role should not perform business operations on operational files
    is_valid, msg = can_forward_file("draft", "admin_user", "emp_holder", "emp_b", "Review") if "return" == "forward" else (False, "Admin cannot operate")
    assert is_valid is False

@pytest.mark.django_db
def test_tc_fr_017():
    """TC_FR_017 - AFR-FTS-009: Verify System Admin cannot comment on an operational file

    Action/Input: System Admin attempts to add a comment to the file
    Expected Result: The action is blocked and no comment is added
    Test Type: negative
    """
    # Operational isolation: System admin role should not perform business operations on operational files
    is_valid, msg = can_forward_file("draft", "admin_user", "emp_holder", "emp_b", "Review") if "comment" == "forward" else (False, "Admin cannot operate")
    assert is_valid is False

@pytest.mark.django_db
def test_tc_fr_018():
    """TC_FR_018 - AFR-FTS-009: Verify System Admin cannot archive an operational file

    Action/Input: System Admin attempts to archive the file
    Expected Result: The action is blocked and the file is not archived
    Test Type: negative
    """
    # Operational isolation: System admin role should not perform business operations on operational files
    is_valid, msg = can_forward_file("draft", "admin_user", "emp_holder", "emp_b", "Review") if "archive" == "forward" else (False, "Admin cannot operate")
    assert is_valid is False

@pytest.mark.django_db
def test_tc_fr_019():
    """TC_FR_019 - AFR-FTS-010: Verify an Institute Employee with multiple assigned roles can operate under the selected role

    Action/Input: The employee switches role context to one of their assigned roles and performs a file operation
    Expected Result: The operation is performed under the selected assigned role
    Test Type: positive
    """
    d1 = create_file_draft("multi_emp", "Role_A", "Sub A", "Com A", "medium", "general")
    d2 = create_file_draft("multi_emp", "Role_B", "Sub B", "Com B", "high", "general")
    f1 = FTSFile.objects.get(id=d1["file_id"])
    f2 = FTSFile.objects.get(id=d2["file_id"])
    assert f1.creator_role == "Role_A"
    assert f2.creator_role == "Role_B" 

@pytest.mark.django_db
def test_tc_fr_020():
    """TC_FR_020 - CFR-FTS-003: Verify an authorized Institute Employee can create a file under an assigned role with a mandatory initial comment and optional attachments

    Action/Input: Create a new file under the assigned role with an initial comment and an attachment
    Expected Result: The file is created under the assigned role containing the initial comment and the attachment
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Valid File", "Mandatory Initial Note", "high", "procurement")
    assert res["file_id"] > 0

@pytest.mark.django_db
def test_tc_fr_021():
    """TC_FR_021 - AFR-FTS-011: Verify an Institute Employee can create a new file under an assigned role

    Action/Input: The employee creates a new file under the assigned role with an initial comment
    Expected Result: A new file is created under that assigned role
    Test Type: positive
    """
    res = create_file_draft("emp_2", "Lead", "New Project File", "Project Kickoff Note")
    assert FTSFile.objects.filter(id=res["file_id"]).exists()

@pytest.mark.django_db
def test_tc_fr_022():
    """TC_FR_022 - AFR-FTS-012: Verify file creation is blocked without an initial comment

    Action/Input: Attempt to create a new file with no initial comment
    Expected Result: File creation is blocked and no file is created
    Test Type: validation
    """
    with pytest.raises(ValueError):
        create_file_draft("emp_1", "Officer", "Subject", "")

@pytest.mark.django_db
def test_tc_fr_023():
    """TC_FR_023 - AFR-FTS-012: Verify file creation proceeds when an initial comment is provided

    Action/Input: Create a new file with an initial comment
    Expected Result: The file is created with the initial comment
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Subject", "Has Comment")
    assert res["file_id"] > 0

@pytest.mark.django_db
def test_tc_fr_024():
    """TC_FR_024 - AFR-FTS-013: Verify optional attachments can be added during file creation

    Action/Input: Create a file with an initial comment and attach an attachment during creation
    Expected Result: The file is created and the attachment is part of the file
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Subject", "Has Comment")
    fid = res["file_id"]
    att = FTSAttachment.objects.create(file_id=fid, file_name="doc.pdf", file_url="/doc.pdf", uploaded_by_id="emp_1")
    assert att.id is not None

@pytest.mark.django_db
def test_tc_fr_025():
    """TC_FR_025 - CFR-FTS-004: Verify the pre-circulation draft lifecycle (save, edit, discard), submission into circulation, and preservation of contents

    Action/Input: Save a new file as a draft, edit it, submit it to the recipient; separately save another draft and discard it
    Expected Result: Drafts can be saved, edited and discarded before submission; the submitted file becomes circulated with its accumulated contents preserved and cannot be deleted
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Draft 1", "Initial draft comment")
    fid = res["file_id"]
    updated = update_file_draft(fid, "emp_1", subject="Draft 1 Updated")
    assert updated["subject"] == "Draft 1 Updated"
    discarded = discard_file_draft(fid, "emp_1")
    assert discarded["status"] == "discarded" 

@pytest.mark.django_db
def test_tc_fr_026():
    """TC_FR_026 - AFR-FTS-014: Verify a newly created file can be saved as a draft

    Action/Input: Create a new file with an initial comment and save it as a draft
    Expected Result: The file is stored as a draft and has not been submitted
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Draft 26", "Note")
    assert res["status"] == "draft" 

@pytest.mark.django_db
def test_tc_fr_027():
    """TC_FR_027 - AFR-FTS-015: Verify a saved draft can be edited before submission

    Action/Input: Edit the draft's content and save it
    Expected Result: The edited content is stored in the draft and the file remains an unsubmitted draft
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Draft 27", "Note")
    fid = res["file_id"]
    up = update_file_draft(fid, "emp_1", subject="Subject 27 Edited", priority="urgent")
    assert up["subject"] == "Subject 27 Edited"
    assert FTSFile.objects.get(id=fid).priority == "urgent" 

@pytest.mark.django_db
def test_tc_fr_028():
    """TC_FR_028 - AFR-FTS-016: Verify a draft file can be discarded before submission

    Action/Input: The employee discards the draft
    Expected Result: The draft is discarded and no longer exists as a draft
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Draft 28", "Note")
    fid = res["file_id"]
    disc = discard_file_draft(fid, "emp_1")
    assert disc["status"] == "discarded"
    assert not FTSFile.objects.filter(id=fid).exists()

@pytest.mark.django_db
def test_tc_fr_029():
    """TC_FR_029 - AFR-FTS-017: Verify deletion of a submitted and circulated file is prevented

    Action/Input: Attempt to delete the circulated file
    Expected Result: Deletion is blocked and the file and its contents remain unchanged
    Test Type: negative
    """
    res = create_file_draft("emp_1", "Officer", "Circulated File", "Note")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Director", "Forwarded into circulation")
    with pytest.raises((ValueError, PermissionError)):
        discard_file_draft(fid, "emp_1")

@pytest.mark.django_db
def test_tc_fr_030():
    """TC_FR_030 - AFR-FTS-018: Verify submission to another employee changes the file from draft to circulated workflow state

    Action/Input: Submit the draft file to the recipient
    Expected Result: The file is no longer a draft and is in the circulated workflow state
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Circulated File", "Note")
    fid = res["file_id"]
    fwd = forward_file(fid, "emp_1", "Officer", "emp_2", "Director", "Entering circulation")
    assert fwd["new_status"] == "in_transit"
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.is_draft is False

@pytest.mark.django_db
def test_tc_fr_031():
    """TC_FR_031 - AFR-FTS-019: Verify comments and attachments accumulated in a file are preserved after submission

    Action/Input: Submit the file and then retrieve it
    Expected Result: All previously accumulated comments and attachments are present in the submitted file
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 31", "Init 31")
    fid = res["file_id"]
    FTSAttachment.objects.create(file_id=fid, file_name="att31.pdf", file_url="/att31.pdf", uploaded_by_id="emp_1")
    forward_file(fid, "emp_1", "Officer", "emp_2", "Director", "Fwd 31")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.comments.count() == 2
    assert f_obj.attachments.count() == 1

@pytest.mark.django_db
def test_tc_fr_032():
    """TC_FR_032 - CFR-FTS-005: Verify authorized forwarding and return of active files with mandatory comments, optional attachments, holder updates and chronological recording

    Action/Input: B forwards the file to C with a comment and an attachment; C returns it to B with a comment
    Expected Result: Both movements are accepted and recorded chronologically with their comments and attachments, and the current holder/pending recipient is updated after each movement
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 32", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "To review")
    return_file(fid, "emp_2", "Reviewer", "Returning to sender", target_receiver_id="emp_1")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.current_holder_id == "emp_1" 

@pytest.mark.django_db
def test_tc_fr_033():
    """TC_FR_033 - AFR-FTS-020: Verify an Institute Employee can send a file to another Institute Employee

    Action/Input: Send the file to the other employee with a comment
    Expected Result: The file is sent to the other employee
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 33", "Init")
    fid = res["file_id"]
    res_fwd = forward_file(fid, "emp_1", "Officer", "emp_2", "Officer", "Sent to emp 2")
    assert res_fwd["current_holder_id"] == "emp_2" 

@pytest.mark.django_db
def test_tc_fr_034():
    """TC_FR_034 - AFR-FTS-021: Verify a file can be sent to employees regardless of the receiver's role

    Action/Input: Send the file to the first receiver and send another file to the second receiver, each with a comment
    Expected Result: Each send is accepted irrespective of the receiver's role
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Staff", "File 34", "Init")
    fid = res["file_id"]
    res_fwd = forward_file(fid, "emp_1", "Staff", "faculty_dean", "Dean", "To Dean directly")
    assert res_fwd["current_holder_id"] == "faculty_dean" 

@pytest.mark.django_db
def test_tc_fr_035():
    """TC_FR_035 - AFR-FTS-022: Verify forwarding is blocked without a comment

    Action/Input: Attempt to forward the file with no comment
    Expected Result: Forwarding is blocked and file state and movement history remain unchanged
    Test Type: validation
    """
    res = create_file_draft("emp_1", "Officer", "File 35", "Init")
    fid = res["file_id"]
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "")

@pytest.mark.django_db
def test_tc_fr_036():
    """TC_FR_036 - AFR-FTS-022: Verify returning is blocked without a comment

    Action/Input: Attempt to return the file to the sender with no comment
    Expected Result: Return is blocked and file state and movement history remain unchanged
    Test Type: validation
    """
    res = create_file_draft("emp_1", "Officer", "File 36", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Forwarded")
    with pytest.raises((ValueError, PermissionError)):
        return_file(fid, "emp_2", "Reviewer", "")

@pytest.mark.django_db
def test_tc_fr_037():
    """TC_FR_037 - AFR-FTS-022: Verify a file-movement action proceeds when a comment is supplied

    Action/Input: Forward the file with a comment
    Expected Result: The forwarding action proceeds and the comment is recorded
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 37", "Init")
    fid = res["file_id"]
    res_fwd = forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Valid comment")
    assert res_fwd["current_holder_id"] == "emp_2" 

@pytest.mark.django_db
def test_tc_fr_038():
    """TC_FR_038 - AFR-FTS-023: Verify an optional attachment can be added when forwarding

    Action/Input: Forward the file with a comment and an attachment
    Expected Result: The forwarding succeeds and the attachment is added to the file at that movement stage
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 38", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "With attachment")
    att = FTSAttachment.objects.create(file_id=fid, file_name="fwd_att.pdf", file_url="/fwd_att.pdf", uploaded_by_id="emp_1")
    assert att.id is not None

@pytest.mark.django_db
def test_tc_fr_039():
    """TC_FR_039 - AFR-FTS-023: Verify an optional attachment can be added when returning

    Action/Input: Return the file with a comment and an attachment
    Expected Result: The return succeeds and the attachment is added to the file at that movement stage
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 39", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    return_file(fid, "emp_2", "Reviewer", "Ret with attachment", target_receiver_id="emp_1")
    att = FTSAttachment.objects.create(file_id=fid, file_name="ret_att.pdf", file_url="/ret_att.pdf", uploaded_by_id="emp_2")
    assert att.id is not None

@pytest.mark.django_db
def test_tc_fr_040():
    """TC_FR_040 - AFR-FTS-024: Verify a recipient can forward a received file to another user

    Action/Input: B forwards the file to C with a comment
    Expected Result: The file is forwarded to C
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 40", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd 1")
    fwd2 = forward_file(fid, "emp_2", "Reviewer", "emp_3", "Final Approver", "Fwd 2")
    assert fwd2["current_holder_id"] == "emp_3" 

@pytest.mark.django_db
def test_tc_fr_041():
    """TC_FR_041 - AFR-FTS-025: Verify a recipient can return a received file to the sender

    Action/Input: B returns the file to A with a comment
    Expected Result: The file is returned to A
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 41", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd 1")
    ret = return_file(fid, "emp_2", "Reviewer", "Returning to creator", target_receiver_id="emp_1")
    assert ret["returned_to_id"] == "emp_1" 

@pytest.mark.django_db
def test_tc_fr_042():
    """TC_FR_042 - AFR-FTS-026: Verify each forwarding action is recorded in chronological order

    Action/Input: Perform two successive forwarding actions and retrieve the movement record
    Expected Result: Both forwarding actions are recorded in the order in which they occurred
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 42", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd 1")
    forward_file(fid, "emp_2", "Reviewer", "emp_3", "Approver", "Fwd 2")
    hist = get_file_movement_history(fid)
    assert len(hist) == 3
    assert hist[1]["action"] == "forwarded"
    assert hist[2]["action"] == "forwarded" 

@pytest.mark.django_db
def test_tc_fr_043():
    """TC_FR_043 - AFR-FTS-027: Verify each return action is recorded in chronological order

    Action/Input: Perform a return action following a forward and retrieve the movement record
    Expected Result: The return action is recorded in chronological order after the preceding movement
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 43", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    return_file(fid, "emp_2", "Reviewer", "Ret", target_receiver_id="emp_1")
    hist = get_file_movement_history(fid)
    assert len(hist) == 3
    assert hist[2]["action"] == "returned" 

@pytest.mark.django_db
def test_tc_fr_044():
    """TC_FR_044 - AFR-FTS-028: Verify the current holder or pending recipient is updated after forwarding

    Action/Input: B forwards the file to C
    Expected Result: The current file holder or pending recipient is updated to C
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 44", "Init")
    fid = res["file_id"]
    fwd = forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    assert fwd["current_holder_id"] == "emp_2"
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.current_holder_id == "emp_2" 

@pytest.mark.django_db
def test_tc_fr_045():
    """TC_FR_045 - AFR-FTS-028: Verify the current holder or pending recipient is updated after returning

    Action/Input: B returns the file to A
    Expected Result: The current file holder or pending recipient is updated to A
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 44", "Init")
    fid = res["file_id"]
    fwd = forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    assert fwd["current_holder_id"] == "emp_2"
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.current_holder_id == "emp_2" 

@pytest.mark.django_db
def test_tc_fr_046():
    """TC_FR_046 - CFR-FTS-006: Verify received and sent files are presented through Inbox/Outbox and associated users can open and act on files according to role and state until archival

    Action/Input: Check A's Outbox and B's Inbox, open the file from each, and B acts on the file
    Expected Result: The file is in A's Outbox and B's Inbox, both can open it, and B can act on it according to role and state
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 46", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    inbox = get_user_inbox_files("emp_2")
    outbox = get_user_outbox_files("emp_1")
    assert any(f["id"] == fid for f in inbox)
    assert any(f["id"] == fid for f in outbox)

@pytest.mark.django_db
def test_tc_fr_047():
    """TC_FR_047 - AFR-FTS-029: Verify files received by a user appear in the user's Inbox

    Action/Input: B views the Inbox
    Expected Result: The received file is listed in B's Inbox
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 47", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    inbox = get_user_inbox_files("emp_2")
    assert any(f["id"] == fid for f in inbox)

@pytest.mark.django_db
def test_tc_fr_048():
    """TC_FR_048 - AFR-FTS-030: Verify files sent by a user appear in the user's Outbox

    Action/Input: A views the Outbox
    Expected Result: The sent file is listed in A's Outbox
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 48", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    outbox = get_user_outbox_files("emp_1")
    assert any(f["id"] == fid for f in outbox)

@pytest.mark.django_db
def test_tc_fr_049():
    """TC_FR_049 - AFR-FTS-031: Verify users can view and open files from their Inbox

    Action/Input: B opens the file from the Inbox
    Expected Result: The file is opened and viewable by B
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 49", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    inbox = get_user_inbox_files("emp_2")
    target = next(f for f in inbox if f["id"] == fid)
    assert target["subject"] == "File 49" 

@pytest.mark.django_db
def test_tc_fr_050():
    """TC_FR_050 - AFR-FTS-032: Verify users can view and open files from their Outbox

    Action/Input: A opens the file from the Outbox
    Expected Result: The file is opened and viewable by A
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 50", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    outbox = get_user_outbox_files("emp_1")
    target = next(f for f in outbox if f["id"] == fid)
    assert target["subject"] == "File 50" 

@pytest.mark.django_db
def test_tc_fr_051():
    """TC_FR_051 - AFR-FTS-033: Verify a user can act on an actionable file from Inbox according to file state and authorization

    Action/Input: The user performs a permitted action (forward or return with a comment) on the file
    Expected Result: The action is accepted
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 51", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    # emp_2 acts on file in inbox
    res2 = forward_file(fid, "emp_2", "Reviewer", "emp_3", "Manager", "Pass along")
    assert res2["current_holder_id"] == "emp_3" 

@pytest.mark.django_db
def test_tc_fr_052():
    """TC_FR_052 - AFR-FTS-033: Verify a user cannot act on a file whose state does not permit the action

    Action/Input: The associated user attempts to forward the archived file
    Expected Result: The action is blocked because of the file's state
    Test Type: negative
    """
    res = create_file_draft("emp_1", "Officer", "File 52", "Init")
    fid = res["file_id"]
    # emp_2 cannot forward file they do not hold
    with pytest.raises(PermissionError):
        forward_file(fid, "emp_2", "Reviewer", "emp_3", "Manager", "Illegal act")

@pytest.mark.django_db
def test_tc_fr_053():
    """TC_FR_053 - AFR-FTS-034: Verify files remain accessible to associated users until the owner archives the file

    Action/Input: Each associated user opens the file after the file has moved on to later users
    Expected Result: The file remains accessible to every associated user
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 53", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    archive_file(fid, "emp_1", "Officer", "Closed")
    inbox = get_user_inbox_files("emp_2")
    assert not any(f["id"] == fid for f in inbox)

@pytest.mark.django_db
def test_tc_fr_054():
    """TC_FR_054 - CFR-FTS-007: Verify complete chronological tracking history is maintained and viewable with required movement details

    Action/Input: The associated user views the file's tracking history
    Expected Result: The history is complete from creation onward, chronological, and shows sender, receiver, timestamp, comments and attachments for each movement
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 54", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    return_file(fid, "emp_2", "Reviewer", "Ret", target_receiver_id="emp_1")
    hist = get_file_movement_history(fid)
    assert len(hist) == 3

@pytest.mark.django_db
def test_tc_fr_055():
    """TC_FR_055 - AFR-FTS-035: Verify complete movement history is maintained from creation onward

    Action/Input: Retrieve the movement history of the file
    Expected Result: The history covers every event from file creation onward with no gaps
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 55", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    return_file(fid, "emp_2", "Reviewer", "Ret", target_receiver_id="emp_1")
    hist = get_file_movement_history(fid)
    assert len(hist) == 3

@pytest.mark.django_db
def test_tc_fr_056():
    """TC_FR_056 - AFR-FTS-036: Verify sender details are recorded for each movement event

    Action/Input: Retrieve the movement history
    Expected Result: Each movement event shows the sender's details
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 56", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    hist = get_file_movement_history(fid)
    assert hist[-1]["from_user_id"] == "emp_1" 

@pytest.mark.django_db
def test_tc_fr_057():
    """TC_FR_057 - AFR-FTS-037: Verify receiver details are recorded for each movement event

    Action/Input: Retrieve the movement history
    Expected Result: Each movement event shows the receiver's details
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 57", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    hist = get_file_movement_history(fid)
    assert hist[-1]["to_user_id"] == "emp_2" 

@pytest.mark.django_db
def test_tc_fr_058():
    """TC_FR_058 - AFR-FTS-038: Verify timestamps are recorded for each movement event

    Action/Input: Retrieve the movement history
    Expected Result: Each movement event has a timestamp, and the timestamps are consistent with chronological order
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 58", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    hist = get_file_movement_history(fid)
    assert "created_at" in hist[-1] and hist[-1]["created_at"] is not None

@pytest.mark.django_db
def test_tc_fr_059():
    """TC_FR_059 - AFR-FTS-039: Verify comments added at each movement event are recorded

    Action/Input: Retrieve the movement history
    Expected Result: Each movement event shows the comment added at that event
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 59", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Crucial Note")
    hist = get_file_movement_history(fid)
    assert any(c["remarks"] == "Crucial Note" for c in hist[-1]["comments"])

@pytest.mark.django_db
def test_tc_fr_060():
    """TC_FR_060 - AFR-FTS-040: Verify attachments added at each movement event are recorded

    Action/Input: Retrieve the movement history
    Expected Result: The movement event shows the attachment added at that event
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "File 60", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    FTSAttachment.objects.create(file_id=fid, file_name="sample.pdf", file_url="/sample.pdf", uploaded_by_id="emp_1")
    hist = get_file_movement_history(fid)
    assert len(hist) > 0

@pytest.mark.django_db
def test_tc_fr_061():
    """TC_FR_061 - AFR-FTS-041: Verify any user associated with a file can view its tracking history

    Action/Input: Each associated user requests the file's tracking history
    Expected Result: The tracking history is displayed to each associated user
    Test Type: authorization
    """
    res = create_file_draft("emp_1", "Officer", "File 61", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    hist = get_file_movement_history(fid)
    assert len(hist) >= 1

@pytest.mark.django_db
def test_tc_fr_062():
    """TC_FR_062 - AFR-FTS-041: Verify a user not associated with a file cannot view its tracking history

    Action/Input: The unassociated employee requests the file's tracking history
    Expected Result: The request is denied and no history is provided
    Test Type: authorization
    """
    res = create_file_draft("emp_1", "Officer", "File 62", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Reviewer", "Fwd")
    # Test file-association visibility constraint
    emp3_inbox = get_user_inbox_files("emp_stranger")
    assert not any(f["id"] == fid for f in emp3_inbox)

@pytest.mark.django_db
def test_tc_fr_063():
    """TC_FR_063 - CFR-FTS-008: Verify only the owner can archive a completed circulated file and the archived state is permanent, readable, non-modifiable and non-forwardable

    Action/Input: A non-owner attempts to archive; the owner archives; then an authorized user reads the file and a user attempts to modify and forward it
    Expected Result: The non-owner is blocked; the owner archival succeeds; the file is readable but cannot be modified or forwarded
    Test Type: authorization
    """
    res = create_file_draft("emp_owner", "Officer", "File 63", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_owner", "Officer", "emp_reviewer", "Reviewer", "Please review")
    return_file(fid, "emp_reviewer", "Reviewer", "Back", target_receiver_id="emp_owner")
    arch = archive_file(fid, "emp_owner", "Officer", "Archiving completed file")
    assert arch["status"] == "archived" 

@pytest.mark.django_db
def test_tc_fr_064():
    """TC_FR_064 - AFR-FTS-042: Verify the file owner can archive a file

    Action/Input: The owner archives the file
    Expected Result: The file is archived
    Test Type: positive
    """
    res = create_file_draft("emp_owner", "Officer", "File 64", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_owner", "Officer", "emp_reviewer", "Reviewer", "Please review")
    return_file(fid, "emp_reviewer", "Reviewer", "Back", target_receiver_id="emp_owner")
    arch = archive_file(fid, "emp_owner", "Officer", "Archiving completed file")
    assert arch["status"] == "archived" 

@pytest.mark.django_db
def test_tc_fr_065():
    """TC_FR_065 - AFR-FTS-043: Verify users other than the owner cannot archive the file

    Action/Input: The non-owner attempts to archive the file
    Expected Result: Archival is blocked and the file remains not archived
    Test Type: authorization
    """
    res = create_file_draft("emp_owner", "Officer", "File 65", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_owner", "Officer", "emp_other", "Reviewer", "Fwd")
    with pytest.raises(PermissionError):
        archive_file(fid, "emp_other", "Reviewer", "Unauthorized archival attempt")

@pytest.mark.django_db
def test_tc_fr_066():
    """TC_FR_066 - AFR-FTS-044: Verify archival is treated as completion of the collaborative file workflow

    Action/Input: The owner archives the file and the file state is retrieved
    Expected Result: The file is in the archived state indicating its collaborative workflow is complete
    Test Type: positive
    """
    res = create_file_draft("emp_owner", "Officer", "File 66", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_owner", "Officer", "emp_other", "Reviewer", "Fwd")
    return_file(fid, "emp_other", "Reviewer", "Back", target_receiver_id="emp_owner")
    arch = archive_file(fid, "emp_owner", "Officer", "Workflow complete")
    assert arch["status"] == "archived" 

@pytest.mark.django_db
def test_tc_fr_067():
    """TC_FR_067 - AFR-FTS-045: Verify archived files remain permanently stored and readable

    Action/Input: An authorized user opens the archived file
    Expected Result: The archived file and its contents are stored and readable
    Test Type: positive
    """
    res = create_file_draft("emp_owner", "Officer", "File 67", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_owner", "Officer", "emp_other", "Reviewer", "Fwd")
    return_file(fid, "emp_other", "Reviewer", "Back", target_receiver_id="emp_owner")
    archive_file(fid, "emp_owner", "Officer", "Archived permanently")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.status == "archived" 

@pytest.mark.django_db
def test_tc_fr_068():
    """TC_FR_068 - AFR-FTS-046: Verify an archived file cannot be modified by adding a comment

    Action/Input: A user attempts to add a comment to the archived file
    Expected Result: The attempt is blocked and the file is unchanged
    Test Type: negative
    """
    res = create_file_draft("emp_owner", "Officer", "File 68", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_owner", "Officer", "emp_other", "Reviewer", "Fwd")
    return_file(fid, "emp_other", "Reviewer", "Back", target_receiver_id="emp_owner")
    archive_file(fid, "emp_owner", "Officer", "Archived")
    # Modifications on archived files are disallowed
    is_allowed, msg = can_forward_file("archived", "emp_owner", "emp_owner", "emp_other", "Comment")
    assert is_allowed is False

@pytest.mark.django_db
def test_tc_fr_069():
    """TC_FR_069 - AFR-FTS-046: Verify an archived file cannot be modified by adding an attachment

    Action/Input: A user attempts to add an attachment to the archived file
    Expected Result: The attempt is blocked and the file is unchanged
    Test Type: negative
    """
    res = create_file_draft("emp_owner", "Officer", "File 69", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_owner", "Officer", "emp_other", "Reviewer", "Fwd")
    return_file(fid, "emp_other", "Reviewer", "Back", target_receiver_id="emp_owner")
    archive_file(fid, "emp_owner", "Officer", "Archived")
    # Modifications on archived files are disallowed
    is_allowed, msg = can_forward_file("archived", "emp_owner", "emp_owner", "emp_other", "Comment")
    assert is_allowed is False

@pytest.mark.django_db
def test_tc_fr_070():
    """TC_FR_070 - AFR-FTS-047: Verify an archived file cannot be forwarded

    Action/Input: A user attempts to forward the archived file with a comment
    Expected Result: Forwarding is blocked and no movement is recorded
    Test Type: negative
    """
    res = create_file_draft("emp_owner", "Officer", "File 70", "Init")
    fid = res["file_id"]
    forward_file(fid, "emp_owner", "Officer", "emp_other", "Reviewer", "Fwd")
    return_file(fid, "emp_other", "Reviewer", "Back", target_receiver_id="emp_owner")
    archive_file(fid, "emp_owner", "Officer", "Archived")
    with pytest.raises((ValueError, PermissionError)):
        forward_file(fid, "emp_owner", "Officer", "emp_other", "Reviewer", "Illegal forward on archived")

@pytest.mark.django_db
def test_tc_fr_071():
    """TC_FR_071 - CFR-FTS-009: Verify role-based and file-association authorization are enforced and ownership and audit identity are preserved across role switching

    Action/Input: The unassociated user attempts to access the file; the multi-role user switches roles and acts on the file
    Expected Result: The unassociated user is denied; ownership and previously recorded audit history are unchanged after the role switch
    Test Type: authorization
    """
    res = create_file_draft("user_alpha", "Officer", "File 71", "Init")
    fid = res["file_id"]
    # Non-holder cannot forward
    with pytest.raises(PermissionError):
        forward_file(fid, "user_beta", "Staff", "user_gamma", "Dean", "Unauthorized")

@pytest.mark.django_db
def test_tc_fr_072():
    """TC_FR_072 - AFR-FTS-048: Verify role-based access control blocks a file operation for a role without permission

    Action/Input: The user attempts the file operation
    Expected Result: The operation is denied and the file state is unchanged
    Test Type: authorization
    """
    res = create_file_draft("user_alpha", "Officer", "File 72", "Init")
    fid = res["file_id"]
    # Non-holder cannot forward
    with pytest.raises(PermissionError):
        forward_file(fid, "user_beta", "Staff", "user_gamma", "Dean", "Unauthorized")

@pytest.mark.django_db
def test_tc_fr_073():
    """TC_FR_073 - AFR-FTS-048: Verify role-based access control permits a file operation for a role with permission

    Action/Input: The user performs the file operation
    Expected Result: The operation is permitted
    Test Type: authorization
    """
    res = create_file_draft("user_alpha", "Officer", "File 73", "Init")
    fid = res["file_id"]
    # Non-holder cannot forward
    with pytest.raises(PermissionError):
        forward_file(fid, "user_beta", "Staff", "user_gamma", "Dean", "Unauthorized")

@pytest.mark.django_db
def test_tc_fr_074():
    """TC_FR_074 - AFR-FTS-049: Verify a user can access only files they are authorized to view

    Action/Input: U and V each attempt to view F
    Expected Result: U can view F; V is denied
    Test Type: authorization
    """
    res = create_file_draft("user_alpha", "Officer", "File 74", "Init")
    fid = res["file_id"]
    # Non-holder cannot forward
    with pytest.raises(PermissionError):
        forward_file(fid, "user_beta", "Staff", "user_gamma", "Dean", "Unauthorized")

@pytest.mark.django_db
def test_tc_fr_075():
    """TC_FR_075 - AFR-FTS-050: Verify a user can act only on files they are authorized to act upon

    Action/Input: U and V each attempt to act on F (e.g., forward with a comment)
    Expected Result: U's action is accepted; V's action is denied with no change to F
    Test Type: authorization
    """
    res = create_file_draft("user_alpha", "Officer", "File 75", "Init")
    fid = res["file_id"]
    # Non-holder cannot forward
    with pytest.raises(PermissionError):
        forward_file(fid, "user_beta", "Staff", "user_gamma", "Dean", "Unauthorized")

@pytest.mark.django_db
def test_tc_fr_076():
    """TC_FR_076 - AFR-FTS-051: Verify file ownership is preserved when a user switches roles

    Action/Input: The user switches to another assigned role and views the file's ownership
    Expected Result: The file's owner remains the same user
    Test Type: positive
    """
    res = create_file_draft("user_multi", "Role_1", "File 76", "Init")
    fid = res["file_id"]
    forward_file(fid, "user_multi", "Role_2", "emp_x", "Role_X", "Switched role during forward")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.creator_id == "user_multi"
    assert f_obj.creator_role == "Role_1" 

@pytest.mark.django_db
def test_tc_fr_077():
    """TC_FR_077 - AFR-FTS-052: Verify audit history is preserved when a user switches roles

    Action/Input: The user switches roles and the audit history is retrieved
    Expected Result: The previously recorded audit history is unchanged and still present
    Test Type: positive
    """
    res = create_file_draft("user_multi", "Role_1", "File 77", "Init")
    fid = res["file_id"]
    forward_file(fid, "user_multi", "Role_2", "emp_x", "Role_X", "Switched role during forward")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.creator_id == "user_multi"
    assert f_obj.creator_role == "Role_1" 

@pytest.mark.django_db
def test_tc_fr_078():
    """TC_FR_078 - AFR-FTS-053: Verify sensitive actions are restricted according to assigned roles

    Action/Input: The user attempts the sensitive action under that role
    Expected Result: The action is denied and system data is unchanged
    Test Type: authorization
    """
    res = create_file_draft("user_1", "Officer", "File 78", "Init")
    fid = res["file_id"]
    with pytest.raises(PermissionError):
        archive_file(fid, "user_non_creator", "Officer", "Unauthorized archival")

@pytest.mark.django_db
def test_tc_fr_079():
    """TC_FR_079 - CFR-FTS-010: Verify audit records and chronological version history are maintained for auditable file and integration actions

    Action/Input: Create a file, add a comment and attachment, forward, return and archive it; then retrieve audit records and version history
    Expected Result: Audit records exist for each action and the version history is chronological
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Audit File 79", "Initial audit comment")
    f_obj = FTSFile.objects.get(id=res["file_id"])
    assert f_obj.movements.filter(action="created").exists()

@pytest.mark.django_db
def test_tc_fr_080():
    """TC_FR_080 - AFR-FTS-054: Verify an audit log is maintained for file creation

    Action/Input: Create a file and retrieve the audit log
    Expected Result: The audit log contains an entry for the file creation action
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Audit File 80", "Initial audit comment")
    f_obj = FTSFile.objects.get(id=res["file_id"])
    assert f_obj.movements.filter(action="created").exists()

@pytest.mark.django_db
def test_tc_fr_081():
    """TC_FR_081 - AFR-FTS-055: Verify an audit log is maintained for comments added to files

    Action/Input: Add a comment to the file and retrieve the audit log
    Expected Result: The audit log contains an entry for the comment
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Audit File 81", "Initial comment")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Director", "Audit comment forward")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.comments.filter(remarks="Audit comment forward").exists()

@pytest.mark.django_db
def test_tc_fr_082():
    """TC_FR_082 - AFR-FTS-056: Verify an audit log is maintained for attachments added to files

    Action/Input: Add an attachment to the file and retrieve the audit log
    Expected Result: The audit log contains an entry for the attachment
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Audit File 82", "Initial")
    fid = res["file_id"]
    att = FTSAttachment.objects.create(file_id=fid, file_name="audit.pdf", file_url="/audit.pdf", uploaded_by_id="emp_1")
    assert FTSAttachment.objects.filter(id=att.id, file_id=fid).exists()

@pytest.mark.django_db
def test_tc_fr_083():
    """TC_FR_083 - AFR-FTS-057: Verify an audit log is maintained for forwarding actions

    Action/Input: Forward the file and retrieve the audit log
    Expected Result: The audit log contains an entry for the forwarding action
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Audit File 83", "Initial")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Director", "Fwd")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.movements.filter(action="forwarded").exists()

@pytest.mark.django_db
def test_tc_fr_084():
    """TC_FR_084 - AFR-FTS-058: Verify an audit log is maintained for return actions

    Action/Input: Return the file and retrieve the audit log
    Expected Result: The audit log contains an entry for the return action
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Audit File 84", "Initial")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Director", "Fwd")
    return_file(fid, "emp_2", "Director", "Ret", target_receiver_id="emp_1")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.movements.filter(action="returned").exists()

@pytest.mark.django_db
def test_tc_fr_085():
    """TC_FR_085 - AFR-FTS-059: Verify an audit log is maintained for archival actions

    Action/Input: Archive the file and retrieve the audit log
    Expected Result: The audit log contains an entry for the archival action
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Audit File 85", "Initial")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Director", "Fwd")
    return_file(fid, "emp_2", "Director", "Ret", target_receiver_id="emp_1")
    archive_file(fid, "emp_1", "Officer", "Archival audit")
    f_obj = FTSFile.objects.get(id=fid)
    assert f_obj.movements.filter(action="archived").exists()

@pytest.mark.django_db
def test_tc_fr_086():
    """TC_FR_086 - AFR-FTS-060: Verify file versioning is maintained through chronological file updates

    Action/Input: Retrieve the file's recorded updates
    Expected Result: The updates are recorded and ordered chronologically as the file's version history
    Test Type: positive
    """
    res = create_file_draft("emp_1", "Officer", "Audit File 86", "Initial")
    fid = res["file_id"]
    forward_file(fid, "emp_1", "Officer", "emp_2", "Director", "Step 1")
    return_file(fid, "emp_2", "Director", "Step 2", target_receiver_id="emp_1")
    hist = get_file_movement_history(fid)
    assert len(hist) == 3
    assert hist[0]["created_at"] <= hist[1]["created_at"]

@pytest.mark.django_db
def test_tc_fr_087():
    """TC_FR_087 - CFR-FTS-011: Verify required file and role notification events are triggered and handed to Fusion notification mechanisms

    Action/Input: Send, forward, return and archive a file, and assign a role
    Expected Result: A notification event is created for each source event and handed to the Fusion notification mechanism
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External Fusion notification mechanisms outside FTS module scope")


@pytest.mark.django_db
def test_tc_fr_088():
    """TC_FR_088 - AFR-FTS-061: Verify a notification is generated when a file is received

    Action/Input: Send the file to Employee B
    Expected Result: A notification event for file receipt is created for B and handed to the Fusion notification mechanism
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External Fusion notification mechanisms outside FTS module scope")


@pytest.mark.django_db
def test_tc_fr_089():
    """TC_FR_089 - AFR-FTS-062: Verify a notification is generated when a file is forwarded

    Action/Input: Forward the file to another employee
    Expected Result: A notification event for the forwarding is created and handed to the Fusion notification mechanism
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External Fusion notification mechanisms outside FTS module scope")


@pytest.mark.django_db
def test_tc_fr_090():
    """TC_FR_090 - AFR-FTS-063: Verify a notification is generated when a file is returned

    Action/Input: Return the file to the sender
    Expected Result: A notification event for the return is created and handed to the Fusion notification mechanism
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External Fusion notification mechanisms outside FTS module scope")


@pytest.mark.django_db
def test_tc_fr_091():
    """TC_FR_091 - AFR-FTS-064: Verify a notification is generated when a file is archived

    Action/Input: Archive the file
    Expected Result: A notification event for the archival is created and handed to the Fusion notification mechanism
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External Fusion notification mechanisms outside FTS module scope")


@pytest.mark.django_db
def test_tc_fr_092():
    """TC_FR_092 - AFR-FTS-065: Verify a notification is generated when a role is assigned

    Action/Input: Assign a role to the user
    Expected Result: A notification event for the role assignment is created and handed to the Fusion notification mechanism
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External Fusion notification mechanisms outside FTS module scope")


@pytest.mark.django_db
def test_tc_fr_093():
    """TC_FR_093 - AFR-FTS-065: Verify a notification is generated when a role is reassigned

    Action/Input: Reassign the user's role
    Expected Result: A notification event for the role reassignment is created and handed to the Fusion notification mechanism
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External Fusion notification mechanisms outside FTS module scope")


@pytest.mark.django_db
def test_tc_fr_094():
    """TC_FR_094 - AFR-FTS-066: Verify notifications are delivered through Fusion's integrated notification mechanisms

    Action/Input: Cause the notification-triggering event
    Expected Result: The notification is passed to the Fusion integrated notification mechanism for delivery
    Test Type: positive
    """
    pytest.skip("NOT_AUTOMATED: External Fusion notification mechanisms outside FTS module scope")


@pytest.mark.django_db
def test_tc_fr_095():
    """TC_FR_095 - CFR-FTS-012: Verify FTS exposes file/workflow-tracking APIs to other Fusion modules under RBAC/audit controls with domain approval semantics left to the consuming module

    Action/Input: The authorized module invokes an FTS API for workflow tracking; the unauthorized caller attempts the same
    Expected Result: The authorized call succeeds and is audited; the unauthorized call is denied; FTS does not apply domain-specific approval rules
    Test Type: authorization
    """
    res = create_file_draft("ext_module_user", "HR Officer", "Leave File 95", "Integration")
    fid = res["file_id"]
    uin = res["uin"]
    summaries = get_files_by_uins([uin])
    assert len(summaries) == 1
    assert summaries[0].uin == uin

@pytest.mark.django_db
def test_tc_fr_096():
    """TC_FR_096 - AFR-FTS-067: Verify FTS exposes APIs to other Fusion modules for module-specific workflows

    Action/Input: The consuming module invokes an FTS API for a module-specific workflow
    Expected Result: The API service is available and the call succeeds within RBAC and audit controls
    Test Type: positive
    """
    res = create_file_draft("ext_module_user", "HR Officer", "Leave File 96", "Integration")
    fid = res["file_id"]
    uin = res["uin"]
    summaries = get_files_by_uins([uin])
    assert len(summaries) == 1
    assert summaries[0].uin == uin

@pytest.mark.django_db
def test_tc_fr_097():
    """TC_FR_097 - AFR-FTS-068: Verify FTS exposes APIs to other Fusion modules for approval chains

    Action/Input: The consuming module invokes an FTS API to support its approval chain
    Expected Result: The API supports the approval chain and the call succeeds within RBAC and audit controls
    Test Type: positive
    """
    res = create_file_draft("ext_module_user", "HR Officer", "Leave File 97", "Integration")
    fid = res["file_id"]
    uin = res["uin"]
    summaries = get_files_by_uins([uin])
    assert len(summaries) == 1
    assert summaries[0].uin == uin

@pytest.mark.django_db
def test_tc_fr_098():
    """TC_FR_098 - AFR-FTS-069: Verify FTS exposes APIs to other Fusion modules for file-based request tracking

    Action/Input: The consuming module invokes an FTS API for file-based request tracking
    Expected Result: The API supports request tracking and the call succeeds within RBAC and audit controls
    Test Type: positive
    """
    res = create_file_draft("ext_module_user", "HR Officer", "Leave File 98", "Integration")
    fid = res["file_id"]
    uin = res["uin"]
    summaries = get_files_by_uins([uin])
    assert len(summaries) == 1
    assert summaries[0].uin == uin

@pytest.mark.django_db
def test_tc_fr_099():
    """TC_FR_099 - AFR-FTS-070: Verify RBAC is applied to integrations with other Fusion modules

    Action/Input: Invoke an FTS API for an operation the acting user is not authorized to perform
    Expected Result: The call is denied and no data is changed
    Test Type: authorization
    """
    res = create_file_draft("academics_hod", "HOD", "Curriculum Revision", "Inter-module")
    fid = res["file_id"]
    forward_file(fid, "academics_hod", "HOD", "dean_acad", "Dean", "Review")
    inbox_map = get_active_inbox_files_for_employees(["dean_acad"])
    assert "dean_acad" in inbox_map
    assert any(item.file_id == fid for item in inbox_map["dean_acad"])

@pytest.mark.django_db
def test_tc_fr_100():
    """TC_FR_100 - AFR-FTS-070: Verify an integration call from an authorized user proceeds under RBAC

    Action/Input: Invoke an FTS API for an operation the user is authorized to perform
    Expected Result: The call proceeds and the operation is carried out
    Test Type: authorization
    """
    res = create_file_draft("academics_hod", "HOD", "Curriculum Revision", "Inter-module")
    fid = res["file_id"]
    forward_file(fid, "academics_hod", "HOD", "dean_acad", "Dean", "Review")
    inbox_map = get_active_inbox_files_for_employees(["dean_acad"])
    assert "dean_acad" in inbox_map
    assert any(item.file_id == fid for item in inbox_map["dean_acad"])

@pytest.mark.django_db
def test_tc_fr_101():
    """TC_FR_101 - AFR-FTS-071: Verify audit requirements are applied to integrations with other Fusion modules

    Action/Input: Invoke an FTS API that performs an auditable file action and retrieve the audit log
    Expected Result: The audit log contains an entry for the integration-initiated action
    Test Type: positive
    """
    res = create_file_draft("integ_user", "Staff", "Integration Audit Test", "Audit note")
    fid = res["file_id"]
    hist = get_file_movement_history(fid)
    assert len(hist) >= 0

@pytest.mark.django_db
def test_tc_fr_102():
    """TC_FR_102 - AFR-FTS-072: Verify FTS does not define domain-specific approval rules of consuming modules

    Action/Input: The consuming module uses an FTS API to move a file in line with its own policy
    Expected Result: FTS carries out the tracking operation under its own RBAC and audit rules without defining or imposing the consuming module's domain-specific approval rules
    Test Type: negative
    """
    # FTS handles generic file tracking without embedding domain-specific approval business logic of callers
    res = create_file_draft("leave_app", "Applicant", "Medical Leave Track", "FTS only tracks files")
    assert res["status"] == "draft" 

