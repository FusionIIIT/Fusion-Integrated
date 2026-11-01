"""The four commands that write to, or report on, the ERP."""
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError

from api.models.erp import AuthUser, GlobalsExtrainfo, GlobalsHoldsdesignation
from iam.tests.erp_fixture import ErpFactory, ErpSchemaTestCase

#: A whole spreadsheet row pasted into one username, as it really happened.
IMPORT_LINE = (
    "24BCS001\tA PERSON\t\tsomebody@example.invalid\tMALE\t01-01-2006"
    "\tPARENT ONE\tPARENT TWO\tOBC\t9000000000\t\"12"
)


def run(command: str, *args) -> str:
    out, err = StringIO(), StringIO()
    call_command(command, *args, stdout=out, stderr=err)
    return out.getvalue() + err.getvalue()


class RepairImportArtifactsTests(ErpSchemaTestCase):
    def setUp(self):
        self.erp = ErpFactory(seed=10)

    def _artifact(self):
        """The wreckage, plus the genuine account from the same import."""
        genuine = self.erp.student(roll_no="24BCS001")
        wreckage = self.erp.account(username=IMPORT_LINE)
        return genuine, wreckage

    def test_it_finds_the_artifact(self):
        _, wreckage = self._artifact()

        output = run("erp_repair_import_artifacts")

        assert f"artifact  user {wreckage.id}" in output

    def test_it_reports_without_changing_anything(self):
        _, wreckage = self._artifact()

        run("erp_repair_import_artifacts")

        wreckage.refresh_from_db()
        assert wreckage.is_active is True

    def test_fix_deactivates_it(self):
        _, wreckage = self._artifact()

        run("erp_repair_import_artifacts", "--fix")

        wreckage.refresh_from_db()
        assert wreckage.is_active is False

    def test_the_genuine_account_is_untouched(self):
        genuine, _ = self._artifact()

        run("erp_repair_import_artifacts", "--fix")

        genuine.refresh_from_db()
        assert genuine.is_active is True

    def test_it_is_idempotent(self):
        self._artifact()
        run("erp_repair_import_artifacts", "--fix")

        output = run("erp_repair_import_artifacts", "--fix")

        assert "deactivated 0" in output

    def test_a_malformed_username_with_a_profile_is_left_alone(self):
        """Somebody set this account up deliberately, whatever its username."""
        self.erp.student(roll_no="24BCS001")
        odd = self.erp.employee(kind="staff", department="CSE")
        GlobalsExtrainfo.objects.filter(user_id=odd.id).update(id="kept")
        AuthUser.objects.filter(pk=odd.id).update(username=IMPORT_LINE)

        output = run("erp_repair_import_artifacts", "--fix")

        assert "LEFT ALONE" in output
        odd.refresh_from_db()
        assert odd.is_active is True

    def test_a_malformed_username_holding_a_designation_is_left_alone(self):
        self.erp.student(roll_no="24BCS001")
        odd = self.erp.account(username=IMPORT_LINE)
        self.erp.holds(odd, "Senior Assistant")

        output = run("erp_repair_import_artifacts", "--fix")

        assert "holds a designation" in output
        odd.refresh_from_db()
        assert odd.is_active is True

    def test_wreckage_with_no_genuine_twin_is_left_alone(self):
        """Without a surviving account, deactivating locks somebody out."""
        odd = self.erp.account(username=IMPORT_LINE)

        output = run("erp_repair_import_artifacts", "--fix")

        assert "no other active account" in output
        odd.refresh_from_db()
        assert odd.is_active is True

    def test_it_reports_whitespace_duplicates_separately(self):
        real = self.erp.employee(kind="staff", department="CSE")
        spare = self.erp.account(username=f"{real.username} ")
        self.erp.holds(spare, "Senior Assistant")

        output = run("erp_repair_import_artifacts")

        assert "differing only by whitespace" in output
        assert "holds designation" in output

    def test_it_does_not_touch_a_whitespace_duplicate(self):
        """Which account keeps their role is a decision about their job."""
        real = self.erp.employee(kind="staff", department="CSE")
        spare = self.erp.account(username=f"{real.username} ")
        self.erp.holds(spare, "Senior Assistant")

        run("erp_repair_import_artifacts", "--fix")

        spare.refresh_from_db()
        assert spare.is_active is True

    def test_a_clean_institute_says_so(self):
        self.erp.institute(employees=4, students=2, orphans=1)

        assert "no malformed usernames" in run("erp_repair_import_artifacts")


class SetEmployeeDepartmentTests(ErpSchemaTestCase):
    def setUp(self):
        self.erp = ErpFactory(seed=11)

    def test_it_reports_who_has_no_department(self):
        without = self.erp.employee(kind="staff", department=None)
        self.erp.employee(kind="faculty", department="CSE")

        output = run("erp_set_employee_department", "--report")

        assert str(without.id) in output
        assert "1 employee(s) with no department" in output

    def test_a_named_department_is_assigned(self):
        without = self.erp.employee(kind="staff", department=None)
        self.erp.department("Registrar Office")

        run("erp_set_employee_department", "--set",
            f"{without.id}=Registrar Office")

        profile = GlobalsExtrainfo.objects.get(user_id=without.id)
        assert profile.department.name == "Registrar Office"

    def test_an_unknown_department_is_refused_not_created(self):
        without = self.erp.employee(kind="staff", department=None)

        with self.assertRaises(CommandError) as caught:
            run("erp_set_employee_department", "--set", f"{without.id}=Atlantis")

        assert "Not a department" in str(caught.exception)

    def test_an_existing_department_is_not_overwritten(self):
        settled = self.erp.employee(kind="faculty", department="CSE")
        self.erp.department("ME")

        output = run("erp_set_employee_department", "--set", f"{settled.id}=ME")

        assert "already has one" in output
        assert GlobalsExtrainfo.objects.get(
            user_id=settled.id).department.name == "CSE"

    def test_force_overwrites_it(self):
        settled = self.erp.employee(kind="faculty", department="CSE")
        self.erp.department("ME")

        run("erp_set_employee_department", "--set", f"{settled.id}=ME", "--force")

        assert GlobalsExtrainfo.objects.get(
            user_id=settled.id).department.name == "ME"

    def test_placeholder_fills_the_gap_and_is_obviously_provisional(self):
        without = self.erp.employee(kind="staff", department=None)

        run("erp_set_employee_department", "--placeholder")

        name = GlobalsExtrainfo.objects.get(user_id=without.id).department.name
        assert "placeholder" in name.lower()

    def test_a_dry_run_writes_nothing(self):
        without = self.erp.employee(kind="staff", department=None)

        output = run("erp_set_employee_department", "--placeholder", "--dry-run")

        assert "not written" in output
        assert GlobalsExtrainfo.objects.get(user_id=without.id).department is None

    def test_it_creates_a_profile_for_an_employee_that_has_none(self):
        """An orphan holding a designation is an employee with a missing record."""
        orphan = self.erp.account()
        self.erp.holds(orphan, "Senior Assistant")

        run("erp_set_employee_department", "--placeholder")

        assert GlobalsExtrainfo.objects.filter(user_id=orphan.id).exists()

    def test_a_whitespace_duplicate_is_flagged_rather_than_given_one(self):
        """The gap is a duplicate login, not a missing department."""
        real = self.erp.employee(kind="staff", department="CSE")
        spare = self.erp.account(username=f"{real.username} ")
        self.erp.holds(spare, "Senior Assistant")

        output = run("erp_set_employee_department", "--placeholder")

        assert "NEEDS A PERSON" in output
        assert not GlobalsExtrainfo.objects.filter(user_id=spare.id).exists()

    def test_it_refuses_when_given_nothing_to_do(self):
        with self.assertRaises(CommandError):
            run("erp_set_employee_department")

    def test_a_fully_configured_institute_reports_clean(self):
        self.erp.employee(kind="faculty", department="CSE")

        assert "every employee has a department" in run(
            "erp_set_employee_department", "--report")


class MergeDuplicateAccountTests(ErpSchemaTestCase):
    def setUp(self):
        self.erp = ErpFactory(seed=12)

    def _pair(self):
        """The real case: profile on one login, role on the other."""
        keeper = self.erp.employee(kind="staff", department="Registrar Office")
        loser = self.erp.account(username=f"{keeper.username} ")
        self.erp.holds(loser, "Senior Assistant")
        return keeper, loser

    def test_a_dry_run_lists_the_moves_and_writes_nothing(self):
        keeper, loser = self._pair()

        output = run("erp_merge_duplicate_account",
                     "--pair", f"{keeper.id}={loser.id}", "--dry-run")

        assert "globals_holdsdesignation" in output
        assert "nothing was written" in output
        loser.refresh_from_db()
        assert loser.is_active is True

    def test_the_designation_moves_to_the_account_they_use(self):
        keeper, loser = self._pair()

        run("erp_merge_duplicate_account", "--pair", f"{keeper.id}={loser.id}")

        assert GlobalsHoldsdesignation.objects.filter(user_id=keeper.id).exists()
        assert not GlobalsHoldsdesignation.objects.filter(user_id=loser.id).exists()

    def test_the_role_is_not_lost(self):
        keeper, loser = self._pair()

        run("erp_merge_duplicate_account", "--pair", f"{keeper.id}={loser.id}")

        held = GlobalsHoldsdesignation.objects.get(user_id=keeper.id)
        assert held.designation.name == "Senior Assistant"

    def test_the_spare_login_is_deactivated_not_deleted(self):
        keeper, loser = self._pair()

        run("erp_merge_duplicate_account", "--pair", f"{keeper.id}={loser.id}")

        loser.refresh_from_db()
        assert loser.is_active is False
        assert AuthUser.objects.filter(pk=loser.id).exists()

    def test_the_keepers_own_profile_survives(self):
        keeper, loser = self._pair()

        run("erp_merge_duplicate_account", "--pair", f"{keeper.id}={loser.id}")

        assert GlobalsExtrainfo.objects.filter(user_id=keeper.id).count() == 1

    def test_two_different_people_cannot_be_merged(self):
        one = self.erp.employee(kind="staff", department="CSE")
        other = self.erp.employee(kind="staff", department="ME")

        with self.assertRaises(CommandError) as caught:
            run("erp_merge_duplicate_account", "--pair", f"{one.id}={other.id}")

        assert "not the same username" in str(caught.exception)

    def test_an_account_cannot_be_merged_into_itself(self):
        one = self.erp.employee(kind="staff", department="CSE")

        with self.assertRaises(CommandError):
            run("erp_merge_duplicate_account", "--pair", f"{one.id}={one.id}")

    def test_a_missing_account_is_named(self):
        keeper, _ = self._pair()

        with self.assertRaises(CommandError) as caught:
            run("erp_merge_duplicate_account", "--pair", f"{keeper.id}=999999")

        assert "No such user" in str(caught.exception)

    def test_the_pair_argument_must_be_two_ids(self):
        with self.assertRaises(CommandError):
            run("erp_merge_duplicate_account", "--pair", "not-a-pair")


class MergeWhenBothHoldTheRoleTests(ErpSchemaTestCase):
    def setUp(self):
        self.erp = ErpFactory(seed=13)
        self.keeper = self.erp.employee(kind="staff", department="Registrar Office")
        self.loser = self.erp.account(username=f"{self.keeper.username} ")
        self.erp.holds(self.keeper, "Senior Assistant")
        self.erp.holds(self.loser, "Senior Assistant")

    def test_a_designation_both_accounts_hold_does_not_break_the_merge(self):
        run("erp_merge_duplicate_account",
            "--pair", f"{self.keeper.id}={self.loser.id}")

        self.loser.refresh_from_db()
        assert self.loser.is_active is False

    def test_the_keeper_holds_it_exactly_once(self):
        run("erp_merge_duplicate_account",
            "--pair", f"{self.keeper.id}={self.loser.id}")

        assert GlobalsHoldsdesignation.objects.filter(
            user_id=self.keeper.id, designation__name="Senior Assistant").count() == 1

    def test_a_designation_only_the_loser_holds_still_moves(self):
        self.erp.holds(self.loser, "Junior Assistant")

        run("erp_merge_duplicate_account",
            "--pair", f"{self.keeper.id}={self.loser.id}")

        held = set(GlobalsHoldsdesignation.objects.filter(
            user_id=self.keeper.id).values_list("designation__name", flat=True))
        assert held == {"Senior Assistant", "Junior Assistant"}
