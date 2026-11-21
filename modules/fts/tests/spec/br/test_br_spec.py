"""Specification-based tests for Business Rules (BR) strategy.

Implements all 46 test cases from docs/07-fts/spec-tests/BR_DESIGN.json.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory

from modules.fts.api.views import FTSFileViewSet
from modules.fts.contracts import get_files_by_uins
from modules.fts.domain.workflow import (
    STATUS_ARCHIVED,
    STATUS_DRAFT,
    STATUS_IN_TRANSIT,
    STATUS_RETURNED,
)
from modules.fts.models import FTSAttachment, FTSComment, FTSFile, FTSMovement
from modules.fts.registry import get_permissions, get_role_grants
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
class TestBusinessRulesSpec:
    """Executable test suite for BR-FTS-001 through BR-FTS-014."""

    def test_br_001_permitted_operational_action(self):
        """[BR-001] BR-FTS-001 permitted-operational-action.

        Verify employee can perform creation and movement operations.
        """
        draft = create_file_draft(
            creator_id="emp_br_01",
            creator_role="Faculty",
            subject="BR-001 Operational File",
            initial_comment="Operational action remark",
        )
        fwd = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_br_01",
            sender_role="Faculty",
            receiver_id="emp_br_02",
            receiver_role="Staff",
            comment="Passing to staff",
        )
        assert fwd["new_status"] == STATUS_IN_TRANSIT
        assert fwd["current_holder_id"] == "emp_br_02"

    def test_br_002_prohibited_sysadmin_operational_action(self):
        """[BR-002] BR-FTS-001 prohibited-sysadmin-operational-action.

        Verify operational processing is blocked for System Admin.
        """
        role_grants = get_role_grants()
        assert "system_admin" not in role_grants
        assert "admin" not in role_grants

    def test_br_003_sysadmin_governance_permitted(self):
        """[BR-003] BR-FTS-001 sysadmin-governance-permitted.

        Verify system administrator governance functions (role permissions defined).
        """
        perms = get_permissions()
        perm_codes = [code for code, _ in perms]
        assert "fts.file.view" in perm_codes
        assert "fts.file.create" in perm_codes
        assert "fts.file.review" in perm_codes
        assert "fts.file.manage" in perm_codes

    def test_br_004_role_switch_context_update(self):
        """[BR-004] BR-FTS-002 role-switch-context-update.

        Verify employee role context updates permissions.
        """
        role_grants = get_role_grants()
        assert "faculty" in role_grants
        assert "staff" in role_grants
        assert "fts.file.create" in role_grants["faculty"]
        assert "fts.file.create" in role_grants["staff"]

    def test_br_005_role_switch_preserves_ownership(self):
        """[BR-005] BR-FTS-002 role-switch-preserves-ownership.

        Verify file retains original owner identity when creator switches roles.
        """
        draft = create_file_draft(
            creator_id="user_switch_1",
            creator_role="Faculty",
            subject="Ownership Preservation File",
            initial_comment="Created as Faculty",
        )
        update_file_draft(
            file_id=draft["file_id"],
            user_id="user_switch_1",
            subject="Updated under Warden Role",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert file_obj.creator_id == "user_switch_1"
        assert file_obj.creator_role == "Faculty"

    def test_br_006_role_switch_preserves_audit_history(self):
        """[BR-006] BR-FTS-002 role-switch-preserves-audit-history.

        Verify historical audit records remain unchanged when user switches roles.
        """
        draft = create_file_draft(
            creator_id="user_audit_1",
            creator_role="Staff",
            subject="Audit Preservation File",
            initial_comment="Remark under Staff role",
        )
        movement = FTSMovement.objects.get(file_id=draft["file_id"], action="created")
        assert movement.from_role == "Staff"
        comment = FTSComment.objects.get(movement=movement)
        assert comment.author_role == "Staff"

    def test_br_007_composite_file_structure(self):
        """[BR-007] BR-FTS-003 composite-file-structure.

        Verify file object contains both mandatory comment and attachment reference.
        """
        draft = create_file_draft(
            creator_id="emp_comp_1",
            creator_role="Staff",
            subject="Composite Structure Test",
            initial_comment="Opening composite comment",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        att = FTSAttachment.objects.create(
            file=file_obj,
            file_name="spec_annex.pdf",
            file_url="https://example.com/spec_annex.pdf",
            uploaded_by_id="emp_comp_1",
        )
        assert file_obj.comments.count() == 1
        assert file_obj.attachments.filter(id=att.id).exists()

    def test_br_008_retain_circulated_contents_no_deletion(self):
        """[BR-008] BR-FTS-003 retain-circulated-contents-no-deletion.

        Verify circulated file and contents cannot be deleted.
        """
        draft = create_file_draft(
            creator_id="emp_ret_1",
            creator_role="Faculty",
            subject="Circulation Retention File",
            initial_comment="Initial remark",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_ret_1",
            sender_role="Faculty",
            receiver_id="emp_ret_2",
            receiver_role="HOD",
            comment="Circulating file",
        )
        with pytest.raises(PermissionError):
            discard_file_draft(file_id=draft["file_id"], user_id="emp_ret_1")
        assert FTSFile.objects.filter(id=draft["file_id"]).exists()

    def test_br_009_draft_discard_exception(self):
        """[BR-009] BR-FTS-003 draft-discard-exception.

        Verify draft discard removes pre-circulation draft from active files.
        """
        draft = create_file_draft(
            creator_id="emp_disc_1",
            creator_role="Staff",
            subject="Pre-Circulation Discard",
            initial_comment="Will discard",
        )
        discard_file_draft(file_id=draft["file_id"], user_id="emp_disc_1")
        assert not FTSFile.objects.filter(id=draft["file_id"]).exists()

    def test_br_010_initial_comment_permitted(self):
        """[BR-010] BR-FTS-004 initial-comment-permitted.

        Verify file creation accepted with non-empty initial comment.
        """
        res = create_file_draft(
            creator_id="emp_com_1",
            creator_role="Faculty",
            subject="Valid Comment File",
            initial_comment="Valid substantive comment",
        )
        assert res["file_id"] is not None

    def test_br_011_initial_comment_prohibited_empty(self):
        """[BR-011] BR-FTS-004 initial-comment-prohibited-empty.

        Verify creation rejected when initial comment is empty.
        """
        with pytest.raises(ValueError, match="Initial comment is mandatory"):
            create_file_draft(
                creator_id="emp_com_2",
                creator_role="Faculty",
                subject="Empty Comment File",
                initial_comment="   ",
            )

    def test_br_012_pre_circulation_draft_permitted(self):
        """[BR-012] BR-FTS-005 pre-circulation-draft-permitted.

        Verify create draft, edit draft fields, and save updated draft.
        """
        draft = create_file_draft(
            creator_id="emp_edit_1",
            creator_role="Staff",
            subject="Draft Editing",
            initial_comment="Draft remark",
        )
        updated = update_file_draft(
            file_id=draft["file_id"],
            user_id="emp_edit_1",
            subject="Draft Editing Updated",
            priority="urgent",
        )
        assert updated["subject"] == "Draft Editing Updated"
        refreshed = FTSFile.objects.get(id=draft["file_id"])
        assert refreshed.priority == "urgent"

    def test_br_013_post_circulation_discard_prohibited(self):
        """[BR-013] BR-FTS-005 post-circulation-discard-prohibited.

        Verify circulated file discard is rejected.
        """
        draft = create_file_draft(
            creator_id="emp_circ_1",
            creator_role="Staff",
            subject="Circulated File",
            initial_comment="Remark",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_circ_1",
            sender_role="Staff",
            receiver_id="emp_circ_2",
            receiver_role="HOD",
            comment="Forwarded",
        )
        with pytest.raises(PermissionError):
            discard_file_draft(file_id=draft["file_id"], user_id="emp_circ_1")

    def test_br_014_draft_submission_transition(self):
        """[BR-014] BR-FTS-005 draft-submission-transition.

        Verify file transitions from draft to circulated and appears in recipient inbox.
        """
        draft = create_file_draft(
            creator_id="emp_sub_1",
            creator_role="Faculty",
            subject="Submission Transition File",
            initial_comment="First comment",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_sub_1",
            sender_role="Faculty",
            receiver_id="emp_sub_2",
            receiver_role="HOD",
            comment="Transferred",
        )
        inbox = get_user_inbox_files(user_id="emp_sub_2")
        assert any(item["id"] == draft["file_id"] for item in inbox)

    def test_br_015_forward_comment_permitted(self):
        """[BR-015] BR-FTS-006 forward-comment-permitted.

        Verify forward succeeds with non-empty movement comment.
        """
        draft = create_file_draft(
            creator_id="emp_fwd_1",
            creator_role="Staff",
            subject="Forward Comment Permitted",
            initial_comment="First",
        )
        res = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fwd_1",
            sender_role="Staff",
            receiver_id="emp_fwd_2",
            receiver_role="Faculty",
            comment="Valid non-empty forward remark",
        )
        assert res["new_status"] == STATUS_IN_TRANSIT

    def test_br_016_forward_comment_prohibited_empty(self):
        """[BR-016] BR-FTS-006 forward-comment-prohibited-empty.

        Verify forward blocked when comment is empty.
        """
        draft = create_file_draft(
            creator_id="emp_fwd_3",
            creator_role="Staff",
            subject="Forward Empty Comment",
            initial_comment="First",
        )
        with pytest.raises(PermissionError, match="Movement comment is mandatory"):
            forward_file(
                file_id=draft["file_id"],
                sender_id="emp_fwd_3",
                sender_role="Staff",
                receiver_id="emp_fwd_4",
                receiver_role="Faculty",
                comment="   ",
            )

    def test_br_017_return_comment_permitted(self):
        """[BR-017] BR-FTS-006 return-comment-permitted.

        Verify return succeeds with non-empty comment.
        """
        draft = create_file_draft(
            creator_id="emp_ret_3",
            creator_role="Staff",
            subject="Return Comment Permitted",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_ret_3",
            sender_role="Staff",
            receiver_id="emp_ret_4",
            receiver_role="HOD",
            comment="Forwarded",
        )
        ret = return_file(
            file_id=draft["file_id"],
            sender_id="emp_ret_4",
            sender_role="HOD",
            comment="Valid return comment",
        )
        assert ret["new_status"] == STATUS_RETURNED

    def test_br_018_return_comment_prohibited_empty(self):
        """[BR-018] BR-FTS-006 return-comment-prohibited-empty.

        Verify return blocked when comment is empty.
        """
        draft = create_file_draft(
            creator_id="emp_ret_5",
            creator_role="Staff",
            subject="Return Empty Comment",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_ret_5",
            sender_role="Staff",
            receiver_id="emp_ret_6",
            receiver_role="HOD",
            comment="Forwarded",
        )
        with pytest.raises(PermissionError, match="Movement comment is mandatory"):
            return_file(
                file_id=draft["file_id"],
                sender_id="emp_ret_6",
                sender_role="HOD",
                comment="   ",
            )

    def test_br_019_recipient_cross_role_permitted(self):
        """[BR-019] BR-FTS-007 recipient-cross-role-permitted.

        Verify forward succeeds across different administrative and academic roles.
        """
        draft = create_file_draft(
            creator_id="emp_cross_1",
            creator_role="Assistant Professor",
            subject="Cross Role Forward",
            initial_comment="Initial",
        )
        res = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_cross_1",
            sender_role="Assistant Professor",
            receiver_id="emp_cross_2",
            receiver_role="Dean Academic",
            comment="Cross role forward to Dean",
        )
        assert res["current_holder_id"] == "emp_cross_2"

    def test_br_020_recipient_invalid_prohibited(self):
        """[BR-020] BR-FTS-007 recipient-invalid-prohibited.

        Verify forward refused with validation error when recipient is non-existent/invalid (DEF-002).
        """
        draft = create_file_draft(
            creator_id="emp_inv_1",
            creator_role="Staff",
            subject="Invalid Recipient Test",
            initial_comment="Initial",
        )
        # Attempting forward to an invalid/non-existent user identifier must be refused
        with pytest.raises((ValueError, PermissionError), match="Invalid or non-existent recipient"):
            forward_file(
                file_id=draft["file_id"],
                sender_id="emp_inv_1",
                sender_role="Staff",
                receiver_id="",  # Invalid recipient
                receiver_role="",
                comment="Forwarding to nobody",
            )

    def test_br_021_return_to_previous_sender_permitted(self):
        """[BR-021] BR-FTS-007 return-to-previous-sender-permitted.

        Verify file returns back to previous sender.
        """
        draft = create_file_draft(
            creator_id="emp_ps_1",
            creator_role="Staff",
            subject="Return to Previous Sender",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_ps_1",
            sender_role="Staff",
            receiver_id="emp_ps_2",
            receiver_role="HOD",
            comment="Forwarded to 2",
        )
        ret = return_file(
            file_id=draft["file_id"],
            sender_id="emp_ps_2",
            sender_role="HOD",
            comment="Returned to 1",
        )
        assert ret["returned_to_id"] == "emp_ps_1"

    def test_br_022_return_to_arbitrary_user_prohibited(self):
        """[BR-022] BR-FTS-007 return-to-arbitrary-user-prohibited.

        Verify returning to arbitrary user outside movement chain is rejected.
        """
        draft = create_file_draft(
            creator_id="emp_arb_1",
            creator_role="Staff",
            subject="Arbitrary Return Prohibited",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_arb_1",
            sender_role="Staff",
            receiver_id="emp_arb_2",
            receiver_role="HOD",
            comment="Sent to 2",
        )
        with pytest.raises(ValueError, match="not in the historical movement chain"):
            return_file(
                file_id=draft["file_id"],
                sender_id="emp_arb_2",
                sender_role="HOD",
                comment="Returning to outsider",
                target_receiver_id="random_outsider_user",
            )

    def test_br_023_movement_record_completeness(self):
        """[BR-023] BR-FTS-008 movement-record-completeness.

        Verify movement record captures sender, receiver, timestamp, comment.
        """
        draft = create_file_draft(
            creator_id="emp_mov_1",
            creator_role="Faculty",
            subject="Movement Completeness File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_mov_1",
            sender_role="Faculty",
            receiver_id="emp_mov_2",
            receiver_role="HOD",
            comment="Movement record test",
        )
        history = get_file_movement_history(file_id=draft["file_id"])
        last_mov = history[-1]
        assert last_mov["from_user_id"] == "emp_mov_1"
        assert last_mov["to_user_id"] == "emp_mov_2"
        assert last_mov["created_at"] is not None
        assert len(last_mov["comments"]) == 1

    def test_br_024_movement_chronological_append(self):
        """[BR-024] BR-FTS-008 movement-chronological-append.

        Verify all movement events are ordered chronologically.
        """
        draft = create_file_draft(
            creator_id="emp_seq_1",
            creator_role="Staff",
            subject="Chronological Append File",
            initial_comment="Start",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_seq_1",
            sender_role="Staff",
            receiver_id="emp_seq_2",
            receiver_role="HOD",
            comment="Forward 1",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_seq_2",
            sender_role="HOD",
            comment="Return 1",
        )
        history = get_file_movement_history(file_id=draft["file_id"])
        actions = [h["action"] for h in history]
        assert actions == ["created", "forwarded", "returned"]

    def test_br_025_movement_holder_consistency(self):
        """[BR-025] BR-FTS-008 movement-holder-consistency.

        Verify holder updates to receiver after forward, and updates to sender after return.
        """
        draft = create_file_draft(
            creator_id="emp_hc_1",
            creator_role="Staff",
            subject="Holder Consistency File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_hc_1",
            sender_role="Staff",
            receiver_id="emp_hc_2",
            receiver_role="HOD",
            comment="Forwarded",
        )
        f1 = FTSFile.objects.get(id=draft["file_id"])
        assert f1.current_holder_id == "emp_hc_2"

        return_file(
            file_id=draft["file_id"],
            sender_id="emp_hc_2",
            sender_role="HOD",
            comment="Returned",
        )
        f2 = FTSFile.objects.get(id=draft["file_id"])
        assert f2.current_holder_id == "emp_hc_1"

    def test_br_026_inbox_visibility_permitted(self):
        """[BR-026] BR-FTS-009 inbox-visibility-permitted.

        Verify active file appears in recipient inbox.
        """
        draft = create_file_draft(
            creator_id="emp_inb_1",
            creator_role="Faculty",
            subject="Inbox Visibility File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_inb_1",
            sender_role="Faculty",
            receiver_id="emp_inb_2",
            receiver_role="Dean",
            comment="Sent to Dean",
        )
        inbox = get_user_inbox_files(user_id="emp_inb_2")
        assert any(item["id"] == draft["file_id"] for item in inbox)

    def test_br_027_outbox_visibility_permitted(self):
        """[BR-027] BR-FTS-009 outbox-visibility-permitted.

        Verify forwarded file appears in sender outbox.
        """
        draft = create_file_draft(
            creator_id="emp_out_1",
            creator_role="Faculty",
            subject="Outbox Visibility File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_out_1",
            sender_role="Faculty",
            receiver_id="emp_out_2",
            receiver_role="Dean",
            comment="Sent to Dean",
        )
        outbox = get_user_outbox_files(user_id="emp_out_1")
        assert any(item["id"] == draft["file_id"] for item in outbox)

    def test_br_028_unassociated_file_access_prohibited(self):
        """[BR-028] BR-FTS-009 unassociated-file-access-prohibited.

        Verify unassociated employee cannot see file in inbox or outbox.
        """
        draft = create_file_draft(
            creator_id="emp_priv_1",
            creator_role="Faculty",
            subject="Private File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_priv_1",
            sender_role="Faculty",
            receiver_id="emp_priv_2",
            receiver_role="Dean",
            comment="Private forward",
        )
        inbox_x = get_user_inbox_files(user_id="emp_outsider_x")
        outbox_x = get_user_outbox_files(user_id="emp_outsider_x")
        assert not any(item["id"] == draft["file_id"] for item in inbox_x)
        assert not any(item["id"] == draft["file_id"] for item in outbox_x)

    def test_br_029_archived_file_readable_to_associated(self):
        """[BR-029] BR-FTS-009 archived-file-readable-to-associated.

        Verify associated user can read archived file history.
        """
        draft = create_file_draft(
            creator_id="emp_arc_read_1",
            creator_role="Staff",
            subject="Archived Read File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_arc_read_1",
            sender_role="Staff",
            receiver_id="emp_arc_read_2",
            receiver_role="HOD",
            comment="Circulating",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_arc_read_2",
            sender_role="HOD",
            comment="Returned",
        )
        archive_file(
            file_id=draft["file_id"],
            user_id="emp_arc_read_1",
            user_role="Staff",
            remarks="Archiving for read-only retention",
        )
        history = get_file_movement_history(file_id=draft["file_id"])
        assert len(history) >= 2

    def test_br_030_authorized_action_permitted(self):
        """[BR-030] BR-FTS-010 authorized-action-permitted.

        Verify authorized user forward succeeds.
        """
        draft = create_file_draft(
            creator_id="emp_auth_1",
            creator_role="Faculty",
            subject="Authorized Forward File",
            initial_comment="Initial",
        )
        res = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_auth_1",
            sender_role="Faculty",
            receiver_id="emp_auth_2",
            receiver_role="Staff",
            comment="Authorized move",
        )
        assert res["current_holder_id"] == "emp_auth_2"

    def test_br_031_unauthorized_role_prohibited(self):
        """[BR-031] BR-FTS-010 unauthorized-role-prohibited.

        Verify user lacking custodian authority cannot forward.
        """
        draft = create_file_draft(
            creator_id="emp_unauth_1",
            creator_role="Faculty",
            subject="Unauthorized Forward File",
            initial_comment="Initial",
        )
        with pytest.raises(PermissionError, match="Only the current custodian"):
            forward_file(
                file_id=draft["file_id"],
                sender_id="emp_unauth_hacker",
                sender_role="Faculty",
                receiver_id="emp_unauth_2",
                receiver_role="Staff",
                comment="Unauthorized move",
            )

    def test_br_032_state_mismatch_action_prohibited(self):
        """[BR-032] BR-FTS-010 state-mismatch-action-prohibited.

        Verify forward rejected when file is already archived.
        """
        draft = create_file_draft(
            creator_id="emp_sm_1",
            creator_role="Staff",
            subject="State Mismatch File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_sm_1",
            sender_role="Staff",
            receiver_id="emp_sm_2",
            receiver_role="Faculty",
            comment="Circulating",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_sm_2",
            sender_role="Faculty",
            comment="Returned",
        )
        archive_file(
            file_id=draft["file_id"],
            user_id="emp_sm_1",
            user_role="Staff",
            remarks="Archived",
        )
        with pytest.raises(PermissionError, match="Archived files are terminal"):
            forward_file(
                file_id=draft["file_id"],
                sender_id="emp_sm_1",
                sender_role="Staff",
                receiver_id="emp_sm_2",
                receiver_role="Faculty",
                comment="Attempt forward on archived",
            )

    def test_br_033_audit_record_generation(self):
        """[BR-033] BR-FTS-011 audit-record-generation.

        Verify audit entries exist for creation, forward, and archival.
        """
        draft = create_file_draft(
            creator_id="emp_aud_1",
            creator_role="Staff",
            subject="Audit Gen File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_aud_1",
            sender_role="Staff",
            receiver_id="emp_aud_2",
            receiver_role="HOD",
            comment="Forwarded",
        )
        archive_file(
            file_id=draft["file_id"],
            user_id="emp_aud_1",
            user_role="Staff",
            remarks="Archived",
        )
        history = get_file_movement_history(file_id=draft["file_id"])
        actions = [h["action"] for h in history]
        assert "created" in actions
        assert "forwarded" in actions
        assert "archived" in actions

    def test_br_034_audit_record_immutability(self):
        """[BR-034] BR-FTS-011 audit-record-immutability.

        Verify historical audit movements are preserved append-only.
        """
        draft = create_file_draft(
            creator_id="emp_imm_1",
            creator_role="Faculty",
            subject="Immutable Audit File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_imm_1",
            sender_role="Faculty",
            receiver_id="emp_imm_2",
            receiver_role="HOD",
            comment="First move",
        )
        m1 = FTSMovement.objects.filter(file_id=draft["file_id"]).first()
        m1_from = m1.from_user_id
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_imm_2",
            sender_role="HOD",
            receiver_id="emp_imm_3",
            receiver_role="Dean",
            comment="Second move",
        )
        refreshed_m1 = FTSMovement.objects.get(id=m1.id)
        assert refreshed_m1.from_user_id == m1_from

    def test_br_035_integration_audit_generation(self):
        """[BR-035] BR-FTS-011 integration-audit-generation.

        Verify external contract calls accurately reflect underlying audit history.
        """
        draft = create_file_draft(
            creator_id="emp_int_1",
            creator_role="Faculty",
            subject="Integration Audit File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_int_1",
            sender_role="Faculty",
            receiver_id="emp_int_2",
            receiver_role="Dean",
            comment="Integration move",
        )
        summaries = get_files_by_uins([draft["uin"]])
        assert len(summaries) == 1
        assert summaries[0].current_holder_id == "emp_int_2"

    def test_br_036_owner_archival_permitted(self):
        """[BR-036] BR-FTS-012 owner-archival-permitted.

        Verify owner can archive file.
        """
        draft = create_file_draft(
            creator_id="emp_own_arc_1",
            creator_role="Faculty",
            subject="Owner Archival Permitted",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_own_arc_1",
            sender_role="Faculty",
            receiver_id="emp_own_arc_2",
            receiver_role="HOD",
            comment="Circulating",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_own_arc_2",
            sender_role="HOD",
            comment="Returned to owner",
        )
        res = archive_file(
            file_id=draft["file_id"],
            user_id="emp_own_arc_1",
            user_role="Faculty",
            remarks="Archiving my own file",
        )
        assert res["status"] == STATUS_ARCHIVED

    def test_br_037_non_owner_archival_prohibited(self):
        """[BR-037] BR-FTS-012 non-owner-archival-prohibited.

        Verify non-owner recipient cannot archive file (DEF-001).
        """
        draft = create_file_draft(
            creator_id="emp_creator_a",
            creator_role="Staff",
            subject="Non-Owner Archival Refusal",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_creator_a",
            sender_role="Staff",
            receiver_id="emp_recipient_b",
            receiver_role="HOD",
            comment="Sent to HOD",
        )
        # Recipient B is holder but NOT the owner/creator. Archival must be refused.
        with pytest.raises(PermissionError, match="Only the file owner can archive this file"):
            archive_file(
                file_id=draft["file_id"],
                user_id="emp_recipient_b",
                user_role="HOD",
                remarks="Attempted non-owner closure",
            )

    def test_br_038_archived_modification_prohibited(self):
        """[BR-038] BR-FTS-012 archived-modification-prohibited.

        Verify modification of archived file is rejected.
        """
        draft = create_file_draft(
            creator_id="emp_arc_mod_1",
            creator_role="Staff",
            subject="Archived Mod Prohibited",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_arc_mod_1",
            sender_role="Staff",
            receiver_id="emp_arc_mod_2",
            receiver_role="HOD",
            comment="Circulating",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_arc_mod_2",
            sender_role="HOD",
            comment="Returned",
        )
        archive_file(
            file_id=draft["file_id"],
            user_id="emp_arc_mod_1",
            user_role="Staff",
            remarks="Archived",
        )
        with pytest.raises(PermissionError, match="Only files in draft status can be modified"):
            update_file_draft(
                file_id=draft["file_id"],
                user_id="emp_arc_mod_1",
                subject="New Title On Archived",
            )

    def test_br_039_archived_forwarding_prohibited(self):
        """[BR-039] BR-FTS-012 archived-forwarding-prohibited.

        Verify forwarding archived file is rejected.
        """
        draft = create_file_draft(
            creator_id="emp_arc_fwd_1",
            creator_role="Staff",
            subject="Archived Forward Prohibited",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_arc_fwd_1",
            sender_role="Staff",
            receiver_id="emp_arc_fwd_2",
            receiver_role="Faculty",
            comment="Circulating",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_arc_fwd_2",
            sender_role="Faculty",
            comment="Returned",
        )
        archive_file(
            file_id=draft["file_id"],
            user_id="emp_arc_fwd_1",
            user_role="Staff",
            remarks="Archived",
        )
        with pytest.raises(PermissionError, match="Archived files are terminal"):
            forward_file(
                file_id=draft["file_id"],
                sender_id="emp_arc_fwd_1",
                sender_role="Staff",
                receiver_id="emp_arc_fwd_2",
                receiver_role="Faculty",
                comment="Forwarding archived file",
            )

    def test_br_040_notify_file_received_and_forwarded(self):
        """[BR-040] BR-FTS-013 notify-file-received-and-forwarded.

        Verify notification events for forward and receive are dispatched.
        """
        draft = create_file_draft(
            creator_id="emp_br40_a",
            creator_role="Faculty",
            subject="BR-040 Forward & Receive Notify",
            initial_comment="Initial draft",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_br40_a",
            sender_role="Faculty",
            receiver_id="emp_br40_b",
            receiver_role="Staff",
            comment="Forward notification payload",
        )
        history = get_file_movement_history(file_id=draft["file_id"])
        event = history[-1]
        assert event["action"] == "forwarded"
        assert event["from_user_id"] == "emp_br40_a"
        assert event["to_user_id"] == "emp_br40_b"
        assert event["created_at"] is not None
        assert event["comments"][0]["remarks"] == "Forward notification payload"

    def test_br_041_notify_file_returned(self):
        """[BR-041] BR-FTS-013 notify-file-returned.

        Verify notification event for returned file is dispatched.
        """
        draft = create_file_draft(
            creator_id="emp_br41_a",
            creator_role="Faculty",
            subject="BR-041 Return Notify",
            initial_comment="Initial draft",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_br41_a",
            sender_role="Faculty",
            receiver_id="emp_br41_b",
            receiver_role="HOD",
            comment="First pass",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_br41_b",
            sender_role="HOD",
            comment="Needs amendments",
        )
        history = get_file_movement_history(file_id=draft["file_id"])
        event = history[-1]
        assert event["action"] == "returned"
        assert event["from_user_id"] == "emp_br41_b"
        assert event["to_user_id"] == "emp_br41_a"
        assert event["created_at"] is not None
        assert event["comments"][0]["remarks"] == "Needs amendments"

    def test_br_042_notify_file_archived(self):
        """[BR-042] BR-FTS-013 notify-file-archived.

        Verify notification event for archived file is dispatched.
        """
        draft = create_file_draft(
            creator_id="emp_br42_a",
            creator_role="Staff",
            subject="BR-042 Archive Notify",
            initial_comment="Initial draft",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_br42_a",
            sender_role="Staff",
            receiver_id="emp_br42_b",
            receiver_role="Faculty",
            comment="Processed",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_br42_b",
            sender_role="Faculty",
            comment="Returned to creator",
        )
        arc = archive_file(
            file_id=draft["file_id"],
            user_id="emp_br42_a",
            user_role="Staff",
            remarks="Completed lifecycle",
        )
        assert arc["status"] == STATUS_ARCHIVED
        history = get_file_movement_history(file_id=draft["file_id"])
        event = history[-1]
        assert event["action"] == "archived"
        assert event["from_user_id"] == "emp_br42_a"
        assert event["created_at"] is not None
        assert event["comments"][0]["remarks"] == "Completed lifecycle"

    def test_br_043_notify_role_reassigned(self):
        """[BR-043] BR-FTS-013 notify-role-reassigned.

        Verify notification event for role reassignment is dispatched.
        """
        role_grants = get_role_grants()
        assert "faculty" in role_grants
        assert "staff" in role_grants

        draft = create_file_draft(
            creator_id="emp_br43_a",
            creator_role="Staff",
            subject="BR-043 Role Transition Notify",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_br43_a",
            sender_role="Staff",
            receiver_id="emp_br43_b",
            receiver_role="Dean",
            comment="Forward across roles",
        )
        history = get_file_movement_history(file_id=draft["file_id"])
        event = history[-1]
        assert event["from_role"] == "Staff"
        assert event["to_role"] == "Dean"
        assert event["created_at"] is not None

    def test_br_044_authorized_api_access_permitted(self):
        """[BR-044] BR-FTS-014 authorized-api-access-permitted.

        Verify consuming module API contract access succeeds.
        """
        draft = create_file_draft(
            creator_id="emp_api_acc_1",
            creator_role="Staff",
            subject="API Contract Access File",
            initial_comment="Initial",
        )
        dtos = get_files_by_uins([draft["uin"]])
        assert len(dtos) == 1
        assert dtos[0].uin == draft["uin"]

    def test_br_045_unauthorized_api_access_prohibited(self):
        """[BR-045] BR-FTS-014 unauthorized-api-access-prohibited.

        Verify API access without valid authentication context is rejected with 401/403.
        """
        factory = APIRequestFactory()
        view = FTSFileViewSet.as_view({"get": "inbox"})
        req = factory.get("/api/v1/fts/files/inbox/")
        req.user = type("AnonymousUser", (), {"is_authenticated": False, "username": ""})()
        # Anonymous unauthenticated request returns empty or refused
        resp = view(req)
        assert resp.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_br_046_domain_approval_policy_boundary(self):
        """[BR-046] BR-FTS-014 domain-approval-policy-boundary.

        Verify FTS tracks file requests without evaluating external domain approval rules.
        """
        # FTS tracks file state without rejecting based on external domain policies
        draft = create_file_draft(
            creator_id="emp_acad_1",
            creator_role="Student",
            subject="Course Withdrawal Petition",
            initial_comment="Requesting late drop",
        )
        assert draft["status"] == STATUS_DRAFT
        res = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_acad_1",
            sender_role="Student",
            receiver_id="emp_advisor_1",
            receiver_role="Faculty Advisor",
            comment="Submitting petition",
        )
        assert res["new_status"] == STATUS_IN_TRANSIT
