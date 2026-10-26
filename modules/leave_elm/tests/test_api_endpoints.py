from decimal import Decimal
from datetime import date
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from modules.leave_elm.models import (
    LeaveType,
    LeaveBalance,
    LeaveApplication,
    HolidayCalendar,
)


@pytest.fixture(autouse=True)
def seed_data(db):
    LeaveType.objects.all().delete()
    HolidayCalendar.objects.all().delete()

    cl = LeaveType.objects.create(code='CL', name='Casual Leave', max_days_per_year=Decimal('8.0'), is_carry_forward=False)
    el = LeaveType.objects.create(code='EL', name='Earned Leave', max_days_per_year=Decimal('30.0'), is_carry_forward=True)
    vl = LeaveType.objects.create(code='VL', name='Vacation Leave', max_days_per_year=Decimal('60.0'), is_carry_forward=False)

    HolidayCalendar.objects.create(date=date(2026, 10, 15), name='RH Day', is_restricted_holiday=True, year=2026)
    return {'CL': cl, 'EL': el, 'VL': vl}


@pytest.mark.django_db
class TestELMAPIEndpoints:
    def setup_method(self):
        self.client = APIClient()

    def test_list_leave_types_api(self):
        """GET /api/v1/leave/types/ returns list of active leave categories."""
        res = self.client.get('/api/v1/leave/types/')
        assert res.status_code == status.HTTP_200_OK
        items = res.data.get('results', res.data) if isinstance(res.data, dict) else res.data
        codes = [item['code'] for item in items]
        assert 'CL' in codes
        assert 'EL' in codes

    def test_apply_leave_api(self):
        """POST /api/v1/leave/applications/ creates application and computes days."""
        payload = {
            'applicant_username': 'john_doe',
            'leave_type_code': 'CL',
            'start_date': '2026-11-02',
            'end_date': '2026-11-03',
            'half_day': False,
            'reason': 'Medical consultation',
            'station_leave': False
        }
        res = self.client.post('/api/v1/leave/applications/', payload, format='json')
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data['applicant_username'] == 'john_doe'
        assert Decimal(str(res.data['days_count'])) == Decimal('2.0')
        assert res.data['status'] == 'PENDING_UNIT_HEAD'

    def test_withdraw_action_api(self):
        """POST /api/v1/leave/applications/{id}/withdraw/ marks status WITHDRAWN."""
        app = LeaveApplication.objects.create(
            applicant_username='john_doe',
            leave_type=LeaveType.objects.get(code='CL'),
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 2),
            days_count=Decimal('1.0'),
            status='PENDING_UNIT_HEAD'
        )
        res = self.client.post(
            f'/api/v1/leave/applications/{app.id}/withdraw/',
            {'remarks': 'Changed mind'},
            HTTP_X_USER='john_doe'
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.data['status'] == 'WITHDRAWN'

    def test_substitute_consent_action_api(self):
        """POST /api/v1/leave/applications/{id}/substitute_consent/ gates approval."""
        app = LeaveApplication.objects.create(
            applicant_username='john_doe',
            leave_type=LeaveType.objects.get(code='CL'),
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 5),
            days_count=Decimal('1.0'),
            substitute_username='jane_smith',
            substitute_status='PENDING',
            status='SUBSTITUTE_PENDING'
        )
        res = self.client.post(
            f'/api/v1/leave/applications/{app.id}/substitute_consent/',
            {'accept': True, 'remarks': 'Will cover lectures'},
            HTTP_X_USER='jane_smith'
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.data['status'] == 'PENDING_UNIT_HEAD'
        assert res.data['substitute_status'] == 'ACCEPTED'

    def test_unit_head_and_higher_sanction_api(self):
        """Unit head recommendation and higher sanction approval."""
        app = LeaveApplication.objects.create(
            applicant_username='john_doe',
            leave_type=LeaveType.objects.get(code='EL'),
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 12),
            days_count=Decimal('3.0'),
            status='PENDING_UNIT_HEAD'
        )
        LeaveBalance.objects.create(
            username='john_doe',
            leave_type=app.leave_type,
            year=2026,
            balance=Decimal('30.0'),
            credited=Decimal('30.0'),
            utilized=Decimal('0.0')
        )

        # Unit head recommends
        res_uh = self.client.post(
            f'/api/v1/leave/applications/{app.id}/unit_head_decision/',
            {'decision': 'RECOMMEND', 'remarks': 'Strongly recommended'},
            HTTP_X_USER='hod_cse'
        )
        assert res_uh.status_code == status.HTTP_200_OK
        assert res_uh.data['status'] == 'PENDING_HIGHER_SANCTION'

        # Higher sanction approves
        res_hs = self.client.post(
            f'/api/v1/leave/applications/{app.id}/higher_sanction_decision/',
            {'decision': 'APPROVE', 'remarks': 'Approved by Dean'},
            HTTP_X_USER='dean_academic'
        )
        assert res_hs.status_code == status.HTTP_200_OK
        assert res_hs.data['status'] == 'APPROVED'

    def test_convert_vl_to_el_api(self):
        """POST /api/v1/leave/convert-vl-to-el/ converts 2 VL : 1 EL."""
        vl_type = LeaveType.objects.get(code='VL')
        LeaveBalance.objects.create(
            username='prof_albus',
            leave_type=vl_type,
            year=2026,
            balance=Decimal('40.0'),
            credited=Decimal('60.0'),
            utilized=Decimal('20.0')
        )

        res = self.client.post('/api/v1/leave/convert-vl-to-el/', {
            'faculty_username': 'prof_albus',
            'year': 2026
        })
        assert res.status_code == status.HTTP_200_OK
        assert res.data['status'] == 'success'
        assert Decimal(res.data['converted_el_days']) == Decimal('20.0')
