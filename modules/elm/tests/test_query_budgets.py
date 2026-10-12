"""List endpoints must not grow queries with rows."""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from modules.elm.models import LeaveRequest
from modules.elm.tests.conftest import EMPLOYEE, FAC, monday

pytestmark = pytest.mark.django_db


def test_my_requests_list_is_flat(as_user, policy):
    for i in range(10):
        LeaveRequest.objects.create(
            user_id=FAC, category="CL", applicant_kind="faculty", start_date=monday(i + 2),
            end_date=monday(i + 2), days=1, purpose="x", status="approved")
    c = as_user(FAC, EMPLOYEE)
    c.get("/api/v1/elm/requests")
    with CaptureQueriesContext(connection) as ctx:
        assert len(c.get("/api/v1/elm/requests").json()["results"]) == 10
    assert len(ctx.captured_queries) <= 4
