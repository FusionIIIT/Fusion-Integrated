"""Unit tests for FTS pure Python domain workflow logic.

Zero database, Django, or network dependencies.
"""

import pytest

from modules.fts.domain.workflow import (
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    STATUS_ARCHIVED,
    STATUS_DRAFT,
    STATUS_IN_TRANSIT,
    STATUS_RECEIVED,
    can_archive_file,
    can_edit_draft,
    can_forward_file,
    can_return_file,
    generate_file_uin,
    validate_initial_file_data,
)


class TestInitialFileValidation:
    """Tests for validate_initial_file_data (BR-FTS-003, BR-FTS-004)."""

    def test_valid_file_data(self):
        result = validate_initial_file_data(
            subject="Budget Approval 2024",
            initial_comment="Submitting annual departmental budget.",
            priority=PRIORITY_HIGH,
            category="finance",
        )
        assert result["subject"] == "Budget Approval 2024"
        assert result["initial_comment"] == "Submitting annual departmental budget."
        assert result["priority"] == PRIORITY_HIGH
        assert result["category"] == "finance"

    def test_default_priority_and_category(self):
        result = validate_initial_file_data(
            subject="Equipment Request",
            initial_comment="Need two monitors.",
        )
        assert result["priority"] == PRIORITY_MEDIUM
        assert result["category"] == "general"

    def test_empty_subject_raises_value_error(self):
        with pytest.raises(ValueError, match="File subject cannot be empty"):
            validate_initial_file_data(subject="   ", initial_comment="Valid remark")

    def test_empty_initial_comment_raises_value_error(self):
        with pytest.raises(ValueError, match="Initial comment is mandatory"):
            validate_initial_file_data(subject="Valid subject", initial_comment="  \t  ")

    def test_invalid_priority_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid priority"):
            validate_initial_file_data(
                subject="Test",
                initial_comment="Remark",
                priority="super_urgent",
            )


class TestUINGeneration:
    """Tests for generate_file_uin."""

    def test_standard_uin_generation(self):
        uin = generate_file_uin(prefix="FTS", year=2024, sequence_num=1)
        assert uin == "FTS-2024-0001"

    def test_high_sequence_uin(self):
        uin = generate_file_uin(prefix="acad", year=2025, sequence_num=1420)
        assert uin == "ACAD-2025-1420"

    def test_invalid_sequence_number(self):
        with pytest.raises(ValueError, match="Sequence number must be a positive integer"):
            generate_file_uin(prefix="FTS", year=2024, sequence_num=0)


class TestForwardingValidation:
    """Tests for can_forward_file (BR-FTS-006, BR-FTS-007)."""

    def test_valid_forward(self):
        valid, msg = can_forward_file(
            current_status=STATUS_RECEIVED,
            sender_id="emp_01",
            current_holder_id="emp_01",
            receiver_id="emp_02",
            comment="Forwarded for review.",
        )
        assert valid is True
        assert msg == ""

    def test_cannot_forward_to_self(self):
        valid, msg = can_forward_file(
            current_status=STATUS_RECEIVED,
            sender_id="emp_01",
            current_holder_id="emp_01",
            receiver_id="emp_01",
            comment="Self forward",
        )
        assert valid is False
        assert "Cannot forward a file to yourself" in msg

    def test_non_holder_cannot_forward(self):
        valid, msg = can_forward_file(
            current_status=STATUS_RECEIVED,
            sender_id="emp_02",
            current_holder_id="emp_01",
            receiver_id="emp_03",
            comment="Unauthorized",
        )
        assert valid is False
        assert "Only the current custodian can forward" in msg

    def test_empty_comment_disallowed(self):
        valid, msg = can_forward_file(
            current_status=STATUS_RECEIVED,
            sender_id="emp_01",
            current_holder_id="emp_01",
            receiver_id="emp_02",
            comment="   ",
        )
        assert valid is False
        assert "Movement comment is mandatory" in msg

    def test_archived_file_cannot_be_forwarded(self):
        valid, msg = can_forward_file(
            current_status=STATUS_ARCHIVED,
            sender_id="emp_01",
            current_holder_id="emp_01",
            receiver_id="emp_02",
            comment="Let's reopen",
        )
        assert valid is False
        assert "Archived files are terminal" in msg


class TestReturnValidation:
    """Tests for can_return_file (BR-FTS-007)."""

    def test_valid_return(self):
        valid, msg = can_return_file(
            current_status=STATUS_RECEIVED,
            sender_id="emp_02",
            current_holder_id="emp_02",
            previous_senders=["emp_01"],
            comment="Clarification required.",
        )
        assert valid is True
        assert msg == ""

    def test_return_with_empty_history(self):
        valid, msg = can_return_file(
            current_status=STATUS_RECEIVED,
            sender_id="emp_01",
            current_holder_id="emp_01",
            previous_senders=[],
            comment="Return back",
        )
        assert valid is False
        assert "No previous sender" in msg

    def test_draft_cannot_be_returned(self):
        valid, msg = can_return_file(
            current_status=STATUS_DRAFT,
            sender_id="emp_01",
            current_holder_id="emp_01",
            previous_senders=["emp_00"],
            comment="Returning draft",
        )
        assert valid is False
        assert "Draft files cannot be returned" in msg


class TestArchivalValidation:
    """Tests for can_archive_file (BR-FTS-012)."""

    def test_valid_archive_by_current_holder(self):
        valid, msg = can_archive_file(
            current_status=STATUS_RECEIVED,
            user_id="emp_02",
            creator_id="emp_01",
            current_holder_id="emp_02",
        )
        assert valid is True
        assert msg == ""

    def test_valid_archive_by_creator(self):
        valid, msg = can_archive_file(
            current_status=STATUS_RECEIVED,
            user_id="emp_01",
            creator_id="emp_01",
            current_holder_id="emp_02",
        )
        assert valid is True
        assert msg == ""

    def test_unauthorized_archive(self):
        valid, msg = can_archive_file(
            current_status=STATUS_RECEIVED,
            user_id="emp_03",
            creator_id="emp_01",
            current_holder_id="emp_02",
        )
        assert valid is False
        assert "Only the creator or current holder" in msg

    def test_cannot_archive_draft(self):
        valid, msg = can_archive_file(
            current_status=STATUS_DRAFT,
            user_id="emp_01",
            creator_id="emp_01",
            current_holder_id="emp_01",
        )
        assert valid is False
        assert "Draft files cannot be archived" in msg


class TestDraftEditValidation:
    """Tests for can_edit_draft (BR-FTS-005)."""

    def test_creator_can_edit_draft(self):
        valid, msg = can_edit_draft(
            current_status=STATUS_DRAFT,
            user_id="emp_01",
            creator_id="emp_01",
        )
        assert valid is True
        assert msg == ""

    def test_non_creator_cannot_edit_draft(self):
        valid, msg = can_edit_draft(
            current_status=STATUS_DRAFT,
            user_id="emp_02",
            creator_id="emp_01",
        )
        assert valid is False
        assert "Only the file creator can edit" in msg

    def test_active_file_cannot_be_edited_as_draft(self):
        valid, msg = can_edit_draft(
            current_status=STATUS_IN_TRANSIT,
            user_id="emp_01",
            creator_id="emp_01",
        )
        assert valid is False
        assert "Only files in draft status can be modified" in msg
