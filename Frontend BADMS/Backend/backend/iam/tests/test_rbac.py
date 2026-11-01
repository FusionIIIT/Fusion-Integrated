"""One basic role, many additional roles, and who may hold what."""
from unittest.mock import patch

from django.test import TestCase, override_settings

from iam import rbac, services, sync
from iam.models import (IamRole, IamRoleViolation, IamToken, IamUser,
                        IamUserDesignation, RolePermission)
from iam.tests.test_sync import fake_erp, user


def catalogue():
    IamRole.objects.bulk_create([
        IamRole(code="student", category=IamRole.BASIC, allowed_kinds="student"),
        IamRole(code="Professor", category=IamRole.RANK, allowed_kinds="faculty"),
        IamRole(code="Dean Academic", category=IamRole.OFFICE,
                allowed_kinds="faculty"),
        IamRole(code="acadadmin", category=IamRole.OFFICE,
                allowed_kinds="faculty,staff"),
        IamRole(code="co-ordinator", category=IamRole.FUNCTIONAL,
                allowed_kinds="faculty,staff,student"),
    ])


class RolePolicyTests(TestCase):
    databases = {"default", "system_db"}

    def setUp(self):
        catalogue()

    def _sync(self, users, designations):
        with patch.object(sync, "erp_source",
                          fake_erp(users=users, designations=designations)):
            return sync.sync_all()

    def test_a_student_may_not_be_made_dean(self):
        """The live ERP has exactly this row, and it grants 54 permissions."""
        run = self._sync([user(1, "scholar", kind="student")],
                         [(1, "student"), (1, "Dean Academic")])

        self.assertEqual(run.role_violations, 1)
        v = IamRoleViolation.objects.get()
        self.assertEqual((v.username, v.kind, v.designation),
                         ("scholar", "student", "Dean Academic"))

    def test_a_student_may_be_a_coordinator(self):
        """A functional role is open to anyone — the club-coordinator case."""
        run = self._sync([user(1, "scholar", kind="student")],
                         [(1, "student"), (1, "co-ordinator")])

        self.assertEqual(run.role_violations, 0)

    @override_settings(IAM_ENFORCE_ROLE_POLICY=False)
    def test_reporting_mode_records_without_revoking(self):
        """How a deployment starts. The catalogue is a claim about institute
        practice, and refusing before it has been confirmed would revoke access
        from whoever the claim is wrong about, with no warning."""
        self._sync([user(1, "scholar", kind="student")],
                   [(1, "student"), (1, "Dean Academic")])

        held = set(IamUserDesignation.objects.filter(erp_user_id=1)
                   .values_list("designation", flat=True))
        self.assertEqual(held, {"student", "Dean Academic"})
        self.assertFalse(IamRoleViolation.objects.get().enforced)

    @override_settings(IAM_ENFORCE_ROLE_POLICY=True)
    def test_enforcing_withholds_the_role_and_the_authority_with_it(self):
        self._sync([user(1, "scholar", kind="student")],
                   [(1, "student"), (1, "Dean Academic")])

        held = set(IamUserDesignation.objects.filter(erp_user_id=1)
                   .values_list("designation", flat=True))
        self.assertEqual(held, {"student"})
        self.assertTrue(IamRoleViolation.objects.get().enforced)

    def test_an_uncatalogued_role_is_reported_by_absence_not_refused(self):
        """The academic office adds designations without telling this service. A
        new one must not lock its holder out overnight."""
        run = self._sync([user(1, "someone", kind="staff")],
                         [(1, "Chief Vigilance Officer")])

        self.assertEqual(run.role_violations, 0)
        self.assertTrue(IamUserDesignation.objects.filter(
            designation="Chief Vigilance Officer").exists())

    def test_violations_are_the_current_picture_not_a_log(self):
        self._sync([user(1, "scholar", kind="student")],
                   [(1, "student"), (1, "Dean Academic")])
        self.assertEqual(IamRoleViolation.objects.count(), 1)

        self._sync([user(1, "scholar", kind="student")], [(1, "student")])
        self.assertEqual(IamRoleViolation.objects.count(), 0)


class BasicRoleTests(TestCase):
    databases = {"default", "system_db"}

    def _session(self, username):
        u = IamUser.objects.get(username=username)
        return services.build_session(
            IamToken(erp_user_id=u.erp_user_id, username=u.username))

    def test_the_basic_role_is_held_without_being_assigned(self):
        """No ERP row says a professor is faculty — extrainfo.user_type does. A
        permission granted to `faculty` would otherwise reach nobody at all."""
        with patch.object(sync, "erp_source", fake_erp(
                users=[user(1, "atul", kind="faculty")],
                designations=[(1, "Professor")])):
            sync.sync_all()

        s = self._session("atul")
        self.assertEqual(s["basic_role"], "faculty")
        self.assertEqual(s["roles"], ["faculty", "Professor"])

    def test_someone_with_no_designation_still_has_their_basic_role(self):
        """121 staff hold no designation row. Without this they have no role,
        and a role is what every permission is granted to."""
        with patch.object(sync, "erp_source",
                          fake_erp(users=[user(1, "clerk", kind="staff")])):
            sync.sync_all()

        self.assertEqual(self._session("clerk")["roles"], ["staff"])

    def test_an_office_is_the_default_view_over_the_basic_role(self):
        with patch.object(sync, "erp_source", fake_erp(
                users=[user(1, "pankaj", kind="staff")],
                designations=[(1, "acadadmin")])):
            sync.sync_all()

        s = self._session("pankaj")
        self.assertEqual(s["active_role"], "acadadmin")
        self.assertEqual(s["basic_role"], "staff")

    def test_the_basic_role_is_the_default_when_no_office_is_held(self):
        with patch.object(sync, "erp_source",
                          fake_erp(users=[user(1, "clerk", kind="staff")])):
            sync.sync_all()

        self.assertEqual(self._session("clerk")["active_role"], "staff")


class ProgrammeRoleTests(TestCase):
    """A UG student is not a research scholar.

    `globals_holdsdesignation` says "student" for all 3,027 of them, so a
    permission meant for a scholar reached every undergraduate. The programme a
    student is enrolled on is derived into a role beside the basic one.
    """

    databases = {"default", "system_db"}

    def setUp(self):
        catalogue()
        IamRole.objects.bulk_create([
            IamRole(code=code, category=IamRole.BASIC, allowed_kinds="student")
            for code in ("ug_student", "pg_student", "phd_student")
        ])

    def _sync(self, programme_roles):
        with patch.object(sync, "erp_source", fake_erp(
                users=[user(1, "ug", kind="student"),
                       user(2, "pg", kind="student")],
                designations=[(1, "student"), (2, "student")],
                programme_roles=programme_roles)):
            return sync.sync_all()

    def test_the_programme_role_is_held_beside_the_basic_one(self):
        self._sync([(1, "ug_student"), (2, "pg_student")])

        self.assertEqual(
            sorted(IamUserDesignation.objects.filter(erp_user_id=2)
                   .values_list("designation", flat=True)),
            ["pg_student", "student"])

    def test_an_undergraduate_does_not_hold_the_postgraduate_role(self):
        self._sync([(1, "ug_student"), (2, "pg_student")])

        held = set(IamUserDesignation.objects.filter(erp_user_id=1)
                   .values_list("designation", flat=True))
        self.assertNotIn("pg_student", held)
        self.assertNotIn("phd_student", held)

    def test_a_permission_granted_to_the_scholar_role_misses_undergraduates(self):
        """The whole point. `research.scholar.view` on `pg_student` reaches 56
        students; on `student` it reached all 3,027."""
        RolePermission.objects.create(designation="pg_student",
                                      permission="research.scholar.view")
        self._sync([(1, "ug_student"), (2, "pg_student")])

        self.assertEqual(services.permissions_for(["student", "ug_student"]), [])
        self.assertEqual(services.permissions_for(["student", "pg_student"]),
                         ["research.scholar.view"])

    def test_changing_programme_moves_the_role_rather_than_adding_one(self):
        """A student who transfers must not keep the old programme's access."""
        self._sync([(1, "ug_student"), (2, "pg_student")])
        self._sync([(1, "pg_student"), (2, "pg_student")])

        self.assertEqual(
            sorted(IamUserDesignation.objects.filter(erp_user_id=1)
                   .values_list("designation", flat=True)),
            ["pg_student", "student"])

    def test_only_a_student_may_hold_a_programme_role(self):
        """A faculty member with `pg_student` would read as a scholar."""
        with patch.object(sync, "erp_source", fake_erp(
                users=[user(3, "prof", kind="faculty")],
                programme_roles=[(3, "pg_student")])):
            run = sync.sync_all()

        self.assertEqual(run.role_violations, 1)
        self.assertEqual(IamRoleViolation.objects.get().designation,
                         "pg_student")


class TheDeclaredCatalogue(TestCase):
    """The policy that actually gets seeded, rather than a fixture standing in
    for it. A test that builds its own catalogue proves the mechanism works and
    says nothing about what the mechanism was told."""

    databases = {"default", "system_db"}

    def _declared(self, code):
        return next((row for row in rbac.CATALOGUE if row[0] == code), None)

    def test_a_programme_role_is_a_student_role_and_nothing_else(self):
        for code in ("ug_student", "pg_student", "phd_student"):
            row = self._declared(code)
            self.assertIsNotNone(row, f"{code} is not catalogued")
            _code, _label, category, kinds = row
            self.assertEqual(set(kinds), {"student"},
                             f"{code} may be held by {kinds}")
            self.assertEqual(category, IamRole.BASIC)

    def test_an_academic_rank_stays_faculty_only(self):
        for code in ("Professor", "Associate Professor", "Assistant Professor"):
            self.assertEqual(set(self._declared(code)[3]), {"faculty"})

    def test_every_declared_role_names_kinds_that_exist(self):
        """A typo in the allowed kinds silently makes a role unholdable."""
        for code, _label, _category, kinds in rbac.CATALOGUE:
            unknown = set(kinds) - set(rbac.BASIC_KINDS)
            self.assertEqual(unknown, set(), f"{code} allows {unknown}")
