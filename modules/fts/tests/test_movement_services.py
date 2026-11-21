"""Unit tests for FTS Movement Services and Selectors (FTS-UC-003, FTS-UC-004).

Validates forwarding, return workflows, chronological movement recording, and comments.
"""

import pytest

from modules.fts.domain.workflow import (
    ACTION_FORWARDED,
    ACTION_RETURNED,
    STATUS_IN_TRANSIT,
    STATUS_RETURNED,
)
from modules.fts.models import FTSComment, FTSFile, FTSMovement
from modules.fts.selectors.movements import (
    get_file_movement_history,
    get_previous_senders_for_file,
)
from modules.fts.services.drafts import create_file_draft
from modules.fts.services.movements import forward_file, return_file


@pytest.mark.django_db
class TestMovementServices:
    """Tests for forward_file and return_file workflows."""

    def test_forward_file_success(self):
        # 1. Create a draft file
        draft = create_file_draft(
            creator_id="emp_01",
            creator_role="Assistant Professor",
            subject="Equipment Purchase Request",
            initial_comment="Please approve lab equipment purchase.",
        )

        # 2. Forward to HOD
        result = forward_file(
            file_id=draft["file_id"],
            sender_id="emp_01",
            sender_role="Assistant Professor",
            receiver_id="hod_01",
            receiver_role="Head of Department",
            comment="Forwarding for HOD recommendation.",
        )

        assert result["new_status"] == STATUS_IN_TRANSIT
        assert result["current_holder_id"] == "hod_01"

        # Verify DB state
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert file_obj.status == STATUS_IN_TRANSIT
        assert file_obj.is_draft is False
        assert file_obj.current_holder_id == "hod_01"

        # Verify movements table has 2 movements (created, forwarded)
        movements = FTSMovement.objects.filter(file=file_obj).order_by("created_at")
        assert movements.count() == 2
        last_movement = movements.last()
        assert last_movement.action == ACTION_FORWARDED
        assert last_movement.from_user_id == "emp_01"
        assert last_movement.to_user_id == "hod_01"

        # Verify comments
        comment = FTSComment.objects.get(movement=last_movement)
        assert comment.remarks == "Forwarding for HOD recommendation."

    def test_forward_file_non_holder_fails(self):
        draft = create_file_draft(
            creator_id="emp_01",
            creator_role="Staff",
            subject="Budget Request",
            initial_comment="Need funds",
        )

        with pytest.raises(PermissionError, match="Only the current custodian"):
            forward_file(
                file_id=draft["file_id"],
                sender_id="emp_02",  # Not the current holder
                sender_role="Staff",
                receiver_id="emp_03",
                receiver_role="Director",
                comment="Sneaky forward",
            )

    def test_return_file_success(self):
        # 1. Create draft and forward emp_01 -> hod_01
        draft = create_file_draft(
            creator_id="emp_01",
            creator_role="Staff",
            subject="Travel Allowance",
            initial_comment="Claiming TA",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_01",
            sender_role="Staff",
            receiver_id="hod_01",
            receiver_role="HOD",
            comment="Submitted for approval",
        )

        # 2. HOD returns to emp_01 for correction
        return_result = return_file(
            file_id=draft["file_id"],
            sender_id="hod_01",
            sender_role="HOD",
            comment="Receipts missing. Please re-attach and resubmit.",
        )

        assert return_result["new_status"] == STATUS_RETURNED
        assert return_result["returned_to_id"] == "emp_01"

        # Verify DB
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert file_obj.status == STATUS_RETURNED
        assert file_obj.current_holder_id == "emp_01"

        # Verify movement history
        history = get_file_movement_history(draft["file_id"])
        assert len(history) == 3  # created, forwarded, returned
        assert history[2]["action"] == ACTION_RETURNED
        assert (
            history[2]["comments"][0]["remarks"]
            == "Receipts missing. Please re-attach and resubmit."
        )

    def test_return_file_without_history_fails(self):
        draft = create_file_draft(
            creator_id="emp_01",
            creator_role="Staff",
            subject="Unsent File",
            initial_comment="Staying draft",
        )

        with pytest.raises(PermissionError, match="Draft files cannot be returned"):
            return_file(
                file_id=draft["file_id"],
                sender_id="emp_01",
                sender_role="Staff",
                comment="Trying to return draft",
            )


@pytest.mark.django_db
class TestMovementSelectors:
    """Tests for get_file_movement_history and get_previous_senders_for_file."""

    def test_previous_senders_extraction(self):
        draft = create_file_draft(
            creator_id="emp_01",
            creator_role="Staff",
            subject="Circular Movement",
            initial_comment="Start",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_01",
            sender_role="Staff",
            receiver_id="emp_02",
            receiver_role="HOD",
            comment="Forward 1",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_02",
            sender_role="HOD",
            receiver_id="emp_03",
            receiver_role="Dean",
            comment="Forward 2",
        )

        senders = get_previous_senders_for_file(draft["file_id"])
        assert "emp_01" in senders
        assert "emp_02" in senders
        assert "emp_03" not in senders  # emp_03 hasn't sent yet
