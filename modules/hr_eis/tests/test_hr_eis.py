# modules/hr_eis/tests/test_hr_eis.py
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status
from modules.hr_eis.models import EmployeeProfile, WorkExperience

User = get_user_model()


class EmployeeProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="prof_sharma",
            email="sharma@iiitdmj.ac.in",
            password="password123",
        )
        self.profile = EmployeeProfile.objects.create(
            user=self.user,
            pf_number="PF9001",
            designation="PROFESSOR",
            department="CSE",
            date_of_joining=date(2020, 1, 15),
            about_me="Professor in Computer Science",
        )

    def test_str_representation(self):
        expected = "prof_sharma (PF9001) - PROFESSOR"
        self.assertEqual(str(self.profile), expected)

    def test_pf_number_uniqueness(self):
        another_user = User.objects.create_user(
            username="prof_verma", email="verma@iiitdmj.ac.in", password="password123"
        )
        with self.assertRaises(Exception):
            EmployeeProfile.objects.create(
                user=another_user,
                pf_number="PF9001",
                designation="ASSOC_PROF",
                department="ECE",
                date_of_joining=date(2021, 6, 1),
            )

    def test_invalid_designation_rejected(self):
        another_user = User.objects.create_user(
            username="invalid_desig_user", password="password123"
        )
        profile = EmployeeProfile(
            user=another_user,
            pf_number="PF9002",
            designation="CHANCELLOR",
            department="CSE",
            date_of_joining=date(2022, 1, 1),
        )
        with self.assertRaises(ValidationError):
            profile.clean()


class WorkExperienceModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="dr_singh", password="password123"
        )
        self.profile = EmployeeProfile.objects.create(
            user=self.user,
            pf_number="PF9003",
            designation="ASST_PROF",
            department="ME",
            date_of_joining=date(2022, 7, 1),
        )

    def test_valid_work_experience(self):
        exp = WorkExperience.objects.create(
            employee=self.profile,
            organization="IIT Bombay",
            position="Postdoc Fellow",
            start_date=date(2020, 1, 1),
            end_date=date(2022, 6, 30),
            description="Robotics Research",
        )
        self.assertEqual(str(exp), "Postdoc Fellow at IIT Bombay")

    def test_ongoing_work_experience_null_end_date(self):
        exp = WorkExperience.objects.create(
            employee=self.profile,
            organization="IIITDM Jabalpur",
            position="Assistant Professor",
            start_date=date(2022, 7, 1),
            end_date=None,
        )
        self.assertIsNone(exp.end_date)

    def test_model_level_date_validation_rejected(self):
        exp = WorkExperience(
            employee=self.profile,
            organization="Invalid Corp",
            position="Researcher",
            start_date=date(2023, 1, 1),
            end_date=date(2022, 1, 1),
        )
        with self.assertRaises(ValidationError):
            exp.clean()


class HREISAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Regular faculty user
        self.user = User.objects.create_user(
            username="faculty_user", email="faculty@iiitdmj.ac.in", password="password123"
        )
        self.profile = EmployeeProfile.objects.create(
            user=self.user,
            pf_number="PF1010",
            designation="ASST_PROF",
            department="CSE",
            date_of_joining=date(2021, 8, 1),
            about_me="Faculty profile",
        )

        # Another faculty user
        self.other_user = User.objects.create_user(
            username="other_faculty", email="other@iiitdmj.ac.in", password="password123"
        )
        self.other_profile = EmployeeProfile.objects.create(
            user=self.other_user,
            pf_number="PF1011",
            designation="ASSOC_PROF",
            department="ECE",
            date_of_joining=date(2019, 3, 1),
        )

        # Staff user
        self.staff_user = User.objects.create_user(
            username="admin_staff", is_staff=True, password="password123"
        )

        # Unprovisioned user (no profile)
        self.unprovisioned_user = User.objects.create_user(
            username="new_user", password="password123"
        )

    def test_unauthenticated_profile_access_denied(self):
        response = self.client.get("/api/v1/hr-eis/profiles/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_experience_access_denied(self):
        response = self.client.get("/api/v1/hr-eis/experiences/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_my_profile_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/hr-eis/profiles/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["pf_number"], "PF1010")
        self.assertEqual(response.data["username"], "faculty_user")

    def test_get_my_profile_not_found(self):
        self.client.force_authenticate(user=self.unprovisioned_user)
        response = self.client.get("/api/v1/hr-eis/profiles/me/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_staff_only_sees_own_profile_in_list(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/hr-eis/profiles/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["pf_number"], "PF1010")

    def test_staff_sees_all_profiles_in_list(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get("/api/v1/hr-eis/profiles/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertGreaterEqual(len(results), 2)

    def test_create_work_experience_success(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "organization": "National Lab",
            "position": "Senior Scientist",
            "start_date": "2018-01-01",
            "end_date": "2021-07-31",
            "description": "High performance computing research",
        }
        response = self.client.post("/api/v1/hr-eis/experiences/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["organization"], "National Lab")
        self.assertTrue(
            WorkExperience.objects.filter(
                employee=self.profile, organization="National Lab"
            ).exists()
        )

    def test_create_work_experience_invalid_dates(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "organization": "Tech Corp",
            "position": "Consultant",
            "start_date": "2024-01-01",
            "end_date": "2023-01-01",
        }
        response = self.client.post("/api/v1/hr-eis/experiences/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_experience_without_profile_returns_400(self):
        self.client.force_authenticate(user=self.unprovisioned_user)
        payload = {
            "organization": "Some Corp",
            "position": "Analyst",
            "start_date": "2022-01-01",
        }
        response = self.client.post("/api/v1/hr-eis/experiences/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_can_view_all_experiences(self):
        WorkExperience.objects.create(
            employee=self.profile,
            organization="Org A",
            position="Engineer",
            start_date=date(2015, 1, 1),
        )
        WorkExperience.objects.create(
            employee=self.other_profile,
            organization="Org B",
            position="Manager",
            start_date=date(2016, 1, 1),
        )

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get("/api/v1/hr-eis/experiences/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 2)
