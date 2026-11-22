# tests/a8/uc/test_uc_hr_eis.py
"""
Assignment 8 - UC (Use Case) Strategy Tests for hr_eis module.
Source: Problem Statement + Use Cases specification.
Design frozen in: a8_design/UC_DESIGN.json
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
    return User.objects.create_user(username='emp_uc_01', password='pass1234')


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(username='staff_uc_01', password='pass1234', is_staff=True)


@pytest.fixture
def employee_profile(db, employee_user):
    return EmployeeProfile.objects.create(
        user=employee_user,
        pf_number='PF-UC-001',
        designation='ASSOC_PROF',
        department='ECE',
        date_of_joining=date(2020, 7, 1),
    )


@pytest.fixture
def staff_profile(db, staff_user):
    return EmployeeProfile.objects.create(
        user=staff_user,
        pf_number='PF-UC-STAFF',
        designation='PROFESSOR',
        department='ME',
        date_of_joining=date(2015, 1, 1),
    )


# ---------------------------------------------------------------------------
# UC-TC-01: UC-01 Main Flow - Employee views their own profile
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_tc01_view_profile_main_flow(api_client, employee_user, employee_profile):
    """UC-TC-01 | source_id: UC-01 Main Flow | Employee views own profile successfully."""
    api_client.force_authenticate(user=employee_user)
    response = api_client.get('/api/v1/hr-eis/profiles/me/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['pf_number'] == 'PF-UC-001'
    assert 'experiences' in response.data


# ---------------------------------------------------------------------------
# UC-TC-02: UC-01 Alternative A1 - No profile exists for authenticated user
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_tc02_view_profile_no_profile_exists(api_client, db):
    """UC-TC-02 | source_id: UC-01 Alternative A1 | /me returns 404 when no profile exists."""
    user_no_profile = User.objects.create_user(username='no_profile_uc', password='pass1234')
    api_client.force_authenticate(user=user_no_profile)
    response = api_client.get('/api/v1/hr-eis/profiles/me/')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'Profile not found for logged in user.' in str(response.data)


# ---------------------------------------------------------------------------
# UC-TC-03: UC-01 Alternative A2 - Unauthenticated access denied
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_tc03_view_profile_unauthenticated(api_client, db):
    """UC-TC-03 | source_id: UC-01 Alternative A2 | Unauthenticated user denied at /me."""
    response = api_client.get('/api/v1/hr-eis/profiles/me/')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# UC-TC-04: UC-02 Main Flow - Employee adds a new work experience
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_tc04_add_experience_main_flow(api_client, employee_user, employee_profile):
    """UC-TC-04 | source_id: UC-02 Main Flow | Employee adds work experience successfully."""
    api_client.force_authenticate(user=employee_user)
    payload = {
        'organization': 'Research Lab',
        'position': 'Junior Researcher',
        'start_date': '2018-06-01',
        'end_date': '2020-05-31',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['organization'] == 'Research Lab'
    assert response.data['position'] == 'Junior Researcher'


# ---------------------------------------------------------------------------
# UC-TC-05: UC-02 Alternative A1 - Invalid date range submitted
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_tc05_add_experience_invalid_dates(api_client, employee_user, employee_profile):
    """UC-TC-05 | source_id: UC-02 Alternative A1 | Invalid date range rejected with 400."""
    api_client.force_authenticate(user=employee_user)
    payload = {
        'organization': 'Some Corp',
        'position': 'Analyst',
        'start_date': '2024-01-01',
        'end_date': '2023-01-01',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'end_date' in str(response.data)


# ---------------------------------------------------------------------------
# UC-TC-06: UC-02 Alternative A2 - Ongoing experience (no end date)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_tc06_add_experience_ongoing(api_client, employee_user, employee_profile):
    """UC-TC-06 | source_id: UC-02 Alternative A2 | Ongoing experience (null end_date) accepted."""
    api_client.force_authenticate(user=employee_user)
    payload = {
        'organization': 'Current University',
        'position': 'Associate Professor',
        'start_date': '2020-07-01',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['end_date'] is None


# ---------------------------------------------------------------------------
# UC-TC-07: UC-03 Main Flow - Staff retrieves all profiles
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_tc07_staff_retrieves_all_profiles(api_client, staff_user, employee_profile, staff_profile):
    """UC-TC-07 | source_id: UC-03 Main Flow | Staff user retrieves all profiles."""
    api_client.force_authenticate(user=staff_user)
    response = api_client.get('/api/v1/hr-eis/profiles/')
    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    pf_numbers = [p['pf_number'] for p in results]
    assert 'PF-UC-001' in pf_numbers
    assert 'PF-UC-STAFF' in pf_numbers


# ---------------------------------------------------------------------------
# UC-TC-08: UC-03 Alternative A1 - Non-staff employee only sees own profile
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_tc08_non_staff_sees_only_own_profile(api_client, employee_user, employee_profile, staff_profile):
    """UC-TC-08 | source_id: UC-03 Alternative A1 | Non-staff sees only their own profile."""
    api_client.force_authenticate(user=employee_user)
    response = api_client.get('/api/v1/hr-eis/profiles/')
    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    pf_numbers = [p['pf_number'] for p in results]
    assert pf_numbers == ['PF-UC-001']


# ---------------------------------------------------------------------------
# UC-TC-09: UC-04 Main Flow - Employee retrieves their work experiences
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_tc09_list_own_experiences(api_client, employee_user, employee_profile):
    """UC-TC-09 | source_id: UC-04 Main Flow | Employee retrieves their work experiences."""
    WorkExperience.objects.create(
        employee=employee_profile,
        organization='Alpha Corp',
        position='Scientist',
        start_date=date(2017, 1, 1),
        end_date=date(2019, 12, 31),
    )
    api_client.force_authenticate(user=employee_user)
    response = api_client.get('/api/v1/hr-eis/experiences/')
    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    assert len(results) == 1
    assert results[0]['organization'] == 'Alpha Corp'


# ---------------------------------------------------------------------------
# UC-TC-10: UC-04 Alternative A1 - Employee has no experiences yet
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_tc10_list_experiences_empty(api_client, employee_user, employee_profile):
    """UC-TC-10 | source_id: UC-04 Alternative A1 | Empty list returned when no experiences exist."""
    api_client.force_authenticate(user=employee_user)
    response = api_client.get('/api/v1/hr-eis/experiences/')
    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    assert results == []


# ---------------------------------------------------------------------------
# UC-TC-11: UC-05 Main Flow - Employee deletes a work experience entry
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_tc11_delete_experience_main_flow(api_client, employee_user, employee_profile):
    """UC-TC-11 | source_id: UC-05 Main Flow | Employee deletes a work experience successfully."""
    exp = WorkExperience.objects.create(
        employee=employee_profile,
        organization='Beta Ltd',
        position='Analyst',
        start_date=date(2016, 3, 1),
        end_date=date(2018, 3, 1),
    )
    api_client.force_authenticate(user=employee_user)
    response = api_client.delete(f'/api/v1/hr-eis/experiences/{exp.id}/')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    get_response = api_client.get('/api/v1/hr-eis/experiences/')
    results = get_results(get_response.data)
    assert all(e['id'] != exp.id for e in results)
