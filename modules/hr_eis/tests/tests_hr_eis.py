# modules/hr_eis/tests/test_hr_eis.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date
from modules.hr_eis.models import EmployeeProfile, WorkExperience

User = get_user_model()


class EmployeeProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_lecturer',
            email='lecturer@iiitdmj.ac.in',
            password='password123'
        )
        self.profile = EmployeeProfile.objects.create(
            user=self.user,
            pf_number='PF9901',
            designation='ASST_PROF',
            department='CSE',
            date_of_joining=date(2023, 8, 1),
            about_me='Assistant Professor in CSE Department'
        )

    def test_profile_str_representation(self):
        expected_str = "test_lecturer (PF9901) - ASST_PROF"
        self.assertEqual(str(self.profile), expected_str)

    def test_unique_pf_number_constraint(self):
        another_user = User.objects.create_user(username='another_emp', password='password123')
        with self.assertRaises(Exception):
            EmployeeProfile.objects.create(
                user=another_user,
                pf_number='PF9901',
                designation='STAFF',
                department='ECE',
                date_of_joining=date(2024, 1, 1)
            )


class HREISAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.emp_user = User.objects.create_user(username='john_doe', password='password123')
        self.emp_profile = EmployeeProfile.objects.create(
            user=self.emp_user,
            pf_number='PF1001',
            designation='ASST_PROF',
            department='CSE',
            date_of_joining=date(2022, 1, 1)
        )

    def test_unauthenticated_access_denied(self):
        response = self.client.get('/api/v1/hr-eis/profiles/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_my_profile_custom_action(self):
        self.client.force_authenticate(user=self.emp_user)
        response = self.client.get('/api/v1/hr-eis/profiles/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pf_number'], 'PF1001')

    def test_work_experience_serializer_date_validation(self):
        self.client.force_authenticate(user=self.emp_user)
        invalid_payload = {
            'organization': 'Tech Corp',
            'position': 'Engineer',
            'start_date': '2024-06-01',
            'end_date': '2023-01-01'
        }
        response = self.client.post('/api/v1/hr-eis/experiences/', invalid_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('end_date', response.data)