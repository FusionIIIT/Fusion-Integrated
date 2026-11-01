"""Unit tests for FTS basis and composite workflows (Folder 7: 05_FTS_Workflow_Specifications).

Tests:
- BW-FTS-01: Forward File to Recipient — Zero Onward Traversal
- BW-FTS-02: Onward Forwarding — One Loop Traversal
- BW-FTS-03: Return File to Previous Sender
- BW-FTS-04: Archive Completed Circulated File
- BW-FTS-05: Prepare and Circulate New File — Zero Draft-Edit Traversal
- BW-FTS-06: Prepare and Circulate New File — One Draft-Edit Traversal
- BW-FTS-07: Create and Discard Draft — Zero Draft-Edit Traversal
- BW-FTS-08: Edit Once and Discard Draft — One Draft-Edit Traversal
- CW-FTS-01: Collaborative File Circulation and Completion
- CW-FTS-02: New File Preparation and Initial Outcome
"""
import pytest

from modules.filetracking.domain import (
    AttachmentInfo,
    DraftBoundaryViolationError,
    FileArchivedError,
    FileComposite,
    FileLifecycleState,
    MovementType,
)


class TestBasisWorkflows:
    def test_bw_fts_01_forward_file_zero_onward_traversal(self):
        """BW-FTS-01: File circulated from creator to recipient without onward forward."""
        file_obj = FileComposite.create_new_draft(
            subject="Approval of Conference Travel",
            description="Travel grant request",
            creator_id=10,
            creator_role="faculty",
            initial_comment="Requesting permission and budget approval.",
        )
        movement = file_obj.forward(
            sender_id=10,
            sender_role="faculty",
            receiver_id=20,
            receiver_role="HOD",
            comment="Forwarded for HOD recommendation.",
        )
        assert file_obj.state == FileLifecycleState.CIRCULATED
        assert file_obj.current_holder_id == 20
        assert movement.movement_type == MovementType.FORWARD
        assert len(file_obj.movements) == 1

    def test_bw_fts_02_onward_forwarding_one_loop_traversal(self):
        """BW-FTS-02: Onward forwarding through an intermediate recipient."""
        file_obj = FileComposite.create_new_draft(
            subject="Lab Budget Enhancement",
            description="Equipment procurement",
            creator_id=10,
            creator_role="faculty",
            initial_comment="Need enhanced budget for sensors.",
        )
        # Step 1: 10 -> 20 (HOD)
        file_obj.forward(
            sender_id=10,
            sender_role="faculty",
            receiver_id=20,
            receiver_role="HOD",
            comment="Recommending approval.",
        )
        # Step 2 (Loop traversal 1): 20 -> 30 (Dean)
        file_obj.forward(
            sender_id=20,
            sender_role="HOD",
            receiver_id=30,
            receiver_role="Dean",
            comment="Endorsed and forwarded to Dean.",
        )
        assert file_obj.current_holder_id == 30
        assert len(file_obj.movements) == 2
        assert file_obj.get_previous_sender_id() == 20

    def test_bw_fts_03_return_file_to_previous_sender(self):
        """BW-FTS-03: Return file to previous sender."""
        file_obj = FileComposite.create_new_draft(
            subject="Proposal Review",
            description="Project Proposal",
            creator_id=10,
            creator_role="faculty",
            initial_comment="Submission.",
        )
        file_obj.forward(
            sender_id=10,
            sender_role="faculty",
            receiver_id=20,
            receiver_role="HOD",
            comment="To HOD.",
        )
        # Return 20 -> 10
        ret_mov = file_obj.return_file(
            sender_id=20,
            sender_role="HOD",
            receiver_id=10,
            receiver_role="faculty",
            comment="Please revise section 3 before submission.",
        )
        assert ret_mov.movement_type == MovementType.RETURN
        assert file_obj.current_holder_id == 10
        assert file_obj.state == FileLifecycleState.CIRCULATED

    def test_bw_fts_04_archive_completed_circulated_file(self):
        """BW-FTS-04: Owner archives completed file; state becomes terminal ARCHIVED."""
        file_obj = FileComposite.create_new_draft(
            subject="Curriculum Revision",
            description="Syllabus updates",
            creator_id=10,
            creator_role="faculty",
            initial_comment="Proposed revised syllabus.",
        )
        file_obj.forward(
            sender_id=10,
            sender_role="faculty",
            receiver_id=20,
            receiver_role="Dean Academic",
            comment="For Dean approval.",
        )
        # File returned or processed back
        file_obj.return_file(
            sender_id=20,
            sender_role="Dean Academic",
            receiver_id=10,
            receiver_role="faculty",
            comment="Approved. Completed.",
        )
        # Owner (10) archives the completed file
        file_obj.archive(user_id=10)
        assert file_obj.state == FileLifecycleState.ARCHIVED

        # Any subsequent forward or modification is blocked (BR-FTS-012)
        with pytest.raises(FileArchivedError):
            file_obj.forward(
                sender_id=10,
                sender_role="faculty",
                receiver_id=20,
                receiver_role="Dean Academic",
                comment="Attempting forward on archived file.",
            )

    def test_bw_fts_05_prepare_and_circulate_zero_draft_edit(self):
        """BW-FTS-05: Create draft and immediately circulate without draft edit."""
        file_obj = FileComposite.create_new_draft(
            subject="Quick Leave Notice",
            description="On-duty leave",
            creator_id=10,
            creator_role="staff",
            initial_comment="On duty leave application.",
        )
        assert file_obj.state == FileLifecycleState.DRAFT
        file_obj.forward(
            sender_id=10,
            sender_role="staff",
            receiver_id=15,
            receiver_role="Registrar",
            comment="Submitted.",
        )
        assert file_obj.state == FileLifecycleState.CIRCULATED
        assert file_obj.current_holder_id == 15

    def test_bw_fts_06_prepare_and_circulate_one_draft_edit(self):
        """BW-FTS-06: Create draft, edit once, then circulate."""
        file_obj = FileComposite.create_new_draft(
            subject="Draft Title",
            description="Draft Desc",
            creator_id=10,
            creator_role="faculty",
            initial_comment="Initial comment.",
        )
        file_obj.edit_draft(
            actor_id=10,
            subject="Final Title",
            description="Final Desc",
            new_comment="Refined comment.",
        )
        file_obj.forward(
            sender_id=10,
            sender_role="faculty",
            receiver_id=25,
            receiver_role="HOD",
            comment="Sending finalized file.",
        )
        assert file_obj.subject == "Final Title"
        assert file_obj.state == FileLifecycleState.CIRCULATED

    def test_bw_fts_07_create_and_discard_zero_draft_edit(self):
        """BW-FTS-07: Create draft and discard without edit."""
        file_obj = FileComposite.create_new_draft(
            subject="Accidental Draft",
            description="Mistaken entry",
            creator_id=10,
            creator_role="faculty",
            initial_comment="Mistake.",
        )
        assert file_obj.state == FileLifecycleState.DRAFT
        file_obj.discard_draft(actor_id=10)

    def test_bw_fts_08_edit_once_and_discard_draft(self):
        """BW-FTS-08: Create draft, edit once, then discard."""
        file_obj = FileComposite.create_new_draft(
            subject="Draft",
            description="Desc",
            creator_id=10,
            creator_role="faculty",
            initial_comment="Drafting.",
        )
        file_obj.edit_draft(
            actor_id=10,
            subject="Edited Draft",
        )
        file_obj.discard_draft(actor_id=10)


class TestCompositeWorkflows:
    def test_cw_fts_01_collaborative_file_circulation_and_completion(self):
        """CW-FTS-01: End-to-end multi-step file circulation, returns, and archival."""
        # 1. Creator creates file and circulates to Reviewer 1 (BW-FTS-05)
        file_obj = FileComposite.create_new_draft(
            subject="Sponsored Project Proposal",
            description="Research Grant",
            creator_id=100,
            creator_role="faculty",
            initial_comment="Please endorse our research project.",
            attachments=[AttachmentInfo(file_name="proposal.pdf", file_path="/docs/prop.pdf")],
        )
        file_obj.forward(
            sender_id=100,
            sender_role="faculty",
            receiver_id=200,
            receiver_role="HOD",
            comment="Submitting to HOD.",
        )

        # 2. HOD forwards onward to Dean (BW-FTS-02)
        file_obj.forward(
            sender_id=200,
            sender_role="HOD",
            receiver_id=300,
            receiver_role="Dean R&D",
            comment="Strongly endorsed.",
        )

        # 3. Dean returns to HOD for clarification (BW-FTS-03)
        file_obj.return_file(
            sender_id=300,
            sender_role="Dean R&D",
            receiver_id=200,
            receiver_role="HOD",
            comment="Verify equipment quotes.",
        )

        # 4. HOD forwards back to Dean with revised comment
        file_obj.forward(
            sender_id=200,
            sender_role="HOD",
            receiver_id=300,
            receiver_role="Dean R&D",
            comment="Quotes verified and attached.",
        )

        # 5. Dean returns to HOD (BW-FTS-03), HOD forwards back to Creator/Owner (BW-FTS-01)
        file_obj.return_file(
            sender_id=300,
            sender_role="Dean R&D",
            receiver_id=200,
            receiver_role="HOD",
            comment="Approved.",
        )
        file_obj.forward(
            sender_id=200,
            sender_role="HOD",
            receiver_id=100,
            receiver_role="faculty",
            comment="Sanctioned. Process complete.",
        )

        # 6. Owner archives completed file (BW-FTS-04)
        file_obj.archive(user_id=100)
        assert file_obj.state == FileLifecycleState.ARCHIVED

        # Verify auditability / association trace
        associated = file_obj.get_associated_user_ids()
        assert set(associated) == {100, 200, 300}
        assert len(file_obj.movements) == 6
        assert len(file_obj.comments) == 7  # 1 initial + 6 movements

    def test_cw_fts_02_new_file_preparation_and_initial_outcome(self):
        """CW-FTS-02: Branching workflow between draft edit, discard, and circulation."""
        # Branch A: Create, edit, and discard
        f_discard = FileComposite.create_new_draft(
            subject="Test Draft A",
            description="Desc",
            creator_id=10,
            creator_role="faculty",
            initial_comment="Drafting.",
        )
        f_discard.edit_draft(actor_id=10, subject="Updated Draft A")
        f_discard.discard_draft(actor_id=10)

        # Branch B: Create, edit, and circulate
        f_circulate = FileComposite.create_new_draft(
            subject="Test Draft B",
            description="Desc",
            creator_id=10,
            creator_role="faculty",
            initial_comment="Drafting B.",
        )
        f_circulate.edit_draft(actor_id=10, subject="Finalized Draft B")
        f_circulate.forward(
            sender_id=10,
            sender_role="faculty",
            receiver_id=20,
            receiver_role="staff",
            comment="Circulated.",
        )
        assert f_circulate.state == FileLifecycleState.CIRCULATED

        # In circulation, discard is prohibited
        with pytest.raises(DraftBoundaryViolationError):
            f_circulate.discard_draft(actor_id=10)
