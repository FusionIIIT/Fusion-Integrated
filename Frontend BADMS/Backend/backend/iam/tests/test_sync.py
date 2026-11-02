"""The ERP -> IAM projection.

Every test here fakes iam.sync.erp_source. That is not a shortcut: erp_source
is the only module that knows the ERP's shape, so replacing it exercises
everything downstream of the anti-corruption boundary without needing the ERP's
276-FK schema to exist. If a test here needed a real ERP table, the boundary
would have leaked.
"""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from iam import sync
from iam.tests.erp_fixture import ErpFactory, ErpSchemaTestCase
from iam.models import (IamDesignationModule, IamRole, IamRoleViolation,
                        IamUser,
                        IamUserAcademic,
                        IamUserDesignation, SyncRun)


def user(uid, username, **over):
    row = {
        "erp_user_id": uid, "username": username,
        "display_name": username.title(), "email": f"{username}@example.invalid",
        "kind": "student", "is_active": True, "password_hash": "pbkdf2$fake",
        "department": "CSE", "programme": "B.Tech", "discipline": "CSE",
        "batch_year": 2023,
    }
    row.update(over)
    return row


def academic(roll, cpi="8.0", **over):
    row = {
        "roll_no": roll, "programme": "B.Tech", "semester": 5,
        "semester_type": "Odd Semester", "declared_seq": 50,
        "cpi": Decimal(cpi), "earned_credits": Decimal("100"),
        "cpi_denominator_credits": Decimal("96"), "active_backlogs": 0,
        "courses_counted": 30, "announcement_id": 7,
    }
    row.update(over)
    return row


def fake_erp(users=(), designations=(), academics=(), profiles=None,
             programme_roles=()):
    """A stand-in for iam.erp_source with the same callables.

    Must mirror the real module exactly. When erp_source grows a function, it
    grows here too — a fake that has drifted is worse than no fake, because it
    makes the sync look tested when the new path is not exercised at all.
    """
    return SimpleNamespace(
        iter_users=lambda batch_size=500: iter([list(users)] if users else []),
        all_user_designations=lambda: list(designations),
        all_student_programme_roles=lambda: list(programme_roles),
        all_academic_standings=lambda: list(academics),
        all_student_profiles=lambda: dict(profiles or {}),
        fetch_password_hash=lambda username: None,
        designations_for_user=lambda uid: [p for p in (*designations,
                                                       *programme_roles)
                                           if p[0] == uid],
    )


class SyncTests(TestCase):
    databases = {"default", "system_db"}

    def test_projects_users_and_designations(self):
        erp = fake_erp(
            users=[user(1, "alice"), user(2, "bob", kind="faculty")],
            designations=[(1, "student"), (2, "professor")],
        )
        with patch.object(sync, "erp_source", erp):
            run = sync.sync_all()

        self.assertEqual(run.status, "succeeded")
        self.assertEqual(run.users_seen, 2)
        self.assertEqual(IamUser.objects.count(), 2)
        self.assertEqual(IamUserDesignation.objects.count(), 2)

        alice = IamUser.objects.get(pk=1)
        self.assertEqual(alice.username, "alice")
        self.assertEqual(alice.discipline, "CSE")
        self.assertEqual(alice.batch_year, 2023)

    def test_running_twice_changes_nothing(self):
        erp = fake_erp(users=[user(1, "alice")], designations=[(1, "student")])
        with patch.object(sync, "erp_source", erp):
            sync.sync_all()
            sync.sync_all()

        self.assertEqual(IamUser.objects.count(), 1)
        self.assertEqual(IamUserDesignation.objects.count(), 1)

    def test_an_updated_user_is_overwritten_not_duplicated(self):
        with patch.object(sync, "erp_source", fake_erp(users=[user(1, "alice")])):
            sync.sync_all()
        with patch.object(sync, "erp_source",
                          fake_erp(users=[user(1, "alice", display_name="Alice B",
                                               discipline="ECE")])):
            sync.sync_all()

        self.assertEqual(IamUser.objects.count(), 1)
        alice = IamUser.objects.get(pk=1)
        self.assertEqual(alice.display_name, "Alice B")
        self.assertEqual(alice.discipline, "ECE")

    def test_a_revoked_designation_actually_disappears(self):
        """The security-relevant direction. A diff that only adds would keep a
        revoked role alive forever, so the sync replaces wholesale."""
        with patch.object(sync, "erp_source",
                          fake_erp(users=[user(1, "alice")],
                                   designations=[(1, "student"), (1, "placement_coord")])):
            sync.sync_all()
        self.assertEqual(IamUserDesignation.objects.filter(erp_user_id=1).count(), 2)

        with patch.object(sync, "erp_source",
                          fake_erp(users=[user(1, "alice")],
                                   designations=[(1, "student")])):
            sync.sync_all()

        held = set(IamUserDesignation.objects.filter(erp_user_id=1)
                   .values_list("designation", flat=True))
        self.assertEqual(held, {"student"})

    def test_the_sync_never_touches_module_grants(self):
        """Grants come from each service's manifest, and from nowhere else.

        The ERP projection used to write them too, and the union of two writers
        could only ever widen access. One writer per module is what makes a
        revoke actually revoke.
        """
        IamDesignationModule.objects.create(
            designation="faculty", module_code="examinations",
            source="manifest:legacy")

        with patch.object(sync, "erp_source", fake_erp(users=[user(1, "alice")])):
            sync.sync_all()

        rows = set(IamDesignationModule.objects.values_list(
            "designation", "module_code", "source"))
        self.assertEqual(rows, {("faculty", "examinations", "manifest:legacy")})

    def test_a_vanished_user_is_deactivated_never_deleted(self):
        """Applications and audit rows reference the id; a hard delete would
        leave them dangling."""
        with patch.object(sync, "erp_source",
                          fake_erp(users=[user(1, "alice"), user(2, "bob")])):
            sync.sync_all()

        with patch.object(sync, "erp_source", fake_erp(users=[user(1, "alice")])):
            run = sync.sync_all()

        self.assertEqual(run.deactivated, 1)
        self.assertEqual(IamUser.objects.count(), 2)          # still there
        self.assertFalse(IamUser.objects.get(pk=2).is_active)
        self.assertTrue(IamUser.objects.get(pk=1).is_active)

    def test_an_empty_erp_read_does_not_deactivate_everyone(self):
        """A failed or empty read must not be mistaken for 'nobody exists'."""
        with patch.object(sync, "erp_source", fake_erp(users=[user(1, "alice")])):
            sync.sync_all()
        with patch.object(sync, "erp_source", fake_erp(users=[])):
            sync.sync_all()

        self.assertTrue(IamUser.objects.get(pk=1).is_active)

    def test_a_failure_is_recorded_and_re_raised(self):
        def boom(batch_size=500):
            raise RuntimeError("ERP went away mid-read")

        erp = fake_erp(users=[user(1, "alice")])
        erp.iter_users = boom
        with patch.object(sync, "erp_source", erp):
            with self.assertRaises(RuntimeError):
                sync.sync_all()

        run = SyncRun.objects.first()
        self.assertEqual(run.status, "failed")
        self.assertIn("ERP went away mid-read", run.error)
        self.assertIsNotNone(run.finished_at)

    def test_academic_standing_is_projected_and_joined_to_the_user(self):
        with patch.object(sync, "erp_source",
                          fake_erp(users=[user(1, "21BCS002")],
                                   academics=[academic("21BCS002", cpi="8.4")])):
            run = sync.sync_all()

        self.assertEqual(run.academics_written, 1)
        a = IamUserAcademic.objects.get(pk=1)          # keyed on erp_user_id
        self.assertEqual(a.roll_no, "21BCS002")
        self.assertEqual(a.cpi, Decimal("8.4"))
        self.assertEqual(a.computed_by, sync.COMPUTED_BY)

    def test_a_standing_with_no_matching_user_is_dropped_not_crashed(self):
        with patch.object(sync, "erp_source",
                          fake_erp(users=[user(1, "alice")],
                                   academics=[academic("GHOST999")])):
            run = sync.sync_all()
        self.assertEqual(run.academics_written, 0)

    def test_roll_number_case_mismatch_still_joins(self):
        with patch.object(sync, "erp_source",
                          fake_erp(users=[user(1, "21bcs002")],
                                   academics=[academic("21BCS002")])):
            run = sync.sync_all()
        self.assertEqual(run.academics_written, 1)

    def test_a_retracted_result_removes_the_standing(self):
        """The case that matters. If a declaration is withdrawn the student's
        CPI must vanish so eligibility fails closed again — an upsert-only sync
        would leave a retracted CPI in place and someone would apply on it."""
        with patch.object(sync, "erp_source",
                          fake_erp(users=[user(1, "21BCS002")],
                                   academics=[academic("21BCS002")])):
            sync.sync_all()
        self.assertEqual(IamUserAcademic.objects.count(), 1)

        with patch.object(sync, "erp_source",
                          fake_erp(users=[user(1, "21BCS002")], academics=[])):
            sync.sync_all()
        self.assertEqual(IamUserAcademic.objects.count(), 0)

    def test_designations_are_deduplicated(self):
        """The ERP can hold the same pair twice; the unique constraint must not
        turn that into a crash."""
        with patch.object(sync, "erp_source",
                          fake_erp(users=[user(1, "alice")],
                                   designations=[(1, "student"), (1, "student")])):
            run = sync.sync_all()
        self.assertEqual(run.designations_written, 1)


class DeactivationGuardTests(TestCase):
    """A truncated ERP read must not be mistaken for a mass resignation."""
    databases = {"default", "system_db"}

    def _populate(self, n):
        IamUser.objects.bulk_create(
            [IamUser(**user(i, f"u{i}")) for i in range(1, n + 1)])

    def test_a_read_that_lost_most_of_the_people_is_refused(self):
        self._populate(200)
        erp = fake_erp(users=[user(i, f"u{i}") for i in range(1, 51)])
        with patch.object(sync, "erp_source", erp):
            with self.assertRaises(sync.SuspectDeactivation):
                sync.sync_all()
        # Nothing was deactivated: the refusal comes before the update.
        self.assertEqual(IamUser.objects.filter(is_active=True).count(), 200)

    def test_a_plausible_handful_still_goes_through(self):
        self._populate(2000)
        erp = fake_erp(users=[user(i, f"u{i}") for i in range(1, 1991)])
        with patch.object(sync, "erp_source", erp):
            run = sync.sync_all()
        self.assertEqual(run.status, "succeeded")
        self.assertEqual(run.deactivated, 10)

    def test_a_small_installation_is_judged_by_count_not_share(self):
        """Ten of forty is 25%, but ten people is not a truncated read."""
        self._populate(40)
        erp = fake_erp(users=[user(i, f"u{i}") for i in range(1, 31)])
        with patch.object(sync, "erp_source", erp):
            run = sync.sync_all()
        self.assertEqual(run.deactivated, 10)

    def test_the_operator_can_override_a_genuine_mass_departure(self):
        self._populate(200)
        erp = fake_erp(users=[user(i, f"u{i}") for i in range(1, 51)])
        with patch.object(sync, "erp_source", erp):
            run = sync.sync_all(force_deactivate=True)
        self.assertEqual(run.deactivated, 150)

    def test_keeping_missing_users_skips_the_question_entirely(self):
        self._populate(200)
        erp = fake_erp(users=[user(i, f"u{i}") for i in range(1, 51)])
        with patch.object(sync, "erp_source", erp):
            run = sync.sync_all(deactivate_missing=False)
        self.assertEqual(run.deactivated, 0)
        self.assertEqual(IamUser.objects.filter(is_active=True).count(), 200)


class RefreshDesignationsTests(TestCase):
    """A post assigned since the last sync must not wait for the next one."""
    databases = {"default", "system_db"}

    def setUp(self):
        IamUser.objects.create(**user(1, "asha", kind="staff"))
        IamUserDesignation.objects.create(erp_user_id=1, designation="staff")

    def test_a_newly_held_post_appears_without_a_full_sync(self):
        erp = fake_erp(designations=[(1, "staff"), (1, "acadadmin")])
        with patch.object(sync, "erp_source", erp):
            self.assertEqual(sync.refresh_designations(1), 2)
        self.assertEqual(
            sorted(IamUserDesignation.objects.filter(erp_user_id=1)
                   .values_list("designation", flat=True)),
            ["acadadmin", "staff"])

    def test_a_revoked_post_disappears(self):
        IamUserDesignation.objects.create(erp_user_id=1, designation="acadadmin")
        erp = fake_erp(designations=[(1, "staff")])
        with patch.object(sync, "erp_source", erp):
            sync.refresh_designations(1)
        self.assertEqual(
            list(IamUserDesignation.objects.filter(erp_user_id=1)
                 .values_list("designation", flat=True)),
            ["staff"])

    def test_another_persons_designations_are_left_alone(self):
        IamUser.objects.create(**user(2, "bob"))
        IamUserDesignation.objects.create(erp_user_id=2, designation="student")
        erp = fake_erp(designations=[(1, "acadadmin")])
        with patch.object(sync, "erp_source", erp):
            sync.refresh_designations(1)
        self.assertTrue(
            IamUserDesignation.objects.filter(erp_user_id=2,
                                              designation="student").exists())

    def test_an_unreachable_erp_leaves_the_projection_as_it_was(self):
        def boom(_uid):
            raise RuntimeError("ERP went away")

        erp = fake_erp()
        erp.designations_for_user = boom
        with patch.object(sync, "erp_source", erp):
            self.assertIsNone(sync.refresh_designations(1))
        self.assertTrue(
            IamUserDesignation.objects.filter(erp_user_id=1,
                                              designation="staff").exists())


class FakeMatchesReal(TestCase):
    """The docstring on fake_erp says it must mirror erp_source. This is what
    makes that true rather than aspirational: a fake missing the function the
    sync just started calling makes the sync look tested when it is not."""

    def test_the_fake_offers_everything_the_sync_reads(self):
        from iam import erp_source

        used = {
            name for name in dir(erp_source)
            if not name.startswith("_") and callable(getattr(erp_source, name))
            and getattr(erp_source, name).__module__ == erp_source.__name__
        }
        offered = set(vars(fake_erp()))
        # The fake need not offer helpers the sync never calls, only the ones it
        # already stands in for plus anything newly added beside them.
        missing = {n for n in used if n in {
            "iter_users", "all_user_designations", "all_student_profiles",
            "all_academic_standings", "fetch_password_hash",
            "all_student_programme_roles",
        }} - offered
        self.assertEqual(missing, set())


class StudentProfileProjectionTests(TestCase):
    databases = {"default", "system_db"}

    def test_the_resume_the_portal_holds_is_projected(self):
        """One resume, maintained on the portal's profile page and read here."""
        erp = fake_erp(users=[user(1, "alice")],
                       profiles={1: {"resume_link": "https://drive/x",
                                     "profile_completed": True}})
        with patch.object(sync, "erp_source", erp):
            sync.sync_all()

        alice = IamUser.objects.get(pk=1)
        self.assertEqual(alice.resume_link, "https://drive/x")
        self.assertTrue(alice.profile_completed)

    def test_a_student_with_no_record_upstream_gets_no_resume(self):
        with patch.object(sync, "erp_source", fake_erp(users=[user(1, "alice")])):
            sync.sync_all()
        alice = IamUser.objects.get(pk=1)
        self.assertEqual(alice.resume_link, "")
        self.assertFalse(alice.profile_completed)

    def test_a_removed_resume_is_cleared_not_kept(self):
        """A stale link is worse than none: a recruiter would open the old CV."""
        with patch.object(sync, "erp_source",
                          fake_erp(users=[user(1, "alice")],
                                   profiles={1: {"resume_link": "https://drive/x",
                                                 "profile_completed": True}})):
            sync.sync_all()
        with patch.object(sync, "erp_source",
                          fake_erp(users=[user(1, "alice")],
                                   profiles={1: {"resume_link": "",
                                                 "profile_completed": False}})):
            sync.sync_all()
        self.assertEqual(IamUser.objects.get(pk=1).resume_link, "")


class MissingProfileTableTests(ErpSchemaTestCase):
    """The public dev dump carries the core ERP tables but not these two — the
    exact fixture a lab restores. Absence of a table this projection reads must
    degrade the two fields it fills, not fail the sync that projects everyone.

    A regression: this projection used to run unguarded as the first step of
    sync_all, so one table a fixture happened not to carry took every user
    down with it, on a database that otherwise had everything it needed.
    """

    def setUp(self):
        self.erp = ErpFactory(seed=7)

    def test_the_other_table_still_contributes(self):
        from django.db.utils import ProgrammingError

        from iam import erp_source

        with patch("api.models.batches.StudentBatchUpload.objects") as broken:
            broken.exclude.side_effect = ProgrammingError(
                'relation "programme_curriculum_studentbatchupload" does not exist')
            profiles = erp_source.all_student_profiles()

        self.assertIsInstance(profiles, dict)

    def test_sync_identity_still_projects_every_user(self):
        student = self.erp.student()
        faculty = self.erp.employee(kind="faculty", department="CSE")

        from django.db.utils import ProgrammingError

        with patch("api.models.batches.StudentBatchUpload.objects") as broken:
            broken.exclude.side_effect = ProgrammingError("relation does not exist")
            run = sync.sync_all()

        self.assertEqual(run.status, "succeeded")
        self.assertTrue(IamUser.objects.filter(pk=student.id).exists())
        self.assertTrue(IamUser.objects.filter(pk=faculty.id).exists())
        # The field this table would have filled is simply absent, not an error.
        self.assertEqual(IamUser.objects.get(pk=student.id).resume_link, "")


class RolePolicyExceptionTests(TestCase):
    databases = {"default", "system_db"}

    def _sync(self, **settings_kw):
        # Uncatalogued roles are allowed, so the rule must exist to be broken.
        IamRole.objects.create(code="acadadmin", label="Academic Administrator",
                               category="office", allowed_kinds="faculty,staff",
                               is_active=True)
        erp = fake_erp(users=[user(1, "intern", kind="student")],
                       designations=[(1, "acadadmin")])
        with self.settings(IAM_ENFORCE_ROLE_POLICY=True, **settings_kw), \
                patch.object(sync, "erp_source", erp):
            sync.sync_all()

    def test_a_role_the_catalogue_refuses_is_withheld(self):
        self._sync(IAM_ROLE_POLICY_EXCEPTIONS="")
        self.assertFalse(IamUserDesignation.objects.filter(
            erp_user_id=1, designation="acadadmin").exists())

    def test_a_named_exception_is_allowed_through(self):
        self._sync(IAM_ROLE_POLICY_EXCEPTIONS="intern:acadadmin")
        self.assertTrue(IamUserDesignation.objects.filter(
            erp_user_id=1, designation="acadadmin").exists())

    def test_an_exception_is_still_reported(self):
        """Granted and forgotten must stay visible on the list somebody reads."""
        self._sync(IAM_ROLE_POLICY_EXCEPTIONS="intern:acadadmin")
        violation = IamRoleViolation.objects.get(erp_user_id=1)
        self.assertEqual(violation.designation, "acadadmin")
        self.assertFalse(violation.enforced)

    def test_an_exception_does_not_cover_a_different_role(self):
        self._sync(IAM_ROLE_POLICY_EXCEPTIONS="intern:Dean Academic")
        self.assertFalse(IamUserDesignation.objects.filter(
            erp_user_id=1, designation="acadadmin").exists())
