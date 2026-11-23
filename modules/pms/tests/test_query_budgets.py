"""The same number of queries at 2 rows and at 20, for every list endpoint (Step 5.8)."""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from modules.pms.domain import state_machine as sm
from modules.pms.models import Escalation, LicensingRequest
from modules.pms.tests.conftest import DIRECTOR, approved_with_attorney, make_app, with_cycle

pytestmark = pytest.mark.django_db


def _grow(n: int) -> None:
    for _ in range(n):
        app = make_app(sm.UNDER_REVIEW)
        with_cycle(app, DIRECTOR)
        Escalation.objects.create(kind="missed_review", application=app, subject_id=app.pk)
        LicensingRequest.objects.create(application=app, applicant_user_id=1001,
                                        kind="licensing", summary="s")
        approved_with_attorney()


def _count(actor, path) -> int:
    """Measured after one warm-up call, so the directory's own cache fill is not counted."""
    actor._go()
    actor.client.get(f"/api/v1/pms/{path}")
    with CaptureQueriesContext(connection) as ctx:
        response = actor.client.get(f"/api/v1/pms/{path}")
    assert response.status_code == 200, response.content
    return len(ctx)


@pytest.mark.parametrize(("who", "path"), [
    ("applicant", "applications"),
    ("pcc", "applications"),
    ("director", "applications"),
    ("attorney", "applications"),
    ("pcc", "my-work"),
    ("director", "my-work"),
    ("pcc", "deadlines"),
    ("pcc", "escalations"),
    ("pcc", "licensing-requests"),
    ("pcc", "audit"),
    ("pcc", "directors"),
    ("pcc", "attorney-panel"),
    ("pcc", "reports/status"),
    ("pcc", "reports/deadlines"),
    ("pcc", "reports/inventors"),
    ("pcc", "reports/financial"),
    ("pcc", "oversight"),
])
def test_queries_do_not_grow_with_rows(world, who, path):
    actor = world[who]
    _grow(2)
    small = _count(actor, path)
    _grow(18)
    large = _count(actor, path)
    assert large == small, f"{path}: {small} queries for 2 rows, {large} for 20"


def test_application_detail_is_a_fixed_number_of_queries(world):
    app = make_app(sm.UNDER_REVIEW)
    for _ in range(5):
        with_cycle(app, DIRECTOR, status="reassigned")
    with_cycle(app, DIRECTOR)
    assert _count(world["pcc"], f"applications/{app.pk}") <= 30
