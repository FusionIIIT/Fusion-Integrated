# tests/a8/wf/test_wf_hr_eis.py
"""
Assignment 8 - WF (Workflow) Strategy Tests for hr_eis module.
Source: Problem Statement + Workflows specification.
Design frozen in: a8_design/WF_DESIGN.json
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date

from modules.hr_eis.models import EmployeeProfile, WorkExperience

User = get_user_model()


def get_results(data):
    """Handle both paginated and unpaginated responses."""
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    return data


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def employee_user(db):
    return User.objects.create_user(username='emp_wf_01', password='pass1234')


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(username='staff_wf_01', password='pass1234', is_staff=True)


@pytest.fixture
def employee_profile(db, employee_user):
    return EmployeeProfile.objects.create(
        user=employee_user,
        pf_number='PF-WF-001',
        designation='ASST_PROF',
        department='CSE',
        date_of_joining=date(2022, 1, 1),
    )


@pytest.fixture
def staff_profile(db, staff_user):
    return EmployeeProfile.objects.create(
        user=staff_user,
        pf_number='PF-WF-STAFF',
        designation='PROFESSOR',
        department='ME',
        date_of_joining=date(2016, 1, 1),
    )


# ---------------------------------------------------------------------------
# WF-TC-01: WF-01 profile-view-authenticated - Workflow completes successfully
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_tc01_view_profile_authenticated(api_client, employee_user, employee_profile):
    """WF-TC-01 | source_id: WF-01 profile-view-authenticated | View-profile workflow completes."""
    api_client.force_authenticate(user=employee_user)
    response = api_client.get('/api/v1/hr-eis/profiles/me/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['pf_number'] == 'PF-WF-001'
    assert 'experiences' in response.data


# ---------------------------------------------------------------------------
# WF-TC-02: WF-01 profile-view-unauthenticated - Auth gate blocks the request
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_tc02_view_profile_unauthenticated(api_client, db):
    """WF-TC-02 | source_id: WF-01 profile-view-unauthenticated | Auth gate blocks unauthenticated request."""
    response = api_client.get('/api/v1/hr-eis/profiles/me/')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# WF-TC-03: WF-01 profile-not-found - Workflow reaches not-found terminal state
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_tc03_view_profile_not_found(api_client, db):
    """WF-TC-03 | source_id: WF-01 profile-not-found | Workflow reaches not-found terminal state."""
    user_no_profile = User.objects.create_user(username='no_profile_wf', password='pass1234')
    api_client.force_authenticate(user=user_no_profile)
    response = api_client.get('/api/v1/hr-eis/profiles/me/')
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# WF-TC-04: WF-02 add-experience-valid - Experience creation workflow completes
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_tc04_add_experience_valid(api_client, employee_user, employee_profile):
    """WF-TC-04 | source_id: WF-02 add-experience-valid | Add-experience workflow with valid data completes."""
    api_client.force_authenticate(user=employee_user)
    payload = {
        'organization': 'Valid Labs',
        'position': 'Researcher',
        'start_date': '2018-01-01',
        'end_date': '2021-12-31',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert WorkExperience.objects.filter(organization='Valid Labs').exists()


# ---------------------------------------------------------------------------
# WF-TC-05: WF-02 add-experience-validation-fail - Workflow halts at validation step
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_tc05_add_experience_validation_fail(api_client, employee_user, employee_profile):
    """WF-TC-05 | source_id: WF-02 add-experience-validation-fail | Invalid dates halt workflow at validation."""
    api_client.force_authenticate(user=employee_user)
    payload = {
        'organization': 'Invalid Dates Corp',
        'position': 'Analyst',
        'start_date': '2024-01-01',
        'end_date': '2022-01-01',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not WorkExperience.objects.filter(organization='Invalid Dates Corp').exists()


# ---------------------------------------------------------------------------
# WF-TC-06: WF-02 add-experience-unauthenticated - Auth gate blocks creation
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_tc06_add_experience_unauthenticated(api_client, db):
    """WF-TC-06 | source_id: WF-02 add-experience-unauthenticated | Unauthenticated request blocked at auth gate."""
    payload = {
        'organization': 'Ghost Corp',
        'position': 'Nobody',
        'start_date': '2020-01-01',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# WF-TC-07: WF-03 list-profiles-staff - Staff list-profiles workflow returns all
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_tc07_list_profiles_staff(api_client, staff_user, employee_profile, staff_profile):
    """WF-TC-07 | source_id: WF-03 list-profiles-staff | Staff user workflow returns all profiles."""
    api_client.force_authenticate(user=staff_user)
    response = api_client.get('/api/v1/hr-eis/profiles/')
    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    pf_numbers = [p['pf_number'] for p in results]
    assert 'PF-WF-001' in pf_numbers
    assert 'PF-WF-STAFF' in pf_numbers


# ---------------------------------------------------------------------------
# WF-TC-08: WF-03 list-profiles-non-staff - Non-staff only sees own profile
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_tc08_list_profiles_non_staff(api_client, employee_user, employee_profile, staff_profile):
    """WF-TC-08 | source_id: WF-03 list-profiles-non-staff | Non-staff workflow returns filtered profile."""
    api_client.force_authenticate(user=employee_user)
    response = api_client.get('/api/v1/hr-eis/profiles/')
    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    pf_numbers = [p['pf_number'] for p in results]
    assert pf_numbers == ['PF-WF-001']
    assert 'PF-WF-STAFF' not in pf_numbers


# ---------------------------------------------------------------------------
# WF-TC-09: WF-04 delete-experience-valid - Delete workflow completes
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_tc09_delete_experience_valid(api_client, employee_user, employee_profile):
    """WF-TC-09 | source_id: WF-04 delete-experience-valid | Delete workflow completes; record is removed."""
    exp = WorkExperience.objects.create(
        employee=employee_profile,
        organization='To Be Deleted',
        position='Temp',
        start_date=date(2010, 1, 1),
        end_date=date(2011, 1, 1),
    )
    api_client.force_authenticate(user=employee_user)
    response = api_client.delete(f'/api/v1/hr-eis/experiences/{exp.id}/')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not WorkExperience.objects.filter(id=exp.id).exists()


# ---------------------------------------------------------------------------
# WF-TC-10: WF-05 auto-link-experience-on-create - Experience is auto-linked to profile
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_tc10_auto_link_experience_on_create(api_client, employee_user, employee_profile):
    """WF-TC-10 | source_id: WF-05 auto-link-experience-on-create | Experience is auto-linked to employee profile."""
    api_client.force_authenticate(user=employee_user)
    payload = {
        'organization': 'AutoLink Institute',
        'position': 'Lecturer',
        'start_date': '2022-06-01',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_201_CREATED
    created_exp = WorkExperience.objects.get(id=response.data['id'])
    assert created_exp.employee.user == employee_user
    assert created_exp.employee == employee_profile
