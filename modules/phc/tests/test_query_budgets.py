"""List endpoints cost the same number of queries at 2 rows as at 20."""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from modules.phc.models import (
    DoctorSchedule,
    LowStockAlert,
    ReimbursementClaim,
    Requisition,
    ScheduleSlot,
    StockAdjustment,
)
from modules.phc.tests.factories import (
    AUTHORITY_ID,
    EMPLOYEE_ID,
    PHC_STAFF_ID,
    STUDENT_ID,
    client_as,
    item,
    visit_for,
)

pytestmark = pytest.mark.django_db


def _count(client, path):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get(path).status_code == 200
    return len(ctx.captured_queries)


def _schedules(n):
    for i in range(n):
        s = DoctorSchedule.objects.create(doctor_name=f"Dr {i}", is_published=True,
                                          published_at=timezone.now(),
                                          created_by_user_id=PHC_STAFF_ID)
        ScheduleSlot.objects.create(schedule=s, day_of_week=i % 7, start_time="09:00",
                                    end_time="10:00")


def _visits(n, patient=STUDENT_ID):
    for _ in range(n):
        visit_for(patient)


def _claims(n):
    for _ in range(n):
        visit = visit_for(EMPLOYEE_ID)
        ReimbursementClaim.objects.create(user_id=EMPLOYEE_ID,
                                          prescription=visit.prescriptions.get(),
                                          expense_date=timezone.localdate(), amount="1.00",
                                          submitted_at=timezone.now())


def _requisitions(n):
    stock = item(name=f"Item {Requisition.objects.count()}")
    for _ in range(n):
        req = Requisition.objects.create(originator_user_id=PHC_STAFF_ID, purpose="x")
        req.lines.create(item=stock, quantity="1")


def _alerts(n):
    for i in range(n):
        stock = item(name=f"Alert item {LowStockAlert.objects.count()}-{i}", level="1",
                     threshold="5")
        adj = StockAdjustment.objects.create(item=stock, delta="-1", level_after="1",
                                             adjusted_by_user_id=PHC_STAFF_ID)
        LowStockAlert.objects.create(item=stock, adjustment=adj, level="1", threshold="5")


@pytest.mark.parametrize(("role", "uid", "path", "make"), [
    ("student", STUDENT_ID, "/api/v1/phc/schedules", _schedules),
    ("student", STUDENT_ID, "/api/v1/phc/records", _visits),
    ("PHC Staff", PHC_STAFF_ID, "/api/v1/phc/claims", _claims),
    ("Approving Authority", AUTHORITY_ID, "/api/v1/phc/requisitions", _requisitions),
    ("PHC Staff", PHC_STAFF_ID, "/api/v1/phc/inventory/alerts", _alerts),
])
def test_list_query_count_does_not_grow_with_rows(stub_iam, role, uid, path, make):
    client = client_as(stub_iam, role, uid)
    make(2)
    small = _count(client, path)
    make(18)
    assert _count(client, path) == small
    assert small <= 8
