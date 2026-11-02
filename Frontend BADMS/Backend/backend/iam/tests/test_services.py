"""Authentication, RBAC and directory — all served from the projection.

The through-line: none of these tests create an ERP table, and none of them
mock one either. If serving a request needed the ERP, these would fail.
"""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.utils import timezone

from iam import services
from iam.models import (IamDesignationModule, IamModule, IamNavItem, IamToken,
                        IamUser, IamUserDesignation, LoginAttempt,
                        RolePermission, SyncRun)

PASSWORD = "correct-horse-battery"


def make_user(uid=1, username="alice", password=PASSWORD, **over):
    fields = {
        "erp_user_id": uid, "username": username, "display_name": username.title(),
        "kind": "student", "is_active": True,
        "password_hash": make_password(password) if password else "",
    }
    fields.update(over)
    return IamUser.objects.create(**fields)


class AuthenticationTests(TestCase):
    databases = {"default", "system_db"}

    def test_login_succeeds_against_the_synced_hash(self):
        make_user()
        token = services.authenticate("alice", PASSWORD)
        self.assertIsNotNone(token)
        self.assertEqual(token.erp_user_id, 1)
        self.assertTrue(token.is_live)
        self.assertEqual(LoginAttempt.objects.get().outcome, "success")

    def test_username_match_is_case_insensitive(self):
        make_user(username="Alice")
        self.assertIsNotNone(services.authenticate("ALICE", PASSWORD))

    def test_wrong_password_fails_closed_when_the_erp_is_unreachable(self):
        """_verify() falls back to a live ERP read so a password reset takes
        effect before the next sync. When that read raises, the answer is no."""
        make_user()
        with patch("iam.sync.refresh_password_hash",
                   side_effect=RuntimeError("ERP down")):
            self.assertIsNone(services.authenticate("alice", "wrong"))
        self.assertEqual(LoginAttempt.objects.get().outcome, "bad_password")

    def test_a_password_reset_in_the_erp_works_before_the_next_sync(self):
        make_user(password="old-password")
        with patch("iam.sync.refresh_password_hash",
                   return_value=make_password("new-password")):
            self.assertIsNotNone(services.authenticate("alice", "new-password"))

    def test_unknown_user_and_wrong_password_are_indistinguishable(self):
        make_user()
        self.assertIsNone(services.authenticate("nobody", "x"))
        with patch("iam.sync.refresh_password_hash", return_value=None):
            self.assertIsNone(services.authenticate("alice", "wrong"))
        outcomes = set(LoginAttempt.objects.values_list("outcome", flat=True))
        self.assertEqual(outcomes, {"unknown_user", "bad_password"})

    def test_an_inactive_user_cannot_sign_in(self):
        make_user(is_active=False)
        self.assertIsNone(services.authenticate("alice", PASSWORD))
        self.assertEqual(LoginAttempt.objects.get().outcome, "inactive")

    def test_a_user_with_no_synced_hash_cannot_sign_in_with_an_empty_password(self):
        make_user(password=None)              # password_hash = ""
        with patch("iam.sync.refresh_password_hash", return_value=None):
            self.assertIsNone(services.authenticate("alice", ""))

    def test_lockout_after_repeated_failures(self):
        make_user()
        for _ in range(5):
            LoginAttempt.objects.create(username="alice", outcome="bad_password")
        with self.assertRaises(services.Locked) as ctx:
            services.check_lockout("alice")
        self.assertEqual(ctx.exception.minutes, 1)

    def test_lockout_escalates_and_finally_needs_an_admin(self):
        for _ in range(15):
            LoginAttempt.objects.create(username="alice", outcome="bad_password")
        with self.assertRaises(services.Locked) as ctx:
            services.check_lockout("alice")
        self.assertIsNone(ctx.exception.minutes)

    def test_old_failures_do_not_count(self):
        for _ in range(15):
            LoginAttempt.objects.create(username="alice", outcome="bad_password")
        LoginAttempt.objects.update(at=timezone.now() - timedelta(hours=2))
        services.check_lockout("alice")       # does not raise

    def test_resolve_token_rejects_expired_and_revoked(self):
        make_user()
        live = IamToken.issue(erp_user_id=1, username="alice")
        self.assertIsNotNone(services.resolve_token(live.raw_key))

        expired = IamToken.issue(erp_user_id=1, username="alice")
        IamToken.objects.filter(pk=expired.key).update(
            expires_at=timezone.now() - timedelta(minutes=1))
        self.assertIsNone(services.resolve_token(expired.raw_key))

        revoked = IamToken.issue(erp_user_id=1, username="alice")
        revoked.revoke()
        self.assertIsNone(services.resolve_token(revoked.raw_key))
        self.assertIsNone(services.resolve_token("no-such-token"))

    def test_the_bearer_value_is_not_stored(self):
        """A dump of system_db must not yield a working session."""
        make_user()
        token = IamToken.issue(erp_user_id=1, username="alice")

        stored = set(IamToken.objects.values_list("key", flat=True))
        self.assertNotIn(token.raw_key, stored)
        self.assertEqual(token.key, IamToken.hash_raw(token.raw_key))
        # And the digest itself is not a credential.
        self.assertIsNone(services.resolve_token(token.key))

    def test_a_reloaded_row_carries_no_raw_key(self):
        """`raw_key` exists on the instance that minted the token and nowhere
        else — reading the row back must not resurrect it."""
        make_user()
        token = IamToken.issue(erp_user_id=1, username="alice")
        self.assertEqual(IamToken.objects.get(pk=token.key).raw_key, "")


class SessionTests(TestCase):
    databases = {"default", "system_db"}

    def setUp(self):
        self.user = make_user(uid=7, username="asha")
        IamUserDesignation.objects.create(erp_user_id=7, designation="placement_coord")
        IamDesignationModule.objects.create(designation="placement_coord",
                                            module_code="placement_cell")
        IamDesignationModule.objects.create(designation="student",
                                            module_code="placement_cell")
        RolePermission.objects.create(designation="placement_coord",
                                      permission="placement_cell.offer.issue")

    def test_session_payload(self):
        token = IamToken.issue(erp_user_id=7, username="asha")
        s = services.build_session(token)

        self.assertEqual(s["user"]["username"], "asha")
        self.assertEqual(s["user"]["id"], 7)
        self.assertEqual(s["modules"], ["placement_cell"])
        self.assertEqual(s["permissions"], ["placement_cell.offer.issue"])
        self.assertIn("identity_synced_at", s)

    def test_a_student_gets_the_student_role_implicitly(self):
        """Students hold no HoldsDesignation row in the ERP — their user_type
        IS the role. Without this they would see an empty sidebar."""
        token = IamToken.issue(erp_user_id=7, username="asha")
        self.assertIn("student", services.build_session(token)["roles"])

    def test_a_deactivated_user_gets_no_session_even_with_a_live_token(self):
        token = IamToken.issue(erp_user_id=7, username="asha")
        IamUser.objects.filter(pk=7).update(is_active=False)
        self.assertEqual(services.build_session(token), {})

    def test_no_designations_means_no_modules_not_all_modules(self):
        """The basic role is held by definition, so `roles` is never empty — but
        nothing is granted to it here, and an ungranted role opens nothing."""
        make_user(uid=8, username="ghost", kind="staff")
        token = IamToken.issue(erp_user_id=8, username="ghost")
        s = services.build_session(token)
        self.assertEqual(s["roles"], ["staff"])
        self.assertEqual(s["modules"], [])
        self.assertEqual(s["permissions"], [])
        self.assertEqual(s["active_role"], "staff")


class LoginRefreshesRolesTests(TestCase):
    """A newly assigned post must appear — without making every login pay."""
    databases = {"default", "system_db"}

    def setUp(self):
        self.user = make_user(uid=11, username="asha")

    def _age(self, seconds):
        IamUser.objects.filter(pk=11).update(
            synced_at=timezone.now() - timedelta(seconds=seconds))

    def test_a_fresh_projection_costs_the_login_nothing(self):
        """The timer ran minutes ago, so the refresh would find nothing."""
        self._age(60)
        with patch("iam.sync.refresh_designations") as refresh:
            self.assertIsNotNone(services.authenticate("asha", PASSWORD))
        refresh.assert_not_called()

    def test_a_stalled_timer_makes_login_re_read_the_posts(self):
        self._age(7200)
        with patch("iam.sync.refresh_designations", return_value=2) as refresh:
            services.authenticate("asha", PASSWORD)
        refresh.assert_called_once_with(11)

    def test_a_successful_refresh_is_not_repeated_on_the_next_login(self):
        self._age(7200)
        with patch("iam.sync.refresh_designations", return_value=2):
            services.authenticate("asha", PASSWORD)
        with patch("iam.sync.refresh_designations") as again:
            services.authenticate("asha", PASSWORD)
        again.assert_not_called()

    def test_an_unreachable_erp_still_lets_the_person_in(self):
        self._age(7200)
        with patch("iam.sync.refresh_designations", return_value=None):
            self.assertIsNotNone(services.authenticate("asha", PASSWORD))

    def test_a_failed_login_does_not_touch_the_projection(self):
        self._age(7200)
        with patch("iam.sync.refresh_designations") as refresh:
            self.assertIsNone(services.authenticate("asha", "wrong-password"))
        refresh.assert_not_called()

    def test_the_refresh_can_be_turned_off_entirely(self):
        self._age(7200)
        with self.settings(IAM_REFRESH_ROLES_AFTER_SECONDS=0):
            with patch("iam.sync.refresh_designations") as refresh:
                services.authenticate("asha", PASSWORD)
        refresh.assert_not_called()


class RoleScopedNavigationTests(TestCase):
    """A module granted to two of somebody's roles must not show one role's
    screens while they are acting as the other."""
    databases = {"default", "system_db"}

    def setUp(self):
        make_user(uid=9, username="vikrant")
        IamUserDesignation.objects.create(erp_user_id=9, designation="acadadmin")
        for designation in ("student", "acadadmin"):
            IamDesignationModule.objects.create(designation=designation,
                                                module_code="placement_cell")
        IamDesignationModule.objects.create(designation="acadadmin",
                                            module_code="leave")
        RolePermission.objects.create(designation="student",
                                      permission="placement_cell.application.apply")
        RolePermission.objects.create(designation="acadadmin",
                                      permission="placement_cell.application.view")
        RolePermission.objects.create(designation="acadadmin",
                                      permission="leave.request.create")

        placement = IamModule.objects.create(
            code="placement_cell", label="Placement Cell", base_path="/placement",
            nav_section="Placement", status="active", app="integrated",
            source="manifest:integrated")
        IamNavItem.objects.create(
            module=placement, code="placement.mine", label="My Applications",
            to="/placement/mine", source="manifest:integrated",
            required_permission="placement_cell.application.apply")
        IamNavItem.objects.create(
            module=placement, code="placement.applications", label="Applications",
            to="/placement/applications", source="manifest:integrated",
            required_permission="placement_cell.application.view")
        leave = IamModule.objects.create(
            code="leave", label="Leave", base_path="/leave", nav_section="Leave",
            status="active", app="integrated", source="manifest:integrated")
        IamNavItem.objects.create(
            module=leave, code="leave.apply", label="Apply", to="/leave/apply",
            source="manifest:integrated",
            required_permission="leave.request.create")

    def _links(self, navigation, module_code):
        for section in navigation:
            for item in section["items"]:
                if item["code"] == module_code:
                    return [link["code"] for link in item.get("links", [])]
        return None

    def test_an_office_does_not_draw_the_student_screens(self):
        by_role = services.navigation_by_designation(["student", "acadadmin"])
        self.assertEqual(self._links(by_role["acadadmin"], "placement_cell"),
                         ["placement.applications"])

    def test_a_student_does_not_draw_the_office_screens(self):
        by_role = services.navigation_by_designation(["student", "acadadmin"])
        self.assertEqual(self._links(by_role["student"], "placement_cell"),
                         ["placement.mine"])

    def test_a_module_granted_to_one_role_is_absent_from_the_other(self):
        by_role = services.navigation_by_designation(["student", "acadadmin"])
        self.assertIsNone(self._links(by_role["student"], "leave"))
        self.assertIsNotNone(self._links(by_role["acadadmin"], "leave"))

    def test_the_session_carries_the_breakdown_beside_the_union(self):
        token = IamToken.issue(erp_user_id=9, username="vikrant")
        session = services.build_session(token)
        self.assertEqual(sorted(session["navigation_by_role"]),
                         ["acadadmin", "student"])
        self.assertEqual(
            self._links(session["navigation_by_role"]["acadadmin"],
                        "placement_cell"),
            ["placement.applications"])


class DirectoryTests(TestCase):
    databases = {"default", "system_db"}

    def setUp(self):
        make_user(uid=1, username="alice", discipline="CSE")
        make_user(uid=2, username="bob", discipline="ECE")
        make_user(uid=3, username="carol", kind="faculty", is_active=False)

    def test_batched_lookup_is_one_query_regardless_of_size(self):
        with self.assertNumQueries(1, using="system_db"):
            rows = services.directory_users([1, 2])
        self.assertEqual([r["username"] for r in rows], ["alice", "bob"])

    def test_a_missing_id_is_simply_absent(self):
        rows = services.directory_users([1, 999])
        self.assertEqual([r["user_id"] for r in rows], [1])

    def test_no_ids_means_no_query_and_no_rows(self):
        with self.assertNumQueries(0, using="system_db"):
            self.assertEqual(services.directory_users([]), [])

    def test_search_excludes_inactive_people(self):
        names = [r["username"] for r in services.search_directory()]
        self.assertNotIn("carol", names)

    def test_search_filters_by_kind_and_limits(self):
        make_user(uid=4, username="dev", kind="faculty")
        self.assertEqual([r["username"] for r in
                          services.search_directory(kind="faculty")], ["dev"])
        self.assertEqual(len(services.search_directory(limit=1)), 1)

    def test_freshness_reports_unsynced_before_any_run(self):
        self.assertEqual(services.identity_freshness()["synced"], False)

    def test_freshness_reports_age_after_a_successful_run(self):
        SyncRun.objects.create(status="succeeded", finished_at=timezone.now())
        f = services.identity_freshness()
        self.assertTrue(f["synced"])
        self.assertLess(f["age_seconds"], 5)
        self.assertEqual(f["users"], 2)       # carol is inactive
