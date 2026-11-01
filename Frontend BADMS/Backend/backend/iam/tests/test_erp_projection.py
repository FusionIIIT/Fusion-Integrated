"""The ERP-facing half of this service, tested for the first time."""
from iam.erp_source import iter_users
from iam.models import IamUser
from iam.services import employee_page
from iam.sync import sync_all
from iam.tests.erp_fixture import ErpFactory, ErpSchemaTestCase


class KindProjectionTests(ErpSchemaTestCase):
    """What the ERP can say somebody is, read out of real rows."""

    def setUp(self):
        self.erp = ErpFactory(seed=1)

    def _kinds(self) -> dict[int, str]:
        return {
            row["erp_user_id"]: row["kind"]
            for batch in iter_users(batch_size=50) for row in batch
        }

    def test_a_profile_is_believed(self):
        faculty = self.erp.employee(kind="faculty", department="CSE")
        staff = self.erp.employee(kind="staff", department="ME")

        kinds = self._kinds()

        assert kinds[faculty.id] == "faculty"
        assert kinds[staff.id] == "staff"

    def test_a_student_is_a_student(self):
        student = self.erp.student(roll_no="24BCS001")

        assert self._kinds()[student.id] == "student"

    def test_an_account_with_nothing_at_all_is_unknown(self):
        """The defect: 92 of these were called staff and drew leave."""
        orphan = self.erp.account()

        assert self._kinds()[orphan.id] == "unknown"

    def test_an_account_holding_a_designation_is_staff(self):
        """The designation is the evidence; the missing profile is a gap."""
        orphan = self.erp.account()
        self.erp.holds(orphan, "Senior Assistant")

        assert self._kinds()[orphan.id] == "staff"

    def test_the_department_comes_across(self):
        employee = self.erp.employee(kind="faculty", department="ECE")

        rows = {r["erp_user_id"]: r for b in iter_users() for r in b}
        assert rows[employee.id]["department"] == "ECE"

    def test_an_employee_with_no_department_projects_an_empty_one(self):
        employee = self.erp.employee(kind="staff", department=None)

        rows = {r["erp_user_id"]: r for b in iter_users() for r in b}
        assert rows[employee.id]["department"] == ""

    def test_is_active_crosses_over(self):
        gone = self.erp.employee(kind="staff", department="CSE", active=False)

        rows = {r["erp_user_id"]: r for b in iter_users() for r in b}
        assert rows[gone.id]["is_active"] is False


class SyncTests(ErpSchemaTestCase):
    """The projection end to end, against a synthetic institute."""

    def setUp(self):
        self.erp = ErpFactory(seed=2)
        self.made = self.erp.institute(employees=20, students=10, orphans=3)

    def test_everybody_is_projected(self):
        sync_all()

        assert IamUser.objects.count() == 33

    def test_the_orphans_land_as_unknown(self):
        sync_all()

        assert IamUser.objects.filter(kind="unknown").count() == 3

    def test_the_payroll_excludes_them(self):
        sync_all()

        page = employee_page(limit=100)

        assert page["count"] == 20
        assert not IamUser.objects.filter(
            erp_user_id__in=[o.id for o in self.made["orphans"]],
            kind__in=("faculty", "staff")).exists()

    def test_students_are_not_on_the_payroll(self):
        sync_all()

        on_payroll = {r["user_id"] for r in employee_page(limit=100)["results"]}
        assert on_payroll.isdisjoint({s.id for s in self.made["students"]})

    def test_syncing_twice_changes_nothing(self):
        sync_all()
        before = IamUser.objects.count()

        sync_all()

        assert IamUser.objects.count() == before

    def test_the_payroll_pages_and_reports_a_total(self):
        sync_all()

        first = employee_page(limit=8, offset=0)
        second = employee_page(limit=8, offset=8)

        assert first["count"] == second["count"] == 20
        assert len(first["results"]) == len(second["results"]) == 8
        assert {r["user_id"] for r in first["results"]}.isdisjoint(
            {r["user_id"] for r in second["results"]})
