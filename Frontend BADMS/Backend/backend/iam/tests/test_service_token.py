"""Service credentials — the server-to-server path.

The invariant under test: a machine and a person are different kinds of caller
and the IAM must never confuse one for the other in either direction.
"""
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from iam.models import IamServiceToken, IamToken, IamUser


class ServiceTokenModelTests(TestCase):
    databases = {"default", "system_db"}

    def test_the_raw_value_is_never_stored(self):
        row, raw = IamServiceToken.issue("fusion-integrated")
        self.assertTrue(raw.startswith("fsvc_"))
        self.assertNotEqual(row.token_hash, raw)
        self.assertNotIn(raw, row.token_hash)
        # And nothing anywhere in the row holds it.
        self.assertNotIn(raw, str(row.__dict__))

    def test_resolve_accepts_the_issued_value(self):
        row, raw = IamServiceToken.issue("platform")
        self.assertEqual(IamServiceToken.resolve(raw), row)

    def test_resolve_rejects_unknown_revoked_and_malformed(self):
        row, raw = IamServiceToken.issue("platform")
        self.assertIsNone(IamServiceToken.resolve("fsvc_not-a-real-token"))
        self.assertIsNone(IamServiceToken.resolve(""))
        self.assertIsNone(IamServiceToken.resolve(None))
        # A value without the prefix is refused before any DB lookup.
        self.assertIsNone(IamServiceToken.resolve(raw[len("fsvc_"):]))

        row.is_active = False
        row.save()
        self.assertIsNone(IamServiceToken.resolve(raw))

    def test_rotate_replaces_the_value_and_keeps_the_name(self):
        row, old = IamServiceToken.issue("platform")
        new = row.rotate()

        self.assertNotEqual(new, old)
        self.assertIsNone(IamServiceToken.resolve(old))
        self.assertEqual(IamServiceToken.resolve(new), row)
        self.assertEqual(IamServiceToken.objects.filter(name="platform").count(), 1)

    def test_rotate_revives_a_revoked_token(self):
        """The name is unique, so rotation is the only way back from --revoke."""
        row, _ = IamServiceToken.issue("platform")
        IamServiceToken.objects.filter(pk=row.pk).update(is_active=False)
        row.refresh_from_db()

        new = row.rotate()
        self.assertEqual(IamServiceToken.resolve(new), row)

    def test_two_tokens_never_collide(self):
        _, a = IamServiceToken.issue("one")
        _, b = IamServiceToken.issue("two")
        self.assertNotEqual(a, b)

    def test_touch_is_throttled_to_a_minute(self):
        """A write per request is the pattern that made the legacy app slow."""
        row, _ = IamServiceToken.issue("platform")
        row.touch()
        row.refresh_from_db()
        first = row.last_used_at
        self.assertIsNotNone(first)

        row.touch()                                   # immediately again
        row.refresh_from_db()
        self.assertEqual(row.last_used_at, first)     # no second write

        IamServiceToken.objects.filter(pk=row.pk).update(
            last_used_at=timezone.now() - timedelta(minutes=2))
        row.refresh_from_db()
        row.touch()
        row.refresh_from_db()
        self.assertGreater(row.last_used_at, first)


class ServiceTokenApiTests(APITestCase):
    databases = {"default", "system_db"}

    def setUp(self):
        IamUser.objects.create(erp_user_id=1, username="alice",
                               display_name="Alice", kind="student",
                               password_hash=make_password("pw"))
        self.row, self.raw = IamServiceToken.issue("fusion-integrated")

    def get(self, path, auth=None):
        return self.client.get(path, **({"HTTP_AUTHORIZATION": auth} if auth else {}))

    def test_directory_accepts_a_service_credential(self):
        r = self.get("/api/iam/v1/directory/users?ids=1", f"Service {self.raw}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"][0]["username"], "alice")

    def test_me_is_unreachable_by_a_machine(self):
        """There is no person behind a service token, so there is no /me to
        serve. This is enforced by which auth classes the view lists."""
        self.assertEqual(self.get("/api/iam/v1/me", f"Service {self.raw}").status_code,
                         401)

    def test_a_service_token_is_rejected_under_the_token_scheme(self):
        """Schemes do not cross: presenting a machine credential as a user
        session must not work, or the two pools have effectively merged."""
        self.assertEqual(
            self.get("/api/iam/v1/directory/users?ids=1",
                     f"Token {self.raw}").status_code, 401)

    def test_a_user_session_is_rejected_under_the_service_scheme(self):
        token = IamToken.issue(erp_user_id=1, username="alice")
        self.assertEqual(
            self.get("/api/iam/v1/directory/users?ids=1",
                     f"Service {token.raw_key}").status_code, 401)

    def test_a_revoked_credential_stops_working_immediately(self):
        self.row.is_active = False
        self.row.save()
        self.assertEqual(
            self.get("/api/iam/v1/directory/users?ids=1",
                     f"Service {self.raw}").status_code, 401)

    def test_no_credential_is_rejected(self):
        self.assertEqual(self.get("/api/iam/v1/directory/users?ids=1").status_code,
                         401)

    def test_a_user_session_still_reaches_the_directory(self):
        token = IamToken.issue(erp_user_id=1, username="alice")
        r = self.get("/api/iam/v1/directory/users?ids=1", f"Token {token.raw_key}")
        self.assertEqual(r.status_code, 200)

    def test_ids_must_be_integers(self):
        r = self.get("/api/iam/v1/directory/users?ids=1,abc", f"Service {self.raw}")
        self.assertEqual(r.status_code, 400)
