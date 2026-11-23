"""List endpoints cost the same number of queries at 2 rows as at 20."""
import itertools

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from modules.phc.models import (
    AmbulanceLog,
    DoctorSchedule,
    HealthAdvisory,
    LowStockAlert,
    Notification,
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


_names = itertools.count()


def _items(n):
    for _ in range(n):
        item(name=f"Stock {next(_names)}")


def _ambulance(n):
    for i in range(n):
        AmbulanceLog.objects.create(used_at=timezone.now(), patient_name=f"P{i}",
                                    destination="H", recorded_by_user_id=PHC_STAFF_ID)


def _advisories(n):
    for i in range(n):
        HealthAdvisory.objects.create(title=f"A{i}", body="b", published_at=timezone.now(),
                                      published_by_user_id=PHC_STAFF_ID)


def _notifications(n):
    for i in range(n):
        Notification.objects.create(recipient_user_id=EMPLOYEE_ID, kind="claim_status",
                                    message=f"m{i}", resource_type="x", resource_id=i)


def _employee_visits(n):
    _visits(n, patient=EMPLOYEE_ID)


@pytest.mark.parametrize(("role", "uid", "path", "make"), [
    ("PHC Staff", PHC_STAFF_ID, "/api/v1/phc/inventory", _items),
    ("PHC Staff", PHC_STAFF_ID, "/api/v1/phc/ambulance", _ambulance),
    ("student", STUDENT_ID, "/api/v1/phc/advisories", _advisories),
    ("staff", EMPLOYEE_ID, "/api/v1/phc/notifications", _notifications),
    ("staff", EMPLOYEE_ID, "/api/v1/phc/claims/prescriptions", _employee_visits),
    ("PHC Staff", PHC_STAFF_ID, "/api/v1/phc/records", _employee_visits),
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
