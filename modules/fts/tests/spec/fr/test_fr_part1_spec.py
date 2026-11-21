"""Specification-based tests for Functional Requirements (FR) strategy - Part 1.

Implements test cases FR-001 through FR-044 from docs/07-fts/spec-tests/FR_DESIGN.json.
"""

import pytest

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
class TestFunctionalRequirementsPart1:
    """Executable test suite for FR-001 through FR-044."""

    def test_fr_001_cfr_fts_001_lifecycle_preservation(self):
        """[FR-001] CFR-FTS-001 lifecycle-preservation.

        Verify persistent composite record whose contents and trace are preserved.
        """
        draft = create_file_draft(
            creator_id="emp_fr1",
            creator_role="Faculty",
            subject="FR-001 Lifecycle Preservation File",
            initial_comment="Initial remark",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        FTSAttachment.objects.create(
            file=file_obj,
            file_name="paper.pdf",
            file_url="https://example.com/paper.pdf",
            uploaded_by_id="emp_fr1",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr1",
            sender_role="Faculty",
            receiver_id="emp_fr1_b",
            receiver_role="HOD",
            comment="Forwarded to HOD",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_fr1_b",
            sender_role="HOD",
            comment="Returned to faculty",
        )
        archive_file(
            file_id=draft["file_id"],
            user_id="emp_fr1",
            user_role="Faculty",
            remarks="Completed lifecycle",
        )
        history = get_file_movement_history(file_id=draft["file_id"])
        assert len(history) == 4
        refreshed = FTSFile.objects.get(id=draft["file_id"])
        assert refreshed.status == STATUS_ARCHIVED
        assert refreshed.comments.count() == 4
        assert refreshed.attachments.count() == 1

    def test_fr_002_afr_fts_001_composite_structure(self):
        """[FR-002] AFR-FTS-001 composite-structure.

        Verify file treated as composite of mandatory comment and optional attachments.
        """
        draft = create_file_draft(
            creator_id="emp_fr2",
            creator_role="Staff",
            subject="FR-002 Composite File",
            initial_comment="Opening mandatory comment",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        att = FTSAttachment.objects.create(
            file=file_obj,
            file_name="annexure.pdf",
            file_url="https://example.com/annexure.pdf",
            uploaded_by_id="emp_fr2",
        )
        assert file_obj.comments.filter(remarks="Opening mandatory comment").exists()
        assert file_obj.attachments.filter(id=att.id).exists()

    def test_fr_003_afr_fts_002_post_circulation_retention(self):
        """[FR-003] AFR-FTS-002 post-circulation-retention.

        Verify circulated files and accumulated contents are preserved without deletion.
        """
        draft = create_file_draft(
            creator_id="emp_fr3_a",
            creator_role="Faculty",
            subject="FR-003 Retention File",
            initial_comment="Initial remark",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr3_a",
            sender_role="Faculty",
            receiver_id="emp_fr3_b",
            receiver_role="HOD",
            comment="Circulated",
        )
        with pytest.raises(PermissionError):
            discard_file_draft(file_id=draft["file_id"], user_id="emp_fr3_a")
        assert FTSFile.objects.filter(id=draft["file_id"]).exists()

    def test_fr_004_afr_fts_003_owner_archival_vs_deletion(self):
        """[FR-004] AFR-FTS-003 owner-archival-vs-deletion.

        Verify file owner can archive a completed circulated file instead of deleting it.
        """
        draft = create_file_draft(
            creator_id="emp_fr4",
            creator_role="Faculty",
            subject="FR-004 Owner Archival File",
            initial_comment="Initial remark",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr4",
            sender_role="Faculty",
            receiver_id="emp_fr4_b",
            receiver_role="Dean",
            comment="Circulated",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_fr4_b",
            sender_role="Dean",
            comment="Returned to owner",
        )
        res = archive_file(
            file_id=draft["file_id"],
            user_id="emp_fr4",
            user_role="Faculty",
            remarks="Archived by owner",
        )
        assert res["status"] == STATUS_ARCHIVED
        assert FTSFile.objects.filter(id=draft["file_id"]).exists()

    def test_fr_005_afr_fts_004_full_traceability(self):
        """[FR-005] AFR-FTS-004 full-traceability.

        Verify complete file movement and audit trace retrieval.
        """
        draft = create_file_draft(
            creator_id="emp_fr5",
            creator_role="Staff",
            subject="FR-005 Traceability File",
            initial_comment="Initial remark",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr5",
            sender_role="Staff",
            receiver_id="emp_fr5_b",
            receiver_role="HOD",
            comment="Step 1",
        )
        history = get_file_movement_history(file_id=draft["file_id"])
        assert len(history) == 2
        assert history[0]["action"] == "created"
        assert history[1]["action"] == "forwarded"

    def test_fr_006_cfr_fts_002_operational_vs_governance_boundary(self):
        """[FR-006] CFR-FTS-002 operational-vs-governance-boundary.

        Verify operational file actions succeed for employees while maintaining governance boundary.
        """
        draft = create_file_draft(
            creator_id="emp_fr6",
            creator_role="Staff",
            subject="FR-006 Operational File",
            initial_comment="Operational remark",
        )
        assert draft["status"] == STATUS_DRAFT
        role_grants = get_role_grants()
        assert "admin" not in role_grants

    def test_fr_007_afr_fts_005_institute_employee_operational_roles(self):
        """[FR-007] AFR-FTS-005 institute-employee-operational-roles.

        Verify Faculty and Staff users can create and forward files.
        """
        role_grants = get_role_grants()
        assert "faculty" in role_grants
        assert "staff" in role_grants
        assert "fts.file.create" in role_grants["faculty"]
        assert "fts.file.review" in role_grants["faculty"]
        assert "fts.file.create" in role_grants["staff"]
        assert "fts.file.review" in role_grants["staff"]

    def test_fr_008_afr_fts_006_sysadmin_role_administration(self):
        """[FR-008] AFR-FTS-006 sysadmin-role-administration.

        Verify sysadmin role administration interface.
        """
        pytest.skip("NOT_AUTOMATED: Central IAM role administration interface is external to FTS")

    def test_fr_009_afr_fts_007_sysadmin_usage_monitoring(self):
        """[FR-009] AFR-FTS-007 sysadmin-usage-monitoring.

        Verify sysadmin usage monitoring statistics interface.
        """
        pytest.skip("NOT_AUTOMATED: System admin usage monitoring interface is not implemented in FTS")

    def test_fr_010_afr_fts_008_sysadmin_audit_oversight(self):
        """[FR-010] AFR-FTS-008 sysadmin-audit-oversight.

        Verify sysadmin security and audit log views interface.
        """
        pytest.skip("NOT_AUTOMATED: System admin audit oversight view is not implemented in FTS")

    def test_fr_011_afr_fts_009_sysadmin_operational_action_prohibited(self):
        """[FR-011] AFR-FTS-009 sysadmin-operational-action-prohibited.

        Verify operational file actions are blocked for System Admin.
        """
        role_grants = get_role_grants()
        assert "system_admin" not in role_grants
        assert "admin" not in role_grants

    def test_fr_012_afr_fts_010_multi_role_selection(self):
        """[FR-012] AFR-FTS-010 multi-role-selection.

        Verify operations evaluated under active role context.
        """
        draft = create_file_draft(
            creator_id="emp_fr12",
            creator_role="Warden",
            subject="FR-012 Multi-Role File",
            initial_comment="Hostel maintenance request",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert file_obj.creator_role == "Warden"

    def test_fr_013_cfr_fts_003_file_creation_service(self):
        """[FR-013] CFR-FTS-003 file-creation-service.

        Verify file creation service provisions new draft file.
        """
        res = create_file_draft(
            creator_id="emp_fr13",
            creator_role="Staff",
            subject="FR-013 Creation Service",
            initial_comment="Creating file",
        )
        assert res["file_id"] is not None
        assert res["status"] == STATUS_DRAFT

    def test_fr_014_afr_fts_011_create_file_assigned_role(self):
        """[FR-014] AFR-FTS-011 create-file-assigned-role.

        Verify file creation captures creator's active assigned role.
        """
        res = create_file_draft(
            creator_id="emp_fr14",
            creator_role="Assistant Registrar",
            subject="FR-014 Role File",
            initial_comment="Initial remark",
        )
        file_obj = FTSFile.objects.get(id=res["file_id"])
        assert file_obj.creator_role == "Assistant Registrar"

    def test_fr_015_afr_fts_012_mandatory_initial_comment_present(self):
        """[FR-015] AFR-FTS-012 mandatory-initial-comment-present.

        Verify file creation accepted when non-empty initial comment is present.
        """
        res = create_file_draft(
            creator_id="emp_fr15",
            creator_role="Staff",
            subject="FR-015 Mandatory Comment Present",
            initial_comment="Substantive initial comment",
        )
        assert res["file_id"] is not None

    def test_fr_016_afr_fts_012_mandatory_initial_comment_missing(self):
        """[FR-016] AFR-FTS-012 mandatory-initial-comment-missing.

        Verify file creation rejected when initial comment is missing.
        """
        with pytest.raises(ValueError, match="Initial comment is mandatory"):
            create_file_draft(
                creator_id="emp_fr16",
                creator_role="Staff",
                subject="FR-016 Missing Comment",
                initial_comment="",
            )

    def test_fr_017_afr_fts_013_optional_attachments_during_creation(self):
        """[FR-017] AFR-FTS-013 optional-attachments-during-creation.

        Verify optional attachments can be attached during file creation.
        """
        draft = create_file_draft(
            creator_id="emp_fr17",
            creator_role="Faculty",
            subject="FR-017 Optional Attachment File",
            initial_comment="Initial remark",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        att = FTSAttachment.objects.create(
            file=file_obj,
            file_name="annex_1.pdf",
            file_url="https://example.com/annex_1.pdf",
            uploaded_by_id="emp_fr17",
        )
        assert file_obj.attachments.filter(id=att.id).exists()

    def test_fr_018_cfr_fts_004_draft_lifecycle_and_circulation(self):
        """[FR-018] CFR-FTS-004 draft-lifecycle-and-circulation.

        Verify draft file can be saved, edited, and circulated.
        """
        draft = create_file_draft(
            creator_id="emp_fr18",
            creator_role="Staff",
            subject="FR-018 Lifecycle File",
            initial_comment="Initial remark",
        )
        update_file_draft(
            file_id=draft["file_id"],
            user_id="emp_fr18",
            subject="FR-018 Updated Subject",
        )
        fwd = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr18",
            sender_role="Staff",
            receiver_id="emp_fr18_b",
            receiver_role="HOD",
            comment="Circulated",
        )
        assert fwd["new_status"] == STATUS_IN_TRANSIT

    def test_fr_019_afr_fts_014_draft_save(self):
        """[FR-019] AFR-FTS-014 draft-save.

        Verify draft saved in pre-circulation state without circulating.
        """
        draft = create_file_draft(
            creator_id="emp_fr19",
            creator_role="Faculty",
            subject="FR-019 Save Draft File",
            initial_comment="Initial remark",
        )
        assert draft["status"] == STATUS_DRAFT
        assert draft["is_draft"] is True

    def test_fr_020_afr_fts_015_draft_edit(self):
        """[FR-020] AFR-FTS-015 draft-edit.

        Verify creator can edit draft content prior to circulation.
        """
        draft = create_file_draft(
            creator_id="emp_fr20",
            creator_role="Faculty",
            subject="FR-020 Before Edit",
            initial_comment="Initial remark",
        )
        update_file_draft(
            file_id=draft["file_id"],
            user_id="emp_fr20",
            subject="FR-020 After Edit",
            priority="high",
        )
        refreshed = FTSFile.objects.get(id=draft["file_id"])
        assert refreshed.subject == "FR-020 After Edit"
        assert refreshed.priority == "high"

    def test_fr_021_afr_fts_016_draft_discard(self):
        """[FR-021] AFR-FTS-016 draft-discard.

        Verify draft discard permanently removes pre-circulation draft.
        """
        draft = create_file_draft(
            creator_id="emp_fr21",
            creator_role="Staff",
            subject="FR-021 Discard Draft",
            initial_comment="Initial remark",
        )
        discard_file_draft(file_id=draft["file_id"], user_id="emp_fr21")
        assert not FTSFile.objects.filter(id=draft["file_id"]).exists()

    def test_fr_022_afr_fts_017_prevent_circulated_file_deletion(self):
        """[FR-022] AFR-FTS-017 prevent-circulated-file-deletion.

        Verify circulated file cannot be deleted.
        """
        draft = create_file_draft(
            creator_id="emp_fr22",
            creator_role="Staff",
            subject="FR-022 Circulated File",
            initial_comment="Initial remark",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr22",
            sender_role="Staff",
            receiver_id="emp_fr22_rec",
            receiver_role="HOD",
            comment="Circulated",
        )
        with pytest.raises(PermissionError):
            discard_file_draft(file_id=draft["file_id"], user_id="emp_fr22")

    def test_fr_023_afr_fts_018_transition_to_circulated_state(self):
        """[FR-023] AFR-FTS-018 transition-to-circulated-state.

        Verify draft transitions to in_transit when submitted to recipient.
        """
        draft = create_file_draft(
            creator_id="emp_fr23",
            creator_role="Staff",
            subject="FR-023 State Transition",
            initial_comment="Initial remark",
        )
        res = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr23",
            sender_role="Staff",
            receiver_id="emp_fr23_rec",
            receiver_role="HOD",
            comment="Submitting",
        )
        assert res["new_status"] == STATUS_IN_TRANSIT
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert file_obj.status == STATUS_IN_TRANSIT
        assert file_obj.is_draft is False

    def test_fr_024_afr_fts_019_preserve_accumulated_content_on_submission(self):
        """[FR-024] AFR-FTS-019 preserve-accumulated-content-on-submission.

        Verify comments and attachments preserved when draft transitions to circulated.
        """
        draft = create_file_draft(
            creator_id="emp_fr24",
            creator_role="Staff",
            subject="FR-024 Preserve Content",
            initial_comment="Draft remark to preserve",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        att = FTSAttachment.objects.create(
            file=file_obj,
            file_name="spec.pdf",
            file_url="https://example.com/spec.pdf",
            uploaded_by_id="emp_fr24",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr24",
            sender_role="Staff",
            receiver_id="emp_fr24_rec",
            receiver_role="HOD",
            comment="Circulating",
        )
        refreshed = FTSFile.objects.get(id=draft["file_id"])
        assert refreshed.comments.filter(remarks="Draft remark to preserve").exists()
        assert refreshed.attachments.filter(id=att.id).exists()

    def test_fr_025_cfr_fts_005_file_forwarding_and_return(self):
        """[FR-025] CFR-FTS-005 file-forwarding-and-return.

        Verify forward and return movement actions and chronological recording.
        """
        draft = create_file_draft(
            creator_id="emp_fr25",
            creator_role="Faculty",
            subject="FR-025 Fwd and Ret File",
            initial_comment="Initial remark",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr25",
            sender_role="Faculty",
            receiver_id="emp_fr25_b",
            receiver_role="HOD",
            comment="Forwarded",
        )
        ret = return_file(
            file_id=draft["file_id"],
            sender_id="emp_fr25_b",
            sender_role="HOD",
            comment="Returned",
        )
        assert ret["new_status"] == STATUS_RETURNED
        assert ret["returned_to_id"] == "emp_fr25"

    def test_fr_026_afr_fts_020_send_file_to_employee(self):
        """[FR-026] AFR-FTS-020 send-file-to-employee.

        Verify file transfer records in sender outbox and recipient inbox.
        """
        draft = create_file_draft(
            creator_id="emp_fr26_a",
            creator_role="Staff",
            subject="FR-026 Send File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr26_a",
            sender_role="Staff",
            receiver_id="emp_fr26_b",
            receiver_role="HOD",
            comment="Sending to B",
        )
        outbox_a = get_user_outbox_files(user_id="emp_fr26_a")
        inbox_b = get_user_inbox_files(user_id="emp_fr26_b")
        assert any(item["id"] == draft["file_id"] for item in outbox_a)
        assert any(item["id"] == draft["file_id"] for item in inbox_b)

    def test_fr_027_afr_fts_021_send_regardless_of_receiver_role(self):
        """[FR-027] AFR-FTS-021 send-regardless-of-receiver-role.

        Verify file transfer succeeds across different role categories.
        """
        draft = create_file_draft(
            creator_id="emp_fr27_a",
            creator_role="Staff",
            subject="FR-027 Cross Role File",
            initial_comment="Initial",
        )
        res = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr27_a",
            sender_role="Staff",
            receiver_id="emp_fr27_b",
            receiver_role="Dean",
            comment="Cross-role transfer",
        )
        assert res["current_holder_id"] == "emp_fr27_b"

    def test_fr_028_afr_fts_022_movement_comment_mandatory_forward_positive(self):
        """[FR-028] AFR-FTS-022 movement-comment-mandatory-forward-positive.

        Verify forward succeeds with valid non-empty comment.
        """
        draft = create_file_draft(
            creator_id="emp_fr28_a",
            creator_role="Faculty",
            subject="FR-028 Fwd Comment Pos",
            initial_comment="Initial",
        )
        res = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr28_a",
            sender_role="Faculty",
            receiver_id="emp_fr28_b",
            receiver_role="HOD",
            comment="Substantive forward comment",
        )
        assert res["new_status"] == STATUS_IN_TRANSIT

    def test_fr_029_afr_fts_022_movement_comment_mandatory_forward_negative(self):
        """[FR-029] AFR-FTS-022 movement-comment-mandatory-forward-negative.

        Verify forward rejected when comment is empty.
        """
        draft = create_file_draft(
            creator_id="emp_fr29_a",
            creator_role="Faculty",
            subject="FR-029 Fwd Empty Comment",
            initial_comment="Initial",
        )
        with pytest.raises(PermissionError, match="Movement comment is mandatory"):
            forward_file(
                file_id=draft["file_id"],
                sender_id="emp_fr29_a",
                sender_role="Faculty",
                receiver_id="emp_fr29_b",
                receiver_role="HOD",
                comment="   ",
            )

    def test_fr_030_afr_fts_022_movement_comment_mandatory_return_negative(self):
        """[FR-030] AFR-FTS-022 movement-comment-mandatory-return-negative.

        Verify return rejected when movement comment is empty.
        """
        draft = create_file_draft(
            creator_id="emp_fr30_a",
            creator_role="Staff",
            subject="FR-030 Return Empty Comment",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr30_a",
            sender_role="Staff",
            receiver_id="emp_fr30_b",
            receiver_role="HOD",
            comment="Forwarded",
        )
        with pytest.raises(PermissionError, match="Movement comment is mandatory"):
            return_file(
                file_id=draft["file_id"],
                sender_id="emp_fr30_b",
                sender_role="HOD",
                comment="",
            )

    def test_fr_031_afr_fts_023_optional_attachments_during_movement(self):
        """[FR-031] AFR-FTS-023 optional-attachments-during-movement.

        Verify attachments can be added during movement actions.
        """
        draft = create_file_draft(
            creator_id="emp_fr31_a",
            creator_role="Staff",
            subject="FR-031 Movement Attachment",
            initial_comment="Initial",
        )
        res = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr31_a",
            sender_role="Staff",
            receiver_id="emp_fr31_b",
            receiver_role="HOD",
            comment="Forwarded with attachment",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        att = FTSAttachment.objects.create(
            file=file_obj,
            movement_id=res["movement_id"],
            file_name="fwd_annex.pdf",
            file_url="https://example.com/fwd_annex.pdf",
            uploaded_by_id="emp_fr31_a",
        )
        assert file_obj.attachments.filter(id=att.id).exists()

    def test_fr_032_afr_fts_024_recipient_forward_onward(self):
        """[FR-032] AFR-FTS-024 recipient-forward-onward.

        Verify recipient can forward file onward to another employee.
        """
        draft = create_file_draft(
            creator_id="emp_fr32_a",
            creator_role="Staff",
            subject="FR-032 Onward Forward",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr32_a",
            sender_role="Staff",
            receiver_id="emp_fr32_b",
            receiver_role="HOD",
            comment="A to B",
        )
        res = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr32_b",
            sender_role="HOD",
            receiver_id="emp_fr32_c",
            receiver_role="Dean",
            comment="B to C onward",
        )
        assert res["current_holder_id"] == "emp_fr32_c"

    def test_fr_033_afr_fts_025_recipient_return_to_sender(self):
        """[FR-033] AFR-FTS-025 recipient-return-to-sender.

        Verify recipient can return file to previous sender.
        """
        draft = create_file_draft(
            creator_id="emp_fr33_a",
            creator_role="Staff",
            subject="FR-033 Return File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr33_a",
            sender_role="Staff",
            receiver_id="emp_fr33_b",
            receiver_role="HOD",
            comment="A to B",
        )
        ret = return_file(
            file_id=draft["file_id"],
            sender_id="emp_fr33_b",
            sender_role="HOD",
            comment="B to A return",
        )
        assert ret["new_status"] == STATUS_RETURNED
        assert ret["returned_to_id"] == "emp_fr33_a"

    def test_fr_034_afr_fts_026_chronological_forward_recording(self):
        """[FR-034] AFR-FTS-026 chronological-forward-recording.

        Verify chronological forward movement recording.
        """
        draft = create_file_draft(
            creator_id="emp_fr34_a",
            creator_role="Staff",
            subject="FR-034 Chronological Forward",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr34_a",
            sender_role="Staff",
            receiver_id="emp_fr34_b",
            receiver_role="HOD",
            comment="Forward 1",
        )
        history = get_file_movement_history(file_id=draft["file_id"])
        assert history[-1]["action"] == "forwarded"
        assert history[-1]["to_user_id"] == "emp_fr34_b"

    def test_fr_035_afr_fts_027_chronological_return_recording(self):
        """[FR-035] AFR-FTS-027 chronological-return-recording.

        Verify chronological return movement recording.
        """
        draft = create_file_draft(
            creator_id="emp_fr35_a",
            creator_role="Staff",
            subject="FR-035 Chronological Return",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr35_a",
            sender_role="Staff",
            receiver_id="emp_fr35_b",
            receiver_role="HOD",
            comment="Forwarded",
        )
        return_file(
            file_id=draft["file_id"],
            sender_id="emp_fr35_b",
            sender_role="HOD",
            comment="Returned",
        )
        history = get_file_movement_history(file_id=draft["file_id"])
        assert history[-1]["action"] == "returned"
        assert history[-1]["to_user_id"] == "emp_fr35_a"

    def test_fr_036_afr_fts_028_update_holder_on_movement(self):
        """[FR-036] AFR-FTS-028 update-holder-on-movement.

        Verify current holder updates to designated recipient.
        """
        draft = create_file_draft(
            creator_id="emp_fr36_a",
            creator_role="Faculty",
            subject="FR-036 Update Holder",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr36_a",
            sender_role="Faculty",
            receiver_id="emp_fr36_b",
            receiver_role="Dean",
            comment="Forwarded to Dean",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert file_obj.current_holder_id == "emp_fr36_b"

    def test_fr_037_cfr_fts_006_inbox_outbox_and_file_access(self):
        """[FR-037] CFR-FTS-006 inbox-outbox-and-file-access.

        Verify inbox and outbox views provide access to files.
        """
        draft = create_file_draft(
            creator_id="emp_fr37_a",
            creator_role="Staff",
            subject="FR-037 Inbox Outbox File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr37_a",
            sender_role="Staff",
            receiver_id="emp_fr37_b",
            receiver_role="HOD",
            comment="Passing to HOD",
        )
        inbox = get_user_inbox_files(user_id="emp_fr37_b")
        outbox = get_user_outbox_files(user_id="emp_fr37_a")
        assert any(item["id"] == draft["file_id"] for item in inbox)
        assert any(item["id"] == draft["file_id"] for item in outbox)

    def test_fr_038_afr_fts_029_inbox_listing(self):
        """[FR-038] AFR-FTS-029 inbox-listing.

        Verify inbox lists all files currently in employee's custody.
        """
        draft = create_file_draft(
            creator_id="emp_fr38_a",
            creator_role="Staff",
            subject="FR-038 Inbox Listing File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr38_a",
            sender_role="Staff",
            receiver_id="emp_fr38_b",
            receiver_role="Dean",
            comment="To Dean",
        )
        inbox = get_user_inbox_files(user_id="emp_fr38_b")
        assert any(item["id"] == draft["file_id"] for item in inbox)

    def test_fr_039_afr_fts_030_outbox_listing(self):
        """[FR-039] AFR-FTS-030 outbox-listing.

        Verify outbox lists all files previously circulated by employee.
        """
        draft = create_file_draft(
            creator_id="emp_fr39_a",
            creator_role="Faculty",
            subject="FR-039 Outbox Listing File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr39_a",
            sender_role="Faculty",
            receiver_id="emp_fr39_b",
            receiver_role="Dean",
            comment="Sent to Dean",
        )
        outbox = get_user_outbox_files(user_id="emp_fr39_a")
        assert any(item["id"] == draft["file_id"] for item in outbox)

    def test_fr_040_afr_fts_031_open_file_from_inbox(self):
        """[FR-040] AFR-FTS-031 open-file-from-inbox.

        Verify employee can view details of file selected from inbox.
        """
        draft = create_file_draft(
            creator_id="emp_fr40_a",
            creator_role="Staff",
            subject="FR-040 Open Inbox File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr40_a",
            sender_role="Staff",
            receiver_id="emp_fr40_b",
            receiver_role="HOD",
            comment="Sent",
        )
        inbox = get_user_inbox_files(user_id="emp_fr40_b")
        file_item = next(item for item in inbox if item["id"] == draft["file_id"])
        assert file_item["subject"] == "FR-040 Open Inbox File"

    def test_fr_041_afr_fts_032_open_file_from_outbox(self):
        """[FR-041] AFR-FTS-032 open-file-from-outbox.

        Verify employee can view details of file selected from outbox.
        """
        draft = create_file_draft(
            creator_id="emp_fr41_a",
            creator_role="Staff",
            subject="FR-041 Open Outbox File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr41_a",
            sender_role="Staff",
            receiver_id="emp_fr41_b",
            receiver_role="HOD",
            comment="Sent",
        )
        outbox = get_user_outbox_files(user_id="emp_fr41_a")
        file_item = next(item for item in outbox if item["id"] == draft["file_id"])
        assert file_item["subject"] == "FR-041 Open Outbox File"

    def test_fr_042_afr_fts_033_act_on_file_by_state_and_auth(self):
        """[FR-042] AFR-FTS-033 act-on-file-by-state-and-auth.

        Verify available actions on a file depend on file status and custodian authorization.
        """
        draft = create_file_draft(
            creator_id="emp_fr42_a",
            creator_role="Staff",
            subject="FR-042 State Actions File",
            initial_comment="Initial",
        )
        # In draft state, cannot return
        with pytest.raises(PermissionError):
            return_file(
                file_id=draft["file_id"],
                sender_id="emp_fr42_a",
                sender_role="Staff",
                comment="Cannot return draft",
            )

    def test_fr_043_afr_fts_034_file_accessibility_until_archived(self):
        """[FR-043] AFR-FTS-034 file-accessibility-until-archived.

        Verify file remains accessible throughout entire active lifecycle.
        """
        draft = create_file_draft(
            creator_id="emp_fr43_a",
            creator_role="Staff",
            subject="FR-043 Active Accessibility",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr43_a",
            sender_role="Staff",
            receiver_id="emp_fr43_b",
            receiver_role="HOD",
            comment="Forwarded",
        )
        inbox_b = get_user_inbox_files(user_id="emp_fr43_b")
        assert any(item["id"] == draft["file_id"] for item in inbox_b)

    def test_fr_044_cfr_fts_007_tracking_history_completeness(self):
        """[FR-044] CFR-FTS-007 tracking-history-completeness.

        Verify tracking history provides complete immutable audit log.
        """
        draft = create_file_draft(
            creator_id="emp_fr44",
            creator_role="Faculty",
            subject="FR-044 History Completeness File",
            initial_comment="Initial remark",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_fr44",
            sender_role="Faculty",
            receiver_id="emp_fr44_rec",
            receiver_role="Dean",
            comment="Forwarding",
        )
        history = get_file_movement_history(file_id=draft["file_id"])
        assert len(history) == 2
        assert history[0]["action"] == "created"
        assert history[1]["action"] == "forwarded"
