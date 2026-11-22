"""Helper utilities for FR tests.

Only a minimal `complaint_factory` is provided.  It creates a complaint
record with the required fields and a default active category.  The
factory does **not** rely on the `UserRef` model – the IAM principal is
handled via the `make_session` helper in the test suite.
"""

import pytest
from django.utils import timezone

from modules.complaints.models import Complaint, ComplaintCategory
from modules.complaints.services.complaints import (
    _generate_complaint_id,
    _calculate_sla_deadline,
)


@pytest.fixture
def complaint_factory(db):
    """Create a complaint with sensible defaults.

    The fixture returns a callable ``_make(**overrides)`` that merges the
    provided ``overrides`` with the defaults before calling
    ``Complaint.objects.create``.
    """

    def _make(**overrides):
        # Ensure there is an active category – the tests need a valid FK.
        category, _ = ComplaintCategory.objects.get_or_create(
            name="Electrical",
            defaults={"description": "Electrical issues", "default_sla_hours": 48, "is_active": True},
        )
        # Basic required fields for a complaint.
        defaults = {
            "complaint_id": _generate_complaint_id(),
            "complainant_user_id": 1,  # placeholder – real principal supplied via IAM session
            "category": category,
            "location": "Building A",
            "description": "Test complaint",
            "status": "submitted",
            "priority": "medium",
            "verification_required": "none",
            "sla_deadline": _calculate_sla_deadline("medium", category),
        }
        defaults.update(overrides)
        return Complaint.objects.create(**defaults)

    return _make

