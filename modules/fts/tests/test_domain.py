"""Tests for pure domain validation rules and entities in FTS."""
import pytest

from modules.fts.domain.entities import (
    validate_employee_operational_actor,
    validate_mandatory_comment,
    validate_owner_archival,
    validate_recipient,
)
from modules.fts.domain.errors import (
    InvalidRecipientError,
    MandatoryCommentMissingError,
    OnlyOwnerMayArchiveError,
    SystemAdminOperationalActionProhibitedError,
)


def test_mandatory_comment_validation_accepts_valid_string():
    assert validate_mandatory_comment("Valid comment text.") == "Valid comment text."


def test_mandatory_comment_validation_rejects_empty_or_whitespace():
    with pytest.raises(MandatoryCommentMissingError):
        validate_mandatory_comment("")
    with pytest.raises(MandatoryCommentMissingError):
        validate_mandatory_comment("   \n\t  ")
    with pytest.raises(MandatoryCommentMissingError):
        validate_mandatory_comment(None)


def test_recipient_validation_accepts_positive_id():
    assert validate_recipient(202) == 202


def test_recipient_validation_rejects_missing_or_non_positive():
    with pytest.raises(InvalidRecipientError):
        validate_recipient(None)
    with pytest.raises(InvalidRecipientError):
        validate_recipient(0)
    with pytest.raises(InvalidRecipientError):
        validate_recipient(-5)


def test_owner_archival_validation_enforces_ownership():
    validate_owner_archival(101, 101)
    with pytest.raises(OnlyOwnerMayArchiveError):
        validate_owner_archival(101, 102)


def test_employee_operational_actor_validation():
    validate_employee_operational_actor("faculty", False)
    validate_employee_operational_actor("staff", False)

    with pytest.raises(SystemAdminOperationalActionProhibitedError):
        validate_employee_operational_actor("staff", True)

    with pytest.raises(SystemAdminOperationalActionProhibitedError):
        validate_employee_operational_actor("student", False)
