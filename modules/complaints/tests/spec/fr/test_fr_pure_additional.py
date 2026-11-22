"""Additional database-free checks for CMS mandatory submission fields.

Partial test supplement, not a replacement for the frozen FR test design.
"""

import pytest

from modules.complaints.domain.submission import InvalidSubmission, validate_submission


@pytest.mark.parametrize(
    ("category", "description"),
    [
        ("Facilities", "Ceiling leak"),
        ("IT", "Network unavailable"),
        ("Hostel", "Water supply interrupted"),
    ],
)
def test_cfr_cms_001_valid_required_fields(category, description):
    """CFR-CMS-001: valid required category and description are accepted."""
    result = validate_submission(category=category, description=description)
    assert result == (category, description)


@pytest.mark.parametrize(
    ("category", "description"),
    [
        ("", "Leak"),
        ("Facilities", ""),
        ("", ""),
        (None, "Leak"),
        ("Facilities", None),
        (" \t ", "Leak"),
        ("Facilities", "\n \t"),
    ],
)
def test_cfr_cms_001_incomplete_required_fields_refused(category, description):
    """CFR-CMS-001: missing mandatory submission fields are refused."""
    with pytest.raises(InvalidSubmission):
        validate_submission(category=category, description=description)
