"""Both gates separately, scoping as 404, and no one acting outside their step."""
import re
import threading
from datetime import date
from pathlib import Path

import pytest
from django.db import connection

from config.celery import app
from modules.leave import registry
from modules.leave.domain.categories import Category
from modules.leave.models import LeaveRequest
from modules.leave.services import requests as leave
from modules.leave.tests.conftest import (
    ADMIN,
    EMPLOYEE,
    EST,
    HEAD,
    OTHER,
    SANCTION,
    STAFF,
    SUB,
    USERS,
)
from modules.leave.tests.test_workflow import act, apply

pytestmark = pytest.mark.django_db

DECLARED = {code for code, _ in registry.PERMISSIONS}


def test_codes_used_by_tests_and_views_are_declared():
    used = set(EMPLOYEE) | set(ADMIN)
    src = Path(registry.__file__).parent / "api" / "views.py"
    used |= set(re.findall(r'"(leave_management\.[a-z_]+\.[a-z_]+)"', src.read_text()))
    assert used <= DECLARED


def test_schedule_is_merged_into_celery():
    assert {"leave.process-sla", "leave.year-end"} <= set(app.conf.beat_schedule)


def test_module_grant_without_permission_is_refused(world, as_user):
    r = apply(as_user(STAFF, perms=()))
    assert r.status_code == 403


def test_permission_without_module_grant_is_refused(world, as_user):
    r = apply(as_user(STAFF, modules=()))
    assert r.status_code == 403


def test_employee_cannot_reach_admin_endpoints(world, as_user):
    me = as_user(STAFF)
    assert me.get("/api/v1/leave/settings/policies").status_code == 403
    assert me.post("/api/v1/leave/records/offline", {}, format="json").status_code == 403
    assert me.post("/api/v1/leave/calendars", {}, format="json").status_code == 403


def test_admin_cannot_apply_or_decide_without_the_employee_grant(world, as_user):
    admin = as_user(OTHER, perms=ADMIN)
    assert apply(admin).status_code == 403
    pk = apply(as_user(STAFF)).json()["id"]
    assert act(as_user(OTHER, perms=ADMIN), pk, "review", decision="approve").status_code \
        == 403


def test_someone_elses_request_is_a_404_everywhere(world, as_user):
    pk = apply(as_user(STAFF)).json()["id"]
    outsider = as_user(OTHER)
    assert outsider.get(f"/api/v1/leave/requests/{pk}").status_code == 404
    assert outsider.get(f"/api/v1/leave/requests/{pk}/print").status_code == 404
    for action in ("withdraw", "cancel", "review", "decide"):
        assert act(outsider, pk, action, decision="approve", approve=True).status_code == 404
    assert outsider.get("/api/v1/leave/requests").json()["results"] == []
    assert outsider.get(f"/api/v1/leave/requests?user_id={STAFF}").json()["results"] == []


def test_only_the_assignee_acts_and_the_applicant_never_approves(world, as_user):
    r = apply(as_user(STAFF), category="EL", start_date="2027-04-05",
              end_date="2027-04-06", substitute_user_id=SUB)
    pk = r.json()["id"]
    assert act(as_user(STAFF), pk, "substitute", accept=True).status_code == 403
    act(as_user(SUB), pk, "substitute", accept=True)
    assert act(as_user(SUB), pk, "review", decision="recommended").status_code == 403
    act(as_user(HEAD), pk, "review", decision="recommended")
    assert act(as_user(SANCTION), pk, "decide", approve=True).status_code == 409
    act(as_user(EST), pk, "route")
    assert act(as_user(HEAD), pk, "decide", approve=True).status_code == 403
    assert act(as_user(STAFF), pk, "decide", approve=True).status_code == 403


def test_request_never_appears_in_its_own_applicants_inbox(world, as_user):
    pk = apply(as_user(HEAD)).json()["id"]
    assert LeaveRequest.objects.get(pk=pk).unit_head_user_id != HEAD
    assert as_user(HEAD).get("/api/v1/leave/tasks").json()["requests"] == []


def test_bad_query_parameter_is_a_400(world, as_user):
    assert as_user(STAFF).get("/api/v1/leave/me/balances?year=abc").status_code == 400


@pytest.mark.django_db(transaction=True)
def test_two_parallel_applications_cannot_double_book(stub_iam, request):
    request.getfixturevalue("world")
    stub_iam(users=USERS)
    applicant = leave.applicant_for(STAFF, "staff")
    app_ = leave.Application(category=Category.CL, start_date=date(2027, 2, 1),
                             end_date=date(2027, 2, 5), purpose="x")
    results, barrier = [], threading.Barrier(2)

    def run():
        barrier.wait()
        try:
            leave.apply(applicant, app_)
            results.append("ok")
        except Exception as exc:  # noqa: BLE001
            results.append(type(exc).__name__)
        finally:
            connection.close()

    threads = [threading.Thread(target=run) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == ["ConflictError", "ok"]
