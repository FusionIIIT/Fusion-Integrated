"""Regression tests: a staff account created through Add Staff must be listed
as staff.

`add_individual_staff` used to persist the final profile row with
`GlobalsFaculty`, so the new account landed in `globals_faculty` while the
staff listing (`GET /users/?type=staff`, used by the User Directory and the
Delete User page) reads `globals_staff`. The UI reported success and the person
never appeared. All data below is synthetic.
"""
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import (
    GlobalsDepartmentinfo,
    GlobalsDesignation,
    GlobalsExtrainfo,
    GlobalsFaculty,
    Staff,
)


class AddStaffThenListTests(APITestCase):
    # `default` holds the ERP shadow tables, `system_db` the operator accounts
    # that authenticate the request (see ConsoleAPITestCase in
    # test_backup_restore.py).
    databases = {"default", "system_db"}

    def setUp(self):
        operator = User.objects.create_user(
            username="operator", password="console-test-password", is_staff=True
        )
        self.client.force_authenticate(user=operator)

        # add_individual_* look up the 'CSE' department by name.
        self.department = GlobalsDepartmentinfo.objects.create(name="CSE")
        self.designation = GlobalsDesignation.objects.create(
            name="TEST ROLE", full_name="Test Role", type="administrative"
        )

    def _add_staff(self, username="zztest01", **overrides):
        payload = {
            "username": username,
            "first_name": "Test",
            "last_name": "Staff",
            "sex": "Male",
            "designation": self.designation.id,
        }
        payload.update(overrides)
        return self.client.post(reverse("add_individual_staff"), payload, format="json")

    def _list(self, user_type):
        response = self.client.get(reverse("user-list"), {"type": user_type})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.json()

    def test_new_staff_is_persisted_as_staff_not_faculty(self):
        response = self._add_staff()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)

        extra_info = GlobalsExtrainfo.objects.get(id="zztest01")
        self.assertEqual(extra_info.user_type, "staff")
        self.assertTrue(Staff.objects.filter(id=extra_info).exists())
        self.assertFalse(GlobalsFaculty.objects.filter(id=extra_info).exists())

    def test_new_staff_appears_in_the_staff_listing(self):
        self._add_staff()

        staff = self._list("staff")

        self.assertEqual([row["username"] for row in staff], ["zztest01"])
        self.assertEqual(staff[0]["full_name"], "Test Staff")
        self.assertEqual(staff[0]["user_type"], "staff")
        self.assertEqual(staff[0]["designations"], ["TEST ROLE"])

    def test_new_staff_does_not_appear_in_the_faculty_listing(self):
        self._add_staff()

        self.assertEqual(self._list("faculty"), [])

    def test_staff_and_faculty_listings_stay_separate(self):
        """The fix must not break the neighbouring flow: Add Faculty still
        lands in the faculty listing, and each listing shows only its own."""
        self._add_staff(username="zztest01")
        response = self.client.post(
            reverse("add_individual_faculty"),
            {
                "username": "zztest02",
                "first_name": "Test",
                "last_name": "Faculty",
                "sex": "Female",
                "designation": self.designation.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)

        self.assertEqual([r["username"] for r in self._list("staff")], ["zztest01"])
        self.assertEqual([r["username"] for r in self._list("faculty")], ["zztest02"])

    def test_staff_listing_filters_still_work(self):
        """Existing listing behaviour: filter by designation and by gender."""
        other = GlobalsDesignation.objects.create(
            name="OTHER ROLE", full_name="Other Role", type="administrative"
        )
        self._add_staff(username="zztest01", sex="Male")
        self._add_staff(username="zztest03", sex="Female", designation=other.id)

        by_role = self.client.get(
            reverse("user-list"), {"type": "staff", "designation": "other role"}
        ).json()
        by_gender = self.client.get(
            reverse("user-list"), {"type": "staff", "gender": "M"}
        ).json()

        self.assertEqual([r["username"] for r in by_role], ["zztest03"])
        self.assertEqual([r["username"] for r in by_gender], ["zztest01"])

    def test_listing_rejects_an_unknown_type(self):
        response = self.client.get(reverse("user-list"), {"type": "nonsense"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
