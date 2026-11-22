# tests/a8/br/test_br_hr_eis.py
"""
Assignment 8 - BR (Business Rules) Strategy Tests for hr_eis module.
Source: Problem Statement + Business Rules specification.
Design frozen in: a8_design/BR_DESIGN.json
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
    return User.objects.create_user(username='emp_br_01', password='pass1234')


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(username='staff_br_01', password='pass1234', is_staff=True)


@pytest.fixture
def employee_profile(db, employee_user):
    return EmployeeProfile.objects.create(
        user=employee_user,
        pf_number='PF-BR-001',
        designation='ASST_PROF',
        department='CSE',
        date_of_joining=date(2021, 8, 1),
    )


@pytest.fixture
def staff_profile(db, staff_user):
    return EmployeeProfile.objects.create(
        user=staff_user,
        pf_number='PF-BR-STAFF',
        designation='PROFESSOR',
        department='DESIGN',
        date_of_joining=date(2016, 1, 1),
    )


# ---------------------------------------------------------------------------
# BR-TC-01: BR-01 condition-true - Duplicate pf_number is rejected
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_tc01_pf_number_duplicate_rejected(employee_profile, db):
    """BR-TC-01 | source_id: BR-01 condition-true | Duplicate pf_number raises IntegrityError."""
    another_user = User.objects.create_user(username='dup_pf_user_br', password='pass1234')
    with pytest.raises(Exception):
        EmployeeProfile.objects.create(
            user=another_user,
            pf_number='PF-BR-001',  # duplicate
            designation='STAFF',
            department='NS',
            date_of_joining=date(2024, 1, 1),
        )


# ---------------------------------------------------------------------------
# BR-TC-02: BR-01 condition-false - Unique pf_number is accepted
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_tc02_pf_number_unique_accepted(db):
    """BR-TC-02 | source_id: BR-01 condition-false | Unique pf_number is accepted."""
    user = User.objects.create_user(username='unique_pf_user_br', password='pass1234')
    profile = EmployeeProfile.objects.create(
        user=user,
        pf_number='PF-BR-999',
        designation='STAFF',
        department='NS',
        date_of_joining=date(2023, 5, 1),
    )
    assert profile.pk is not None
    assert profile.pf_number == 'PF-BR-999'


# ---------------------------------------------------------------------------
# BR-TC-03: BR-02 condition-true - end_date < start_date rejected with message
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_tc03_end_date_before_start_rejected(api_client, employee_user, employee_profile):
    """BR-TC-03 | source_id: BR-02 condition-true | end_date < start_date rejected with correct message."""
    api_client.force_authenticate(user=employee_user)
    payload = {
        'organization': 'Old Firm',
        'position': 'Intern',
        'start_date': '2024-06-01',
        'end_date': '2023-01-01',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'end_date' in str(response.data)
    assert 'End date cannot be earlier than start date.' in str(response.data)


# ---------------------------------------------------------------------------
# BR-TC-04: BR-02 condition-false - end_date == start_date is accepted
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_tc04_end_date_equal_start_accepted(api_client, employee_user, employee_profile):
    """BR-TC-04 | source_id: BR-02 condition-false | end_date == start_date is accepted."""
    api_client.force_authenticate(user=employee_user)
    payload = {
        'organization': 'Short Stint',
        'position': 'Consultant',
        'start_date': '2023-01-01',
        'end_date': '2023-01-01',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_201_CREATED


# ---------------------------------------------------------------------------
# BR-TC-05: BR-03 - null end_date (ongoing) is allowed
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_tc05_null_end_date_allowed(api_client, employee_user, employee_profile):
    """BR-TC-05 | source_id: BR-03 | Ongoing work experience (null end_date) is allowed."""
    api_client.force_authenticate(user=employee_user)
    payload = {
        'organization': 'IIITDMJ',
        'position': 'Faculty',
        'start_date': '2021-08-01',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['end_date'] is None


# ---------------------------------------------------------------------------
# BR-TC-06: BR-04 condition-true - Non-staff sees only their own data
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_tc06_non_staff_data_isolation(api_client, employee_user, employee_profile, staff_profile):
    """BR-TC-06 | source_id: BR-04 condition-true | Non-staff sees only their own profile."""
    api_client.force_authenticate(user=employee_user)
    response = api_client.get('/api/v1/hr-eis/profiles/')
    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    pf_numbers = [p['pf_number'] for p in results]
    assert 'PF-BR-001' in pf_numbers
    assert 'PF-BR-STAFF' not in pf_numbers
    assert len(pf_numbers) == 1


# ---------------------------------------------------------------------------
# BR-TC-07: BR-04 condition-false - Staff sees all profiles
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_tc07_staff_sees_all(api_client, staff_user, employee_profile, staff_profile):
    """BR-TC-07 | source_id: BR-04 condition-false | Staff user sees all profiles."""
    api_client.force_authenticate(user=staff_user)
    response = api_client.get('/api/v1/hr-eis/profiles/')
    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    pf_numbers = [p['pf_number'] for p in results]
    assert 'PF-BR-001' in pf_numbers
    assert 'PF-BR-STAFF' in pf_numbers


# ---------------------------------------------------------------------------
# BR-TC-08: BR-05 - Work experiences scoped to authenticated employee
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_tc08_work_experience_scoped_to_employee(api_client, db):
    """BR-TC-08 | source_id: BR-05 | Work experiences are scoped to authenticated employee."""
    user_a = User.objects.create_user(username='emp_br_a', password='pass1234')
    user_b = User.objects.create_user(username='emp_br_b', password='pass1234')
    profile_a = EmployeeProfile.objects.create(
        user=user_a, pf_number='PF-BR-A', designation='ASST_PROF',
        department='CSE', date_of_joining=date(2020, 1, 1),
    )
    profile_b = EmployeeProfile.objects.create(
        user=user_b, pf_number='PF-BR-B', designation='STAFF',
        department='ME', date_of_joining=date(2021, 1, 1),
    )
    WorkExperience.objects.create(
        employee=profile_a, organization='Corp A', position='Dev',
        start_date=date(2015, 1, 1),
    )
    WorkExperience.objects.create(
        employee=profile_b, organization='Corp B', position='Admin',
        start_date=date(2016, 1, 1),
    )
    api_client.force_authenticate(user=user_a)
    response = api_client.get('/api/v1/hr-eis/experiences/')
    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    organizations = [e['organization'] for e in results]
    assert 'Corp A' in organizations
    assert 'Corp B' not in organizations


# ---------------------------------------------------------------------------
# BR-TC-09: BR-06 - Authentication required for all endpoints
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_tc09_auth_required_for_all_endpoints(api_client, db):
    """BR-TC-09 | source_id: BR-06 | Authentication required for profiles and experiences."""
    res_profiles = api_client.get('/api/v1/hr-eis/profiles/')
    res_experiences = api_client.get('/api/v1/hr-eis/experiences/')
    assert res_profiles.status_code == status.HTTP_401_UNAUTHORIZED
    assert res_experiences.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# BR-TC-10: BR-07 - Experience auto-linked to authenticated user's profile
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_tc10_experience_auto_linked_to_profile(api_client, employee_user, employee_profile):
    """BR-TC-10 | source_id: BR-07 | WorkExperience is auto-linked to authenticated user's profile."""
    api_client.force_authenticate(user=employee_user)
    payload = {
        'organization': 'AutoLink Corp',
        'position': 'Scientist',
        'start_date': '2019-01-01',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_201_CREATED
    exp = WorkExperience.objects.get(id=response.data['id'])
    assert exp.employee == employee_profile


# ---------------------------------------------------------------------------
# BR-TC-11: BR-08 - designation must be one of the allowed choices
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_tc11_invalid_designation_rejected(db):
    """BR-TC-11 | source_id: BR-08 | designation='DIRECTOR' (not in choices) raises ValidationError."""
    user = User.objects.create_user(username='dir_user_br', password='pass1234')
    profile = EmployeeProfile(
        user=user,
        pf_number='PF-BR-DIR',
        designation='DIRECTOR',
        department='CSE',
        date_of_joining=date(2024, 1, 1),
    )
    with pytest.raises(Exception):
        profile.full_clean()


# ---------------------------------------------------------------------------
# BR-TC-12: BR-09 - department must be one of the allowed choices
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_tc12_invalid_department_rejected(db):
    """BR-TC-12 | source_id: BR-09 | department='PHYSICS' (not in choices) raises ValidationError."""
    user = User.objects.create_user(username='phys_user_br', password='pass1234')
    profile = EmployeeProfile(
        user=user,
        pf_number='PF-BR-PHYS',
        designation='STAFF',
        department='PHYSICS',
        date_of_joining=date(2024, 1, 1),
    )
    with pytest.raises(Exception):
        profile.full_clean()
