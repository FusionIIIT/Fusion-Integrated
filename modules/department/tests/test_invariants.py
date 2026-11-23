from concurrent.futures import ThreadPoolExecutor
from itertools import product
from threading import Barrier

import pytest
from django.db import connections

from conftest import make_principal
from core.api.exceptions import ConflictError
from fusion_auth.client import UserRef
from modules.department import permissions
from modules.department.api.operations import StockRequestSerializer
from modules.department.api.urls import urlpatterns
from modules.department.domain import (
    FEEDBACK_TRANSITIONS,
    OFFICIAL_TRANSITIONS,
    STOCK_TRANSITIONS,
)
from modules.department.models import Notice, StockItem, StockMovement, StockRequest
from modules.department.registry import NAV_ITEMS, PERMISSIONS, ROLE_GRANTS
from modules.department.selectors import stock_requests_for
from modules.department.services import _next_state, advance_stock_request


@pytest.mark.parametrize("transitions", [
    STOCK_TRANSITIONS, FEEDBACK_TRANSITIONS, OFFICIAL_TRANSITIONS,
])
def test_every_state_action_pair(transitions):
    """BR-DEPT-007, BR-DEPT-013, BR-DEPT-017, BR-DEPT-018: terminal states refuse actions."""
    states = {state for state, _, _ in transitions} | set(transitions.values())
    actions = {action for _, action, _ in transitions}
    for state, action, lane in product(states | {"unknown"}, actions, ("admin", "hod", "faculty")):
        key = state, action, lane
        if key in transitions:
            assert _next_state(transitions, *key) == transitions[key]
        else:
            with pytest.raises(ConflictError):
                _next_state(transitions, *key)


def test_permission_strings_do_not_drift():
    registered = {code for code, _ in PERMISSIONS}
    declared = {value for name, value in vars(permissions).items() if name.isupper()}
    assert declared == registered
    assert all(set(grants) <= registered for grants in ROLE_GRANTS.values())
    assert all(item["required_permission"] in registered for item in NAV_ITEMS)
    for pattern in urlpatterns:
        view = pattern.callback.cls
        for method, attribute in [("get", "read_permission"), ("post", "write_permission"),
                                  ("put", "write_permission")]:
            if hasattr(view, method):
                required = getattr(view, attribute)
                assert set(required if isinstance(required, tuple) else [required]) <= registered


@pytest.mark.django_db
def test_stock_request_query_budget_is_constant(stub_iam, django_assert_num_queries):
    actor = make_principal(kind="faculty", active_role="HOD (CSE)")
    stub_iam(users={actor.user_id: UserRef(actor.user_id, "hod", "HOD", "faculty", department="CSE")})
    for size in (2, 20):
        for i in range(StockRequest.objects.count(), size):
            item = StockItem.objects.create(department="CSE", name=f"Item {i}", quantity=10)
            StockRequest.objects.create(item=item, user_id=1, quantity=1)
        with django_assert_num_queries(1):
            rows = StockRequestSerializer(stock_requests_for(actor), many=True).data
        assert len(rows) == size
        assert all(row["item_name"].startswith("Item ") for row in rows)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("same_request", [True, False])
def test_concurrent_issuance_never_duplicates_or_overdraws(stub_iam, same_request):
    """BR-DEPT-007, BR-DEPT-015, BR-DEPT-016; BW-DEPT-01: issue once, retain audit."""
    actor = make_principal(kind="staff", active_role="deptadmin_cse", modules=["department"],
                           permissions=[permissions.ISSUE_STOCK])
    stub_iam(users={actor.user_id: UserRef(actor.user_id, "admin", "Admin", "staff", department="CSE")})
    item = StockItem.objects.create(department="CSE", name="Last cable", quantity=1)
    first = StockRequest.objects.create(item=item, user_id=11, quantity=1, status="approved")
    second = first if same_request else StockRequest.objects.create(
        item=item, user_id=12, quantity=1, status="approved",
    )
    ready = Barrier(2, timeout=10)

    def issue(request_id):
        try:
            ready.wait()
            advance_stock_request(actor=actor, request_id=request_id, action="issue")
        except ConflictError:
            return "refused"
        else:
            return "issued"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(issue, [first.pk, second.pk])) == ["issued", "refused"]
    item.refresh_from_db()
    assert item.quantity == 0
    assert StockMovement.objects.get().delta == -1
    assert StockRequest.objects.filter(status="issued").count() == 1
    assert Notice.objects.count() == 1


@pytest.mark.django_db
def test_all_department_lists_keep_a_constant_request_query_budget(stub_iam, django_assert_num_queries):
    """Two page sizes exercise role filtering, pagination and serialization together."""
    from datetime import time

    from django.urls import reverse
    from rest_framework.test import APIClient

    from conftest import make_session
    from modules.department.models import (
        Announcement,
        DepartmentDetails,
        DepartmentProposal,
        Feedback,
        LabResource,
        TimetableSlot,
    )

    details = DepartmentDetails.objects.create(department="CSE")
    endpoints = {
        "department-announcements": "faculty",
        "department-managed-announcements": "HOD (CSE)",
        "department-stock-requests": "HOD (CSE)",
        "department-inventory": "faculty",
        "department-feedback": "deptadmin_cse",
        "department-notices": "deptadmin_cse",
        "department-labs": "faculty",
        "department-timetable": "deptadmin_cse",
        "department-proposals": "deptadmin_cse",
    }
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token query-budget")
    for i in range(20):
        Announcement.objects.create(department="CSE", content=f"Seminar {i}")
        item = StockItem.objects.create(department="CSE", name=f"Item {i}", quantity=10)
        StockRequest.objects.create(item=item, user_id=12, quantity=1)
        Feedback.objects.create(department="CSE", user_id=12, content=f"Feedback {i}")
        Notice.objects.create(department="CSE", audience="admin", message=f"Notice {i}")
        LabResource.objects.create(department="CSE", name=f"Lab {i}", details="Lab resources")
        TimetableSlot.objects.create(department="CSE", term=f"Term {i}", day=1, starts_at=time(10),
                                     ends_at=time(11), programme="BTech", batch_year=2025,
                                     room="R", instructor_id=12, title="Algorithms", kind="class")
        DepartmentProposal.objects.create(department=details, field="official_name", value=f"Name {i}",
                                          proposed_by_id=11, status="approved")
        if i + 1 not in (2, 20):
            continue
        for name, role in endpoints.items():
            session = make_session(user_id=11, kind="faculty", roles=[role], active_role=role,
                                   modules=["department"], permissions=ROLE_GRANTS[role])
            stub_iam(session=session, users={11: UserRef(11, "instructor", "Instructor", "faculty",
                                                         department="CSE")})
            with django_assert_num_queries(1):
                response = client.get(reverse(name), {"limit": 20})
            assert response.status_code == 200, name
            assert len(response.json()["results"]) == i + 1, name
