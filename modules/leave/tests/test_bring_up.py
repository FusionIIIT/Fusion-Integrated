"""Getting the module from an empty database to accepting an application.

This is the path nobody exercises until the day it is deployed, which is why it
is pinned here: the module shipped once with no way to create a policy and a
500 when there was not one.
"""
from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.leave.domain.categories import Category
from modules.leave.models import AuthorityRule, HolidayCalendar, LeavePolicy
from modules.leave.selectors import balances

pytestmark = pytest.mark.django_db

FACULTY = 501
STAFF = 502
ADMIN = 900


@pytest.fixture
def staff_directory():
    for uid, kind in ((FACULTY, "faculty"), (STAFF, "staff"), (ADMIN, "staff")):
        UserRef.objects.create(
            user_id=uid, username=f"u{uid}", display_name=f"User {uid}",
            kind=kind, department="CSE")
    # A student is not an employee and takes no employee leave.
    UserRef.objects.create(user_id=1001, username="s1", display_name="Student",
                           kind="student", department="CSE")


def run(cmd, *args) -> str:
    out = StringIO()
    call_command(cmd, *args, stdout=out, stderr=StringIO())
    return out.getvalue()


def client(stub_iam, user_id, permissions):
    stub_iam(make_session(user_id=user_id, kind="staff", modules=("leave",),
                          permissions=permissions))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


class TestAnUnconfiguredModule:
    def test_applying_is_refused_clearly_rather_than_crashing(
        self, stub_iam, staff_directory
    ):
        c = client(stub_iam, FACULTY, ("leave.request.create",))

        response = c.post("/api/v1/leave/requests", {
            "category": "CL", "starts_on": "2026-03-02", "ends_on": "2026-03-03",
            "reason": "Personal work",
        }, format="json")

        # Regression: this was a 500, because NoEffectivePolicy was not a
        # DomainError and fell through the handler.
        assert response.status_code == 409
        body = response.json()["error"]
        assert body["code"] == "no_effective_policy"
        assert "leave administrator" in body["message"]


class TestConfiguringItThroughItsOwnApi:
    def test_an_administrator_can_take_it_from_empty_to_in_force(
        self, stub_iam, staff_directory
    ):
        c = client(stub_iam, ADMIN, ("leave.policy.manage", "leave.calendar.manage"))

        drafted = c.post("/api/v1/leave/admin/policies", {
            "version": "2026.1", "effective_from": "2026-01-01"}, format="json")
        assert drafted.status_code == 201
        assert drafted.json()["published"] is False
        policy_id = drafted.json()["id"]

        rule = c.post(f"/api/v1/leave/admin/policies/{policy_id}/rules", {
            "category": "CL", "annual_credit": "8.00"}, format="json")
        assert rule.status_code == 201

        published = c.post(f"/api/v1/leave/admin/policies/{policy_id}/publish")
        assert published.status_code == 200
        assert published.json()["published"] is True

    def test_a_version_with_no_rules_cannot_be_published(self, stub_iam, staff_directory):
        c = client(stub_iam, ADMIN, ("leave.policy.manage",))
        drafted = c.post("/api/v1/leave/admin/policies", {
            "version": "2026.1", "effective_from": "2026-01-01"}, format="json")

        refused = c.post(f"/api/v1/leave/admin/policies/{drafted.json()['id']}/publish")

        assert refused.status_code == 400
        assert "entitle nobody" in refused.json()["error"]["message"]

    def test_a_published_version_cannot_have_its_rules_edited(
        self, stub_iam, staff_directory
    ):
        c = client(stub_iam, ADMIN, ("leave.policy.manage",))
        drafted = c.post("/api/v1/leave/admin/policies", {
            "version": "2026.1", "effective_from": "2026-01-01"}, format="json")
        pid = drafted.json()["id"]
        c.post(f"/api/v1/leave/admin/policies/{pid}/rules",
               {"category": "CL", "annual_credit": "8.00"}, format="json")
        c.post(f"/api/v1/leave/admin/policies/{pid}/publish")

        refused = c.post(f"/api/v1/leave/admin/policies/{pid}/rules",
                         {"category": "CL", "annual_credit": "99.00"}, format="json")

        assert refused.status_code == 409
        assert "Draft a new version" in refused.json()["error"]["message"]

    def test_a_calendar_can_be_created_and_published(self, stub_iam, staff_directory):
        c = client(stub_iam, ADMIN, ("leave.calendar.manage",))

        drafted = c.post("/api/v1/leave/admin/calendars",
                         {"year": 2026, "version": "1"}, format="json")
        assert drafted.status_code == 201
        cid = drafted.json()["id"]
        c.post(f"/api/v1/leave/admin/calendars/{cid}/holidays",
               {"day": "2026-01-26", "name": "Republic Day"}, format="json")

        assert c.post(f"/api/v1/leave/admin/calendars/{cid}/publish").status_code == 200

    def test_a_duplicate_version_is_refused(self, stub_iam, staff_directory):
        c = client(stub_iam, ADMIN, ("leave.policy.manage",))
        body = {"version": "2026.1", "effective_from": "2026-01-01"}
        c.post("/api/v1/leave/admin/policies", body, format="json")

        assert c.post("/api/v1/leave/admin/policies", body,
                      format="json").status_code == 409


class TestTheSeedCommand:
    def test_it_puts_a_policy_calendar_and_routing_in_force(self, staff_directory):
        output = run("seed_leave_policy", "--year", "2026")

        assert "ready to accept applications" in output
        assert LeavePolicy.objects.filter(published=True).count() == 1
        assert HolidayCalendar.objects.filter(published=True, year=2026).count() == 1
        assert AuthorityRule.objects.count() == len(list(Category))

    def test_it_seeds_the_figures_the_specification_states(self, staff_directory):
        run("seed_leave_policy", "--year", "2026")

        policy = LeavePolicy.objects.get(published=True)
        entitlement = {
            (r.category, r.applies_to_faculty): r.annual_credit
            for r in policy.rules.all()
        }
        # BR-EL-002 to BR-EL-009.
        assert entitlement[("CL", None)] == 8
        assert entitlement[("RH", None)] == 2
        assert entitlement[("SCL", None)] == 15
        assert entitlement[("EL", False)] == 30
        assert entitlement[("COL", None)] == 20
        assert entitlement[("VL", True)] == 60

    def test_it_refuses_to_run_over_a_configured_institute(self, staff_directory):
        run("seed_leave_policy", "--year", "2026")

        output = run("seed_leave_policy", "--year", "2027")

        assert "already published" in output
        assert LeavePolicy.objects.count() == 1

    def test_draft_only_publishes_nothing(self, staff_directory):
        run("seed_leave_policy", "--year", "2026", "--draft-only")

        assert not LeavePolicy.objects.filter(published=True).exists()

    def test_the_policy_version_can_be_named(self, staff_directory):
        run("seed_leave_policy", "--year", "2026", "--policy-version", "ord-2026-a")

        assert LeavePolicy.objects.get().version == "ord-2026-a"


class TestCreditingTheYear:
    def test_entitlement_is_zero_until_it_is_credited(self, staff_directory):
        run("seed_leave_policy", "--year", "2026")

        assert balances.balance_for(STAFF, 2026, Category.CL).available == 0

    def test_crediting_gives_everyone_their_entitlement(self, staff_directory):
        run("seed_leave_policy", "--year", "2026")

        run("leave_credit_year", "2026")

        assert balances.balance_for(STAFF, 2026, Category.CL).available == 8
        assert balances.balance_for(STAFF, 2026, Category.EL).available == 30

    def test_faculty_get_vacation_leave_instead_of_earned_leave(self, staff_directory):
        run("seed_leave_policy", "--year", "2026")

        run("leave_credit_year", "2026")

        assert balances.balance_for(FACULTY, 2026, Category.VL).available == 60
        assert balances.balance_for(FACULTY, 2026, Category.EL).available == 0

    def test_students_are_not_employees(self, staff_directory):
        run("seed_leave_policy", "--year", "2026")

        output = run("leave_credit_year", "2026")

        assert "employees   3" in output
        assert balances.balance_for(1001, 2026, Category.CL).available == 0

    def test_running_it_again_credits_only_the_people_who_were_missed(
        self, staff_directory
    ):
        run("seed_leave_policy", "--year", "2026")
        run("leave_credit_year", "2026")
        UserRef.objects.create(user_id=503, username="u503", display_name="New",
                               kind="staff", department="ECE")

        output = run("leave_credit_year", "2026")

        assert "credited    1" in output
        assert "already had 3" in output
        assert balances.balance_for(STAFF, 2026, Category.CL).available == 8

    def test_a_dry_run_writes_nothing(self, staff_directory):
        run("seed_leave_policy", "--year", "2026")

        output = run("leave_credit_year", "2026", "--dry-run")

        assert "nothing was written" in output
        assert balances.balance_for(STAFF, 2026, Category.CL).available == 0

    def test_crediting_without_a_policy_says_what_is_missing(self, staff_directory):
        with pytest.raises(CommandError, match="No leave policy is published"):
            run("leave_credit_year", "2026")

    def test_an_empty_directory_says_what_to_run_first(self):
        run("seed_leave_policy", "--year", "2026")

        with pytest.raises(CommandError, match="sync_identity"):
            run("leave_credit_year", "2026")


class TestTheWholeWayThrough:
    def test_seed_credit_apply_approve(self, stub_iam, staff_directory):
        run("seed_leave_policy", "--year", "2026")
        run("leave_credit_year", "2026")

        applicant = client(stub_iam, STAFF, ("leave.request.create",
                                             "leave.request.view_self"))
        created = applicant.post("/api/v1/leave/requests", {
            "category": "CL", "starts_on": "2026-03-02", "ends_on": "2026-03-03",
            "reason": "Personal work"}, format="json")
        assert created.status_code == 201
        assert created.json()["state"] == "AWAITING_UNIT_HEAD"

        head = client(stub_iam, 601, ("leave.request.review",))
        UserRef.objects.create(user_id=601, username="u601", display_name="Head",
                               kind="faculty", department="CSE")
        approved = head.post(f"/api/v1/leave/review/{created.json()['id']}",
                             {"approve": True}, format="json")
        assert approved.status_code == 200
        assert approved.json()["state"] == "APPROVED_NOT_STARTED"

        assert balances.balance_for(STAFF, 2026, Category.CL).available == 6

    def test_the_seeded_policy_counts_casual_leave_as_working_days(
        self, stub_iam, staff_directory
    ):
        run("seed_leave_policy", "--year", "2026")
        run("leave_credit_year", "2026")
        c = client(stub_iam, STAFF, ("leave.request.create",))

        # Monday 2 March to Monday 9 March: CL skips the weekend, so 6 not 8.
        created = c.post("/api/v1/leave/requests", {
            "category": "CL", "starts_on": str(date(2026, 3, 2)),
            "ends_on": str(date(2026, 3, 9)), "reason": "Personal"}, format="json")

        assert created.status_code == 201
        assert created.json()["requested_days"] == "6.00"
