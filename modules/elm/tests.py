from django.test import TestCase

from rest_framework.test import APIClient

from .models import LeaveCategory, LeaveApplication



class LeaveCategoryModelTest(TestCase):

    def test_create_leave_category(self):

        client = APIClient()

        response = client.post('/api/leave-categories/',
{'code': 'CL', 'name': 'Casual Leave'}, format='json')

        self.assertEqual(response.status_code, 201)

        self.assertEqual(LeaveCategory.objects.count(), 1)



class LeaveApplicationModelTest(TestCase):

    def test_create_leave_application(self):

        client = APIClient()

        response = client.post('/api/leave-applications/', {

            'employee': 1,  # Assuming there's a UserRef with
id=1

            'category': 1,  # Assuming there's a LeaveCategory
with id=1

            'start_date': '2023-10-01',

            'end_date': '2023-10-05',

            'status': 'draft'

        }, format='json')

        self.assertEqual(response.status_code, 201)

        self.assertEqual(LeaveApplication.objects.count(), 1)
