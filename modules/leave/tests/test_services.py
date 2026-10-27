from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from core.api.exceptions import ConflictError
from modules.leave.services import requests as service


class Actor:
    user_id = 1001

    def has_permission(self, permission):
        return permission == service.P_CREATE


@pytest.mark.parametrize("kwargs", [
    {"cl_half": "invalid"},
    {"station_leave": True, "station_leave_details": "   "},
    {"reason": "   "},
])
def test_service_rejects_invalid_write_data_before_persistence(kwargs):
    values = {
        "actor": Actor(), "category": "cl", "starts_on": date(2026, 10, 12),
        "ends_on": date(2026, 10, 12), "cl_half": "full", "reason": "Medical",
    }
    values.update(kwargs)
    with pytest.raises(ConflictError) as raised:
        service.create(**values)
    assert raised.value.code == "leave_validation_failed"


def test_postgres_overlap_check_uses_transaction_scoped_advisory_lock():
    cursor = MagicMock()
    connection = MagicMock(vendor="postgresql")
    connection.cursor.return_value.__enter__.return_value = cursor
    with patch("modules.leave.services.requests.connection", connection):
        service._lock_employee_requests(user_id=1001)
    cursor.execute.assert_called_once_with(
        "SELECT pg_advisory_xact_lock(%s, %s)", [0x454C4D, 1001],
    )


def test_non_postgres_backend_does_not_issue_an_unsupported_advisory_lock():
    connection = MagicMock(vendor="sqlite")
    with patch("modules.leave.services.requests.connection", connection):
        service._lock_employee_requests(user_id=1001)
    connection.cursor.assert_not_called()
