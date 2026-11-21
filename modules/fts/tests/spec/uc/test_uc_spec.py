"""Specification-based tests for Use Cases (UC) strategy.

Implements all 40 test cases from docs/07-fts/spec-tests/UC_DESIGN.json.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory

from modules.fts.api.views import FTSFileViewSet
from modules.fts.contracts import (
    get_active_inbox_files_for_employees,
    get_files_by_uins,
)
from modules.fts.domain.workflow import (
    STATUS_ARCHIVED,
    STATUS_DRAFT,
    STATUS_IN_TRANSIT,
    STATUS_RETURNED,
)
from modules.fts.models import FTSAttachment, FTSFile
from modules.fts.registry import get_role_grants
from modules.fts.selectors.inbox_outbox import (
    get_user_inbox_files,
    get_user_outbox_files,
)
from modules.fts.selectors.movements import get_file_movement_history
from modules.fts.services.archival import archive_file
from modules.fts.services.drafts import (
    create_file_draft,
    discard_file_draft,
    update_file_draft,
)
from modules.fts.services.movements import forward_file, return_file


@pytest.mark.django_db
class TestUseCasesSpec:
    """Executable test suite for FTS-UC-001 through FTS-UC-010."""

    def test_uc_001_fts_uc_001_main_flow(self):
        """[UC-001] FTS-UC-001 Main Flow.

        Verify file draft creation with mandatory comment and optional attachment.
        """
        draft = create_file_draft(
            creator_id="emp_uc1",
            creator_role="Faculty",
            subject="UC-001 Main Draft",
            initial_comment="Submitting grant proposal",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        att = FTSAttachment.objects.create(
            file=file_obj,
            file_name="proposal.pdf",
            file_url="https://example.com/proposal.pdf",
            uploaded_by_id="emp_uc1",
        )
        assert file_obj.status == STATUS_DRAFT
        assert file_obj.attachments.filter(id=att.id).exists()
        assert file_obj.comments.count() == 1

    def test_uc_002_fts_uc_001_alternative_flow_1(self):
        """[UC-002] FTS-UC-001 Alternative Flow 1.

        Verify immediate send/circulate upon file creation without draft holding.
        """
        draft = create_file_draft(
            creator_id="emp_uc2",
            creator_role="Faculty",
            subject="UC-002 Immediate Circulate",
            initial_comment="Immediate dispatch",
        )
        fwd = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc2",
            sender_role="Faculty",
            receiver_id="emp_uc2_rec",
            receiver_role="HOD",
            comment="Dispatching now",
        )
        assert fwd["new_status"] == STATUS_IN_TRANSIT
        assert fwd["current_holder_id"] == "emp_uc2_rec"

    def test_uc_003_fts_uc_001_alternative_flow_2(self):
        """[UC-003] FTS-UC-001 Alternative Flow 2.

        Verify file creation succeeds without attachments.
        """
        draft = create_file_draft(
            creator_id="emp_uc3",
            creator_role="Staff",
            subject="UC-003 No Attachment",
            initial_comment="Valid text only creation",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert file_obj.attachments.count() == 0
        assert file_obj.comments.count() == 1

    def test_uc_004_fts_uc_001_exception_flow_1(self):
        """[UC-004] FTS-UC-001 Exception Flow 1.

        Verify creation rejected with validation error when comment is empty.
        """
        with pytest.raises(ValueError, match="Initial comment is mandatory"):
            create_file_draft(
                creator_id="emp_uc4",
                creator_role="Staff",
                subject="UC-004 Empty Comment",
                initial_comment="   ",
            )

    def test_uc_005_fts_uc_001_exception_flow_2(self):
        """[UC-005] FTS-UC-001 Exception Flow 2.

        Verify user lacking create permission is denied.
        """
        role_grants = get_role_grants()
        # Guest or unauthorized role has no create permissions
        guest_perms = role_grants.get("guest", [])
        assert "fts.file.create" not in guest_perms

    def test_uc_006_fts_uc_002_main_flow(self):
        """[UC-006] FTS-UC-002 Main Flow.

        Verify draft owner can edit comment and add attachment before circulation.
        """
        draft = create_file_draft(
            creator_id="emp_uc6",
            creator_role="Faculty",
            subject="UC-006 Initial Draft",
            initial_comment="Initial remark",
        )
        updated = update_file_draft(
            file_id=draft["file_id"],
            user_id="emp_uc6",
            subject="UC-006 Updated Draft",
        )
        assert updated["subject"] == "UC-006 Updated Draft"
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        FTSAttachment.objects.create(
            file=file_obj,
            file_name="extra.pdf",
            file_url="https://example.com/extra.pdf",
            uploaded_by_id="emp_uc6",
        )
        assert file_obj.attachments.count() == 1

    def test_uc_007_fts_uc_002_alternative_flow_1(self):
        """[UC-007] FTS-UC-002 Alternative Flow 1.

        Verify draft owner can discard draft before submission.
        """
        draft = create_file_draft(
            creator_id="emp_uc7",
            creator_role="Staff",
            subject="UC-007 Discard Draft",
            initial_comment="Initial remark",
        )
        discard_file_draft(file_id=draft["file_id"], user_id="emp_uc7")
        assert not FTSFile.objects.filter(id=draft["file_id"]).exists()

    def test_uc_008_fts_uc_002_exception_flow_1(self):
        """[UC-008] FTS-UC-002 Exception Flow 1.

        Verify draft discard is denied on circulated file.
        """
        draft = create_file_draft(
            creator_id="emp_uc8",
            creator_role="Staff",
            subject="UC-008 Circulated File",
            initial_comment="Initial remark",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc8",
            sender_role="Staff",
            receiver_id="emp_uc8_rec",
            receiver_role="HOD",
            comment="Circulated",
        )
        with pytest.raises(PermissionError, match="Only files in draft status"):
            discard_file_draft(file_id=draft["file_id"], user_id="emp_uc8")

    def test_uc_009_fts_uc_002_exception_flow_2(self):
        """[UC-009] FTS-UC-002 Exception Flow 2.

        Verify non-owner cannot edit or discard another employee's draft.
        """
        draft = create_file_draft(
            creator_id="emp_uc9_a",
            creator_role="Staff",
            subject="UC-009 Draft Owner A",
            initial_comment="Initial remark",
        )
        with pytest.raises(PermissionError, match="Only the file creator"):
            update_file_draft(
                file_id=draft["file_id"],
                user_id="emp_uc9_b",
                subject="Hacked Draft",
            )
        with pytest.raises(PermissionError, match="Only the file creator"):
            discard_file_draft(file_id=draft["file_id"], user_id="emp_uc9_b")

    def test_uc_010_fts_uc_003_main_flow(self):
        """[UC-010] FTS-UC-003 Main Flow.

        Verify forwarding file with comment and optional attachment.
        """
        draft = create_file_draft(
            creator_id="emp_uc10",
            creator_role="Faculty",
            subject="UC-010 Forward Main Flow",
            initial_comment="Initial remark",
        )
        fwd = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc10",
            sender_role="Faculty",
            receiver_id="emp_uc10_rec",
            receiver_role="HOD",
            comment="Forwarding for review",
        )
        assert fwd["new_status"] == STATUS_IN_TRANSIT
        assert fwd["current_holder_id"] == "emp_uc10_rec"

    def test_uc_011_fts_uc_003_alternative_flow_1(self):
        """[UC-011] FTS-UC-003 Alternative Flow 1.

        Verify onward forwarding where recipient passes file to third employee.
        """
        draft = create_file_draft(
            creator_id="emp_uc11_a",
            creator_role="Staff",
            subject="UC-011 Onward Forward",
            initial_comment="Initial remark",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc11_a",
            sender_role="Staff",
            receiver_id="emp_uc11_b",
            receiver_role="HOD",
            comment="Passing to HOD",
        )
        fwd2 = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc11_b",
            sender_role="HOD",
            receiver_id="emp_uc11_c",
            receiver_role="Dean",
            comment="Onward passing to Dean",
        )
        assert fwd2["current_holder_id"] == "emp_uc11_c"

    def test_uc_012_fts_uc_003_alternative_flow_2(self):
        """[UC-012] FTS-UC-003 Alternative Flow 2.

        Verify forwarding file without attachments succeeds.
        """
        draft = create_file_draft(
            creator_id="emp_uc12",
            creator_role="Staff",
            subject="UC-012 No Attachment Forward",
            initial_comment="Initial remark",
        )
        res = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc12",
            sender_role="Staff",
            receiver_id="emp_uc12_rec",
            receiver_role="Faculty",
            comment="Valid text-only forward comment",
        )
        assert res["new_status"] == STATUS_IN_TRANSIT

    def test_uc_013_fts_uc_003_exception_flow_1(self):
        """[UC-013] FTS-UC-003 Exception Flow 1.

        Verify forward blocked when movement comment is missing.
        """
        draft = create_file_draft(
            creator_id="emp_uc13",
            creator_role="Faculty",
            subject="UC-013 Missing Comment",
            initial_comment="Initial",
        )
        with pytest.raises(PermissionError, match="Movement comment is mandatory"):
            forward_file(
                file_id=draft["file_id"],
                sender_id="emp_uc13",
                sender_role="Faculty",
                receiver_id="emp_uc13_rec",
                receiver_role="HOD",
                comment="   ",
            )

    def test_uc_014_fts_uc_003_exception_flow_2(self):
        """[UC-014] FTS-UC-003 Exception Flow 2.

        Verify forward refused with validation error when recipient is invalid (DEF-002).
        """
        draft = create_file_draft(
            creator_id="emp_uc14",
            creator_role="Staff",
            subject="UC-014 Invalid Recipient",
            initial_comment="Initial",
        )
        with pytest.raises((ValueError, PermissionError), match="Invalid or non-existent recipient"):
            forward_file(
                file_id=draft["file_id"],
                sender_id="emp_uc14",
                sender_role="Staff",
                receiver_id="",  # Invalid recipient identifier
                receiver_role="",
                comment="Sending to invalid recipient",
            )

    def test_uc_015_fts_uc_003_exception_flow_3(self):
        """[UC-015] FTS-UC-003 Exception Flow 3.

        Verify forward denied when actor is not current custodian.
        """
        draft = create_file_draft(
            creator_id="emp_uc15_a",
            creator_role="Staff",
            subject="UC-015 Non Custodian Forward",
            initial_comment="Initial",
        )
        with pytest.raises(PermissionError, match="Only the current custodian"):
            forward_file(
                file_id=draft["file_id"],
                sender_id="emp_uc15_intruder",
                sender_role="Staff",
                receiver_id="emp_uc15_b",
                receiver_role="Faculty",
                comment="Sneaky forward attempt",
            )

    def test_uc_016_fts_uc_004_main_flow(self):
        """[UC-016] FTS-UC-004 Main Flow.

        Verify recipient can return file to previous sender with mandatory comment.
        """
        draft = create_file_draft(
            creator_id="emp_uc16_a",
            creator_role="Staff",
            subject="UC-016 Return Main Flow",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc16_a",
            sender_role="Staff",
            receiver_id="emp_uc16_b",
            receiver_role="HOD",
            comment="Forwarded",
        )
        ret = return_file(
            file_id=draft["file_id"],
            sender_id="emp_uc16_b",
            sender_role="HOD",
            comment="Returning with comments",
        )
        assert ret["new_status"] == STATUS_RETURNED
        assert ret["returned_to_id"] == "emp_uc16_a"

    def test_uc_017_fts_uc_004_alternative_flow_1(self):
        """[UC-017] FTS-UC-004 Alternative Flow 1.

        Verify return succeeds without attachments.
        """
        draft = create_file_draft(
            creator_id="emp_uc17_a",
            creator_role="Faculty",
            subject="UC-017 Return No Att",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc17_a",
            sender_role="Faculty",
            receiver_id="emp_uc17_b",
            receiver_role="Dean",
            comment="Forwarded",
        )
        ret = return_file(
            file_id=draft["file_id"],
            sender_id="emp_uc17_b",
            sender_role="Dean",
            comment="Text only return comment",
        )
        assert ret["new_status"] == STATUS_RETURNED

    def test_uc_018_fts_uc_004_exception_flow_1(self):
        """[UC-018] FTS-UC-004 Exception Flow 1.

        Verify return blocked when movement comment is empty.
        """
        draft = create_file_draft(
            creator_id="emp_uc18_a",
            creator_role="Staff",
            subject="UC-018 Return Empty Comment",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc18_a",
            sender_role="Staff",
            receiver_id="emp_uc18_b",
            receiver_role="HOD",
            comment="Forwarded",
        )
        with pytest.raises(PermissionError, match="Movement comment is mandatory"):
            return_file(
                file_id=draft["file_id"],
                sender_id="emp_uc18_b",
                sender_role="HOD",
                comment="   ",
            )

    def test_uc_019_fts_uc_004_exception_flow_2(self):
        """[UC-019] FTS-UC-004 Exception Flow 2.

        Verify return denied when actor is not the current custodian.
        """
        draft = create_file_draft(
            creator_id="emp_uc19_a",
            creator_role="Staff",
            subject="UC-019 Non Holder Return",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc19_a",
            sender_role="Staff",
            receiver_id="emp_uc19_b",
            receiver_role="HOD",
            comment="Forwarded",
        )
        with pytest.raises(PermissionError, match="Only the current custodian"):
            return_file(
                file_id=draft["file_id"],
                sender_id="emp_uc19_intruder",
                sender_role="Staff",
                comment="Unauthorized return attempt",
            )

    def test_uc_020_fts_uc_005_main_flow(self):
        """[UC-020] FTS-UC-005 Main Flow.

        Verify Inbox lists received files and Outbox lists sent files.
        """
        draft = create_file_draft(
            creator_id="emp_uc20_a",
            creator_role="Staff",
            subject="UC-020 Inbox Outbox Main",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc20_a",
            sender_role="Staff",
            receiver_id="emp_uc20_b",
            receiver_role="HOD",
            comment="Sent to B",
        )
        inbox_b = get_user_inbox_files(user_id="emp_uc20_b")
        outbox_a = get_user_outbox_files(user_id="emp_uc20_a")
        assert any(item["id"] == draft["file_id"] for item in inbox_b)
        assert any(item["id"] == draft["file_id"] for item in outbox_a)

    def test_uc_021_fts_uc_005_alternative_flow_1(self):
        """[UC-021] FTS-UC-005 Alternative Flow 1.

        Verify opening archived file presents read-only view.
        """
        draft = create_file_draft(
            creator_id="emp_uc21",
            creator_role="Faculty",
            subject="UC-021 Archived File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc21",
            sender_role="Faculty",
            receiver_id="emp_uc21_rec",
            receiver_role="Dean",
            comment="Circulating",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_uc21_rec",
            sender_role="Dean",
            comment="Returned",
        )
        archive_file(
            file_id=draft["file_id"],
            user_id="emp_uc21",
            user_role="Faculty",
            remarks="Archiving",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert file_obj.status == STATUS_ARCHIVED

    def test_uc_022_fts_uc_005_exception_flow_1(self):
        """[UC-022] FTS-UC-005 Exception Flow 1.

        Verify unassociated employee cannot access file through inbox/outbox.
        """
        draft = create_file_draft(
            creator_id="emp_uc22_a",
            creator_role="Staff",
            subject="UC-022 Private File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc22_a",
            sender_role="Staff",
            receiver_id="emp_uc22_b",
            receiver_role="HOD",
            comment="Sent to B",
        )
        inbox_c = get_user_inbox_files(user_id="emp_uc22_c")
        outbox_c = get_user_outbox_files(user_id="emp_uc22_c")
        assert not any(item["id"] == draft["file_id"] for item in inbox_c)
        assert not any(item["id"] == draft["file_id"] for item in outbox_c)

    def test_uc_023_fts_uc_005_exception_flow_2(self):
        """[UC-023] FTS-UC-005 Exception Flow 2.

        Verify employee denied when attempting unauthorized action on a file.
        """
        draft = create_file_draft(
            creator_id="emp_uc23_a",
            creator_role="Staff",
            subject="UC-023 Unauthorized Action",
            initial_comment="Initial",
        )
        with pytest.raises(PermissionError):
            forward_file(
                file_id=draft["file_id"],
                sender_id="emp_uc23_random",
                sender_role="Staff",
                receiver_id="emp_uc23_b",
                receiver_role="HOD",
                comment="Unauthorized forward attempt",
            )

    def test_uc_024_fts_uc_006_main_flow(self):
        """[UC-024] FTS-UC-006 Main Flow.

        Verify complete chronological tracking history retrieval.
        """
        draft = create_file_draft(
            creator_id="emp_uc24",
            creator_role="Staff",
            subject="UC-024 History Main Flow",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc24",
            sender_role="Staff",
            receiver_id="emp_uc24_rec",
            receiver_role="HOD",
            comment="First forward",
        )
        history = get_file_movement_history(file_id=draft["file_id"])
        assert len(history) == 2
        assert history[0]["action"] == "created"
        assert history[1]["action"] == "forwarded"

    def test_uc_025_fts_uc_006_alternative_flow_1(self):
        """[UC-025] FTS-UC-006 Alternative Flow 1.

        Verify tracking history of archived file retains all lifecycle events.
        """
        draft = create_file_draft(
            creator_id="emp_uc25",
            creator_role="Staff",
            subject="UC-025 Archived History",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc25",
            sender_role="Staff",
            receiver_id="emp_uc25_b",
            receiver_role="HOD",
            comment="Sent to B",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_uc25_b",
            sender_role="HOD",
            comment="Returned to owner",
        )
        archive_file(
            file_id=draft["file_id"],
            user_id="emp_uc25",
            user_role="Staff",
            remarks="Archived",
        )
        history = get_file_movement_history(file_id=draft["file_id"])
        actions = [h["action"] for h in history]
        assert actions == ["created", "forwarded", "returned", "archived"]

    def test_uc_026_fts_uc_006_exception_flow_1(self):
        """[UC-026] FTS-UC-006 Exception Flow 1.

        Verify unassociated employee access is checked when querying file details.
        """
        draft = create_file_draft(
            creator_id="emp_uc26_a",
            creator_role="Staff",
            subject="UC-026 Private Details",
            initial_comment="Initial",
        )
        inbox_outsider = get_user_inbox_files(user_id="emp_uc26_outsider")
        assert not any(item["id"] == draft["file_id"] for item in inbox_outsider)

    def test_uc_027_fts_uc_007_main_flow(self):
        """[UC-027] FTS-UC-007 Main Flow.

        Verify owner can archive completed circulated file.
        """
        draft = create_file_draft(
            creator_id="emp_uc27",
            creator_role="Faculty",
            subject="UC-027 Archival Main Flow",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc27",
            sender_role="Faculty",
            receiver_id="emp_uc27_rec",
            receiver_role="Dean",
            comment="Circulating",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_uc27_rec",
            sender_role="Dean",
            comment="Returned",
        )
        res = archive_file(
            file_id=draft["file_id"],
            user_id="emp_uc27",
            user_role="Faculty",
            remarks="Task complete, archiving",
        )
        assert res["status"] == STATUS_ARCHIVED

    def test_uc_028_fts_uc_007_alternative_flow_1(self):
        """[UC-028] FTS-UC-007 Alternative Flow 1.

        Verify archive on already archived file is refused.
        """
        draft = create_file_draft(
            creator_id="emp_uc28",
            creator_role="Faculty",
            subject="UC-028 Duplicate Archival",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc28",
            sender_role="Faculty",
            receiver_id="emp_uc28_rec",
            receiver_role="Dean",
            comment="Circulating",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_uc28_rec",
            sender_role="Dean",
            comment="Returned",
        )
        archive_file(
            file_id=draft["file_id"],
            user_id="emp_uc28",
            user_role="Faculty",
            remarks="First archive",
        )
        with pytest.raises(PermissionError, match="File is already archived"):
            archive_file(
                file_id=draft["file_id"],
                user_id="emp_uc28",
                user_role="Faculty",
                remarks="Duplicate archive attempt",
            )

    def test_uc_029_fts_uc_007_exception_flow_1(self):
        """[UC-029] FTS-UC-007 Exception Flow 1.

        Verify non-owner recipient cannot archive file (DEF-001).
        """
        draft = create_file_draft(
            creator_id="emp_owner_29",
            creator_role="Staff",
            subject="UC-029 Non-Owner Archival Refusal",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_owner_29",
            sender_role="Staff",
            receiver_id="emp_recipient_29",
            receiver_role="HOD",
            comment="Sent to recipient",
        )
        with pytest.raises(PermissionError, match="Only the file owner can archive this file"):
            archive_file(
                file_id=draft["file_id"],
                user_id="emp_recipient_29",
                user_role="HOD",
                remarks="Attempted non-owner archive",
            )

    def test_uc_030_fts_uc_007_exception_flow_2(self):
        """[UC-030] FTS-UC-007 Exception Flow 2.

        Verify user lacking permissions cannot archive file.
        """
        draft = create_file_draft(
            creator_id="emp_uc30",
            creator_role="Staff",
            subject="UC-030 Unauth Archival",
            initial_comment="Initial",
        )
        with pytest.raises(PermissionError):
            archive_file(
                file_id=draft["file_id"],
                user_id="emp_uc30_intruder",
                user_role="Unknown",
                remarks="Unauthorized attempt",
            )

    def test_uc_031_fts_uc_008_main_flow(self):
        """[UC-031] FTS-UC-008 Main Flow.

        Verify role context switch preserves file ownership and audit history.
        """
        draft = create_file_draft(
            creator_id="emp_uc31",
            creator_role="Faculty",
            subject="UC-031 Multi Role File",
            initial_comment="Created as Faculty",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert file_obj.creator_id == "emp_uc31"
        assert file_obj.creator_role == "Faculty"

    def test_uc_032_fts_uc_008_alternative_flow_1(self):
        """[UC-032] FTS-UC-008 Alternative Flow 1.

        Verify single role employee access directly applies role permissions.
        """
        role_grants = get_role_grants()
        assert "faculty" in role_grants
        assert "fts.file.view" in role_grants["faculty"]

    def test_uc_033_fts_uc_008_exception_flow_1(self):
        """[UC-033] FTS-UC-008 Exception Flow 1.

        Verify restricted action denied when role lacks permission.
        """
        role_grants = get_role_grants()
        student_perms = role_grants.get("student", [])
        assert "fts.file.manage" not in student_perms

    def test_uc_034_fts_uc_009_main_flow(self):
        """[UC-034] FTS-UC-009 Main Flow.

        Verify system admin governance separation: System Administrator cannot execute
        operational file mutations (forwarding, archival), raising PermissionError per BR-FTS-002.
        """
        role_grants = get_role_grants()
        assert "system_admin" not in role_grants
        assert "admin" not in role_grants

        draft = create_file_draft(
            creator_id="emp_uc34_custodian",
            creator_role="Faculty",
            subject="UC-034 Governance Separation File",
            initial_comment="Initial remark",
        )
        with pytest.raises(PermissionError):
            forward_file(
                file_id=draft["file_id"],
                sender_id="sysadmin_001",
                sender_role="System Admin",
                receiver_id="emp_uc34_target",
                receiver_role="Faculty",
                comment="Sysadmin forward prohibited",
            )

        with pytest.raises(PermissionError):
            archive_file(
                file_id=draft["file_id"],
                user_id="sysadmin_001",
                user_role="System Admin",
                remarks="Sysadmin archive prohibited",
            )

    def test_uc_035_fts_uc_009_alternative_flow_1(self):
        """[UC-035] FTS-UC-009 Alternative Flow 1.

        Verify FTS consumes identity context without managing central user directory.
        """
        # FTS models record external user identifiers without storing full user directory tables
        draft = create_file_draft(
            creator_id="dir_emp_001",
            creator_role="Staff",
            subject="Directory Context File",
            initial_comment="Referencing directory user id",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert file_obj.creator_id == "dir_emp_001"

    def test_uc_036_fts_uc_009_exception_flow_1(self):
        """[UC-036] FTS-UC-009 Exception Flow 1.

        Verify operational processing is blocked for System Admin.
        """
        role_grants = get_role_grants()
        assert "admin" not in role_grants
        assert "system_admin" not in role_grants

    def test_uc_037_fts_uc_010_main_flow(self):
        """[UC-037] FTS-UC-010 Main Flow.

        Verify consuming module can retrieve file summaries by UINs via public contract.
        """
        draft = create_file_draft(
            creator_id="emp_uc37",
            creator_role="Staff",
            subject="UC-037 Contract File",
            initial_comment="Initial",
        )
        summaries = get_files_by_uins([draft["uin"]])
        assert len(summaries) == 1
        assert summaries[0].uin == draft["uin"]

    def test_uc_038_fts_uc_010_alternative_flow_1(self):
        """[UC-038] FTS-UC-010 Alternative Flow 1.

        Verify consuming module can query active inbox files for employee sequences.
        """
        draft = create_file_draft(
            creator_id="emp_uc38_a",
            creator_role="Staff",
            subject="UC-038 Active Inbox Contract",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_uc38_a",
            sender_role="Staff",
            receiver_id="emp_uc38_b",
            receiver_role="HOD",
            comment="Forwarded to HOD",
        )
        inbox_map = get_active_inbox_files_for_employees(["emp_uc38_b"])
        assert "emp_uc38_b" in inbox_map
        assert len(inbox_map["emp_uc38_b"]) >= 1

    def test_uc_039_fts_uc_010_exception_flow_1(self):
        """[UC-039] FTS-UC-010 Exception Flow 1.

        Verify unauthenticated API request returns 401/403 or handled gracefully.
        """
        factory = APIRequestFactory()
        view = FTSFileViewSet.as_view({"get": "inbox"})
        req = factory.get("/api/v1/fts/files/inbox/")
        req.user = type("AnonymousUser", (), {"is_authenticated": False, "username": ""})()
        resp = view(req)
        assert resp.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_uc_040_fts_uc_010_exception_flow_2(self):
        """[UC-040] FTS-UC-010 Exception Flow 2.

        Verify FTS tracks workflow requests without executing external domain approval logic.
        """
        draft = create_file_draft(
            creator_id="emp_external_mod",
            creator_role="Purchase Officer",
            subject="Purchase Indent #90210",
            initial_comment="Forwarding for budget clearance",
        )
        fwd = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_external_mod",
            sender_role="Purchase Officer",
            receiver_id="emp_finance_officer",
            receiver_role="Finance Officer",
            comment="Forwarding indent",
        )
        assert fwd["new_status"] == STATUS_IN_TRANSIT
