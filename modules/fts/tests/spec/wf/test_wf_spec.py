"""Specification-based tests for Workflow (WF) strategy.

Implements all 23 test cases from docs/07-fts/spec-tests/WF_DESIGN.json.
"""

import pytest

from modules.fts.domain.workflow import (
    ACTION_FORWARDED,
    STATUS_ARCHIVED,
    STATUS_DRAFT,
    STATUS_IN_TRANSIT,
    STATUS_RETURNED,
)
from modules.fts.models import FTSAttachment, FTSFile, FTSMovement
from modules.fts.selectors.movements import get_file_movement_history
from modules.fts.services.archival import archive_file
from modules.fts.services.drafts import (
    create_file_draft,
    discard_file_draft,
    update_file_draft,
)
from modules.fts.services.movements import forward_file, return_file


@pytest.mark.django_db
class TestWorkflowBasisAndCompound:
    """Executable test suite for Basis Workflows (BW-FTS-01..08) and Compound Workflows (CW-FTS-01..02)."""

    def test_wf_001_bw_fts_01_single_forward_zero_onward(self):
        """[WF-001] BW-FTS-01 single-forward-zero-onward.

        Verify single forward from sender to recipient with movement comment and attachment.
        """
        draft = create_file_draft(
            creator_id="emp_sender_01",
            creator_role="Faculty",
            subject="BW-01 Single Forward File",
            initial_comment="Initial draft creation",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        att = FTSAttachment.objects.create(
            file=file_obj,
            file_name="doc.pdf",
            file_url="https://example.com/doc.pdf",
            uploaded_by_id="emp_sender_01",
        )
        assert att.id is not None

        result = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_sender_01",
            sender_role="Faculty",
            receiver_id="emp_recipient_01",
            receiver_role="HOD",
            comment="Forwarding single step for approval",
        )

        assert result["new_status"] == STATUS_IN_TRANSIT
        assert result["current_holder_id"] == "emp_recipient_01"

        refreshed = FTSFile.objects.get(id=draft["file_id"])
        assert refreshed.status == STATUS_IN_TRANSIT
        assert refreshed.current_holder_id == "emp_recipient_01"

        history = get_file_movement_history(file_id=draft["file_id"])
        assert len(history) == 2
        assert history[1]["action"] == ACTION_FORWARDED
        assert history[1]["to_user_id"] == "emp_recipient_01"

    def test_wf_002_bw_fts_02_onward_forwarding_one_loop(self):
        """[WF-002] BW-FTS-02 onward-forwarding-one-loop.

        Verify onward forwarding where recipient passes file to next recipient.
        """
        draft = create_file_draft(
            creator_id="user_a",
            creator_role="Staff",
            subject="BW-02 Onward Forward File",
            initial_comment="First creation",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="user_a",
            sender_role="Staff",
            receiver_id="user_b",
            receiver_role="HOD",
            comment="Forwarding to HOD",
        )
        result = forward_file(
            file_id=draft["file_id"],
            sender_id="user_b",
            sender_role="HOD",
            receiver_id="user_c",
            receiver_role="Dean",
            comment="Onward forwarding to Dean",
        )

        assert result["new_status"] == STATUS_IN_TRANSIT
        assert result["current_holder_id"] == "user_c"

        refreshed = FTSFile.objects.get(id=draft["file_id"])
        assert refreshed.current_holder_id == "user_c"
        history = get_file_movement_history(file_id=draft["file_id"])
        assert len(history) == 3

    def test_wf_003_bw_fts_03_return_to_previous_sender(self):
        """[WF-003] BW-FTS-03 return-to-previous-sender.

        Verify returning a received file to the previous sender.
        """
        draft = create_file_draft(
            creator_id="sender_1",
            creator_role="Faculty",
            subject="BW-03 Return Workflow File",
            initial_comment="Proposal submission",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="sender_1",
            sender_role="Faculty",
            receiver_id="recipient_1",
            receiver_role="HOD",
            comment="Submitting to HOD",
        )

        ret_result = return_file(
            file_id=draft["file_id"],
            sender_id="recipient_1",
            sender_role="HOD",
            comment="Returning for revision",
        )

        assert ret_result["new_status"] == STATUS_RETURNED
        assert ret_result["returned_to_id"] == "sender_1"

        refreshed = FTSFile.objects.get(id=draft["file_id"])
        assert refreshed.status == STATUS_RETURNED
        assert refreshed.current_holder_id == "sender_1"

    def test_wf_004_bw_fts_04_archive_completed_circulated_file(self):
        """[WF-004] BW-FTS-04 archive-completed-circulated-file.

        Verify owner archiving an active circulated file.
        """
        draft = create_file_draft(
            creator_id="owner_1",
            creator_role="Dean",
            subject="BW-04 Completed Task File",
            initial_comment="Mandatory start",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="owner_1",
            sender_role="Dean",
            receiver_id="worker_1",
            receiver_role="Staff",
            comment="Execute task",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="worker_1",
            sender_role="Staff",
            comment="Work finished, returning to owner",
        )

        arc_result = archive_file(
            file_id=draft["file_id"],
            user_id="owner_1",
            user_role="Dean",
            remarks="Task complete. Archiving record.",
        )

        assert arc_result["status"] == STATUS_ARCHIVED
        refreshed = FTSFile.objects.get(id=draft["file_id"])
        assert refreshed.status == STATUS_ARCHIVED

        with pytest.raises(PermissionError):
            forward_file(
                file_id=draft["file_id"],
                sender_id="owner_1",
                sender_role="Dean",
                receiver_id="worker_2",
                receiver_role="Staff",
                comment="Attempt forward on archived",
            )

    def test_wf_005_bw_fts_05_step_1_draft_creation(self):
        """[WF-005] BW-FTS-05 Step 1 draft-creation.

        Verify initial draft creation enters draft state.
        """
        res = create_file_draft(
            creator_id="emp_d1",
            creator_role="Staff",
            subject="BW-05 Step 1 Draft",
            initial_comment="Opening draft comment",
        )
        assert res["status"] == STATUS_DRAFT
        assert res["is_draft"] is True
        file_obj = FTSFile.objects.get(id=res["file_id"])
        assert file_obj.status == STATUS_DRAFT

    def test_wf_006_bw_fts_05_step_2_immediate_circulation(self):
        """[WF-006] BW-FTS-05 Step 2 immediate-circulation.

        Verify immediate forward from draft to recipient without prior editing.
        """
        draft = create_file_draft(
            creator_id="emp_d2",
            creator_role="Staff",
            subject="BW-05 Step 2 File",
            initial_comment="Draft for immediate send",
        )
        res = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_d2",
            sender_role="Staff",
            receiver_id="emp_r2",
            receiver_role="HOD",
            comment="Sending immediately",
        )
        assert res["new_status"] == STATUS_IN_TRANSIT
        assert res["current_holder_id"] == "emp_r2"

        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert file_obj.status == STATUS_IN_TRANSIT
        assert file_obj.is_draft is False

    def test_wf_007_bw_fts_06_step_1_draft_creation(self):
        """[WF-007] BW-FTS-06 Step 1 draft-creation.

        Verify initial draft creation.
        """
        draft = create_file_draft(
            creator_id="emp_d3",
            creator_role="Faculty",
            subject="BW-06 Draft Creation",
            initial_comment="Draft remark",
        )
        assert draft["status"] == STATUS_DRAFT
        assert FTSFile.objects.filter(id=draft["file_id"], status=STATUS_DRAFT).exists()

    def test_wf_008_bw_fts_06_step_2_draft_edit_traversal(self):
        """[WF-008] BW-FTS-06 Step 2 draft-edit-traversal.

        Verify draft content editing traversal.
        """
        draft = create_file_draft(
            creator_id="emp_d4",
            creator_role="Faculty",
            subject="BW-06 Initial Title",
            initial_comment="Initial remark",
        )
        updated = update_file_draft(
            file_id=draft["file_id"],
            user_id="emp_d4",
            subject="BW-06 Edited Title",
            priority="urgent",
        )
        assert updated["subject"] == "BW-06 Edited Title"
        refreshed = FTSFile.objects.get(id=draft["file_id"])
        assert refreshed.subject == "BW-06 Edited Title"
        assert refreshed.priority == "urgent"
        assert refreshed.status == STATUS_DRAFT

    def test_wf_009_bw_fts_06_step_3_circulate_updated_draft(self):
        """[WF-009] BW-FTS-06 Step 3 circulate-updated-draft.

        Verify circulation of updated draft file.
        """
        draft = create_file_draft(
            creator_id="emp_d5",
            creator_role="Faculty",
            subject="BW-06 V1 Title",
            initial_comment="Initial remark",
        )
        update_file_draft(
            file_id=draft["file_id"],
            user_id="emp_d5",
            subject="BW-06 V2 Title",
        )
        res = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_d5",
            sender_role="Faculty",
            receiver_id="emp_rec_5",
            receiver_role="Dean",
            comment="Circulating edited draft",
        )
        assert res["new_status"] == STATUS_IN_TRANSIT
        assert res["current_holder_id"] == "emp_rec_5"

    def test_wf_010_bw_fts_07_step_1_draft_creation(self):
        """[WF-010] BW-FTS-07 Step 1 draft-creation.

        Verify draft enters pre-circulation state.
        """
        res = create_file_draft(
            creator_id="emp_d6",
            creator_role="Staff",
            subject="BW-07 Draft",
            initial_comment="Remark for draft",
        )
        assert res["status"] == STATUS_DRAFT
        assert FTSFile.objects.filter(id=res["file_id"], is_draft=True).exists()

    def test_wf_011_bw_fts_07_step_2_draft_discard_zero_edit(self):
        """[WF-011] BW-FTS-07 Step 2 draft-discard-zero-edit.

        Verify discarding draft before editing removes the file.
        """
        res = create_file_draft(
            creator_id="emp_d7",
            creator_role="Staff",
            subject="BW-07 Discard File",
            initial_comment="To be discarded",
        )
        discard_file_draft(file_id=res["file_id"], user_id="emp_d7")
        assert not FTSFile.objects.filter(id=res["file_id"]).exists()

    def test_wf_012_bw_fts_08_step_1_draft_creation(self):
        """[WF-012] BW-FTS-08 Step 1 draft-creation.

        Verify draft creation.
        """
        res = create_file_draft(
            creator_id="emp_d8",
            creator_role="Staff",
            subject="BW-08 Draft File",
            initial_comment="Step 1 draft comment",
        )
        assert res["status"] == STATUS_DRAFT

    def test_wf_013_bw_fts_08_step_2_draft_edit_traversal(self):
        """[WF-013] BW-FTS-08 Step 2 draft-edit-traversal.

        Verify editing draft content.
        """
        res = create_file_draft(
            creator_id="emp_d9",
            creator_role="Staff",
            subject="BW-08 Initial Subject",
            initial_comment="Initial remark",
        )
        updated = update_file_draft(
            file_id=res["file_id"],
            user_id="emp_d9",
            subject="BW-08 Modified Subject",
        )
        assert updated["subject"] == "BW-08 Modified Subject"

    def test_wf_014_bw_fts_08_step_3_discard_updated_draft(self):
        """[WF-014] BW-FTS-08 Step 3 discard-updated-draft.

        Verify discarding an updated draft before circulation.
        """
        res = create_file_draft(
            creator_id="emp_d10",
            creator_role="Staff",
            subject="BW-08 Subject Pre-Discard",
            initial_comment="Remark",
        )
        update_file_draft(
            file_id=res["file_id"],
            user_id="emp_d10",
            subject="BW-08 Subject Post-Edit",
        )
        discard_file_draft(file_id=res["file_id"], user_id="emp_d10")
        assert not FTSFile.objects.filter(id=res["file_id"]).exists()

    def test_wf_015_cw_fts_01_path_1_forward_to_completion_archival(self):
        """[WF-015] CW-FTS-01 Path 1 forward-to-completion-archival.

        Verify compound workflow: forward to completion and archive by owner.
        """
        draft = create_file_draft(
            creator_id="cw_owner_1",
            creator_role="Faculty",
            subject="CW-01 Path 1 File",
            initial_comment="Starting compound workflow",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="cw_owner_1",
            sender_role="Faculty",
            receiver_id="cw_rec_1",
            receiver_role="HOD",
            comment="Forward for review",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="cw_rec_1",
            sender_role="HOD",
            comment="Approved and returned to owner",
        )
        arc = archive_file(
            file_id=draft["file_id"],
            user_id="cw_owner_1",
            user_role="Faculty",
            remarks="Completed successfully",
        )
        assert arc["status"] == STATUS_ARCHIVED

    def test_wf_016_cw_fts_01_path_2_forward_then_return(self):
        """[WF-016] CW-FTS-01 Path 2 forward-then-return.

        Verify compound workflow: forward then return to previous sender.
        """
        draft = create_file_draft(
            creator_id="cw_user_a",
            creator_role="Staff",
            subject="CW-01 Path 2 File",
            initial_comment="Start",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="cw_user_a",
            sender_role="Staff",
            receiver_id="cw_user_b",
            receiver_role="Faculty",
            comment="Sending to B",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="cw_user_b",
            sender_role="Faculty",
            comment="Returning to A",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert file_obj.current_holder_id == "cw_user_a"
        assert file_obj.status == STATUS_RETURNED

    def test_wf_017_cw_fts_01_path_3_forward_onward_then_return(self):
        """[WF-017] CW-FTS-01 Path 3 forward-onward-then-return.

        Verify multi-step forward followed by return to direct previous sender.
        """
        draft = create_file_draft(
            creator_id="cw_a",
            creator_role="Staff",
            subject="CW-01 Path 3 File",
            initial_comment="A start",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="cw_a",
            sender_role="Staff",
            receiver_id="cw_b",
            receiver_role="HOD",
            comment="A to B",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="cw_b",
            sender_role="HOD",
            receiver_id="cw_c",
            receiver_role="Dean",
            comment="B to C",
        )
        ret = return_file(
            file_id=draft["file_id"],
            sender_id="cw_c",
            sender_role="Dean",
            comment="C returns to B",
        )
        assert ret["returned_to_id"] == "cw_b"
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert file_obj.current_holder_id == "cw_b"

    def test_wf_018_cw_fts_01_path_4_forward_onward_to_completion_archival(self):
        """[WF-018] CW-FTS-01 Path 4 forward-onward-to-completion-archival.

        Verify multi-step forward followed by archival.
        """
        draft = create_file_draft(
            creator_id="cw_owner_4",
            creator_role="Faculty",
            subject="CW-01 Path 4 File",
            initial_comment="Multi step file",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="cw_owner_4",
            sender_role="Faculty",
            receiver_id="cw_step_b",
            receiver_role="HOD",
            comment="Forward to B",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="cw_step_b",
            sender_role="HOD",
            receiver_id="cw_step_c",
            receiver_role="Director",
            comment="Forward to C",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="cw_step_c",
            sender_role="Director",
            comment="Director approves and returns to B",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="cw_step_b",
            sender_role="HOD",
            comment="HOD returns to Owner",
        )
        arc = archive_file(
            file_id=draft["file_id"],
            user_id="cw_owner_4",
            user_role="Faculty",
            remarks="Full loop complete, archiving",
        )
        assert arc["status"] == STATUS_ARCHIVED

    def test_wf_019_cw_fts_01_path_5_forward_return_reforward_archival(self):
        """[WF-019] CW-FTS-01 Path 5 forward-return-reforward-archival.

        Verify forward -> return -> re-forward -> return -> archival.
        """
        draft = create_file_draft(
            creator_id="cw_owner_5",
            creator_role="Faculty",
            subject="CW-01 Path 5 File",
            initial_comment="Complex loop start",
        )
        # 1. Forward to B
        forward_file(
            file_id=draft["file_id"],
            sender_id="cw_owner_5",
            sender_role="Faculty",
            receiver_id="cw_party_b",
            receiver_role="HOD",
            comment="Round 1 to B",
        )
        # 2. Return to A
        return_file(
            file_id=draft["file_id"],
            sender_id="cw_party_b",
            sender_role="HOD",
            comment="Return for revision",
        )
        # 3. Re-forward to B
        forward_file(
            file_id=draft["file_id"],
            sender_id="cw_owner_5",
            sender_role="Faculty",
            receiver_id="cw_party_b",
            receiver_role="HOD",
            comment="Revised and re-forwarded to B",
        )
        # 4. Return to A
        return_file(
            file_id=draft["file_id"],
            sender_id="cw_party_b",
            sender_role="HOD",
            comment="Final signoff return",
        )
        # 5. Archive
        arc = archive_file(
            file_id=draft["file_id"],
            user_id="cw_owner_5",
            user_role="Faculty",
            remarks="Archived after multi-round circulation",
        )
        assert arc["status"] == STATUS_ARCHIVED

        movements = FTSMovement.objects.filter(file_id=draft["file_id"]).order_by("created_at")
        assert movements.count() == 6  # created, fwd, ret, fwd, ret, arc

    def test_wf_020_cw_fts_02_path_1_create_draft_discard_zero_edit(self):
        """[WF-020] CW-FTS-02 Path 1 create-draft-discard-zero-edit.

        Verify create draft -> discard zero edit lifecycle.
        """
        res = create_file_draft(
            creator_id="cw_user_d1",
            creator_role="Staff",
            subject="CW-02 Path 1 File",
            initial_comment="Zero edit discard",
        )
        discard_file_draft(file_id=res["file_id"], user_id="cw_user_d1")
        assert not FTSFile.objects.filter(id=res["file_id"]).exists()

    def test_wf_021_cw_fts_02_path_2_create_draft_edit_discard(self):
        """[WF-021] CW-FTS-02 Path 2 create-draft-edit-discard.

        Verify create draft -> edit -> discard lifecycle.
        """
        res = create_file_draft(
            creator_id="cw_user_d2",
            creator_role="Staff",
            subject="CW-02 Path 2 Before Edit",
            initial_comment="Remark before edit",
        )
        update_file_draft(
            file_id=res["file_id"],
            user_id="cw_user_d2",
            subject="CW-02 Path 2 After Edit",
        )
        discard_file_draft(file_id=res["file_id"], user_id="cw_user_d2")
        assert not FTSFile.objects.filter(id=res["file_id"]).exists()

    def test_wf_022_cw_fts_02_path_3_create_draft_circulate_zero_edit(self):
        """[WF-022] CW-FTS-02 Path 3 create-draft-circulate-zero-edit.

        Verify create draft -> circulate directly without edits.
        """
        res = create_file_draft(
            creator_id="cw_user_d3",
            creator_role="Staff",
            subject="CW-02 Path 3 File",
            initial_comment="Direct circulation",
        )
        fwd = forward_file(
            file_id=res["file_id"],
            sender_id="cw_user_d3",
            sender_role="Staff",
            receiver_id="cw_user_r3",
            receiver_role="Faculty",
            comment="Sending unedited draft",
        )
        assert fwd["new_status"] == STATUS_IN_TRANSIT
        file_obj = FTSFile.objects.get(id=res["file_id"])
        assert file_obj.current_holder_id == "cw_user_r3"

    def test_wf_023_cw_fts_02_path_4_create_draft_edit_circulate(self):
        """[WF-023] CW-FTS-02 Path 4 create-draft-edit-circulate.

        Verify create draft -> edit -> circulate lifecycle.
        """
        res = create_file_draft(
            creator_id="cw_user_d4",
            creator_role="Staff",
            subject="CW-02 Path 4 Pre Edit",
            initial_comment="Pre edit remark",
        )
        update_file_draft(
            file_id=res["file_id"],
            user_id="cw_user_d4",
            subject="CW-02 Path 4 Post Edit",
            priority="high",
        )
        fwd = forward_file(
            file_id=res["file_id"],
            sender_id="cw_user_d4",
            sender_role="Staff",
            receiver_id="cw_user_r4",
            receiver_role="Faculty",
            comment="Sending edited draft",
        )
        assert fwd["new_status"] == STATUS_IN_TRANSIT
        file_obj = FTSFile.objects.get(id=res["file_id"])
        assert file_obj.subject == "CW-02 Path 4 Post Edit"
        assert file_obj.priority == "high"
        assert file_obj.current_holder_id == "cw_user_r4"
