# tests/a8/fr/test_fr_hr_eis.py
"""
Assignment 8 - FR (Functional Requirements) Strategy Tests for hr_eis module.
Source: Problem Statement + CFR/AFR specifications.
Design frozen in: a8_design/FR_DESIGN.json
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
    return User.objects.create_user(username='emp_fr_01', password='pass1234')


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(username='staff_fr_01', password='pass1234', is_staff=True)


@pytest.fixture
def employee_profile(db, employee_user):
    return EmployeeProfile.objects.create(
        user=employee_user,
        pf_number='PF-FR-001',
        designation='ASST_PROF',
        department='CSE',
        date_of_joining=date(2022, 1, 1),
    )


@pytest.fixture
def staff_profile(db, staff_user):
    return EmployeeProfile.objects.create(
        user=staff_user,
        pf_number='PF-FR-STAFF',
        designation='PROFESSOR',
        department='ME',
        date_of_joining=date(2018, 6, 1),
    )


# ---------------------------------------------------------------------------
# FR-TC-01: CFR-01 - Authenticated employee retrieves own profile via /me
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_tc01_me_profile_authenticated(api_client, employee_user, employee_profile):
    """FR-TC-01 | source_id: CFR-01 | Authenticated employee retrieves own profile via /me."""
    api_client.force_authenticate(user=employee_user)
    response = api_client.get('/api/v1/hr-eis/profiles/me/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['pf_number'] == 'PF-FR-001'
    assert response.data['designation'] == 'ASST_PROF'
    assert response.data['department'] == 'CSE'


# ---------------------------------------------------------------------------
# FR-TC-02: CFR-01 - /me returns 404 when no profile exists for the user
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_tc02_me_profile_not_found(api_client, db):
    """FR-TC-02 | source_id: CFR-01 | /me returns 404 when no profile exists."""
    no_profile_user = User.objects.create_user(username='noprofile_fr', password='pass1234')
    api_client.force_authenticate(user=no_profile_user)
    response = api_client.get('/api/v1/hr-eis/profiles/me/')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'Profile not found for logged in user.' in str(response.data)


# ---------------------------------------------------------------------------
# FR-TC-03: CFR-02 - Unauthenticated access to profiles is denied
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_tc03_unauthenticated_profiles(api_client, db):
    """FR-TC-03 | source_id: CFR-02 | Unauthenticated access to profiles endpoint denied."""
    response = api_client.get('/api/v1/hr-eis/profiles/')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# FR-TC-04: CFR-02 - Unauthenticated access to work experiences is denied
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_tc04_unauthenticated_experiences(api_client, db):
    """FR-TC-04 | source_id: CFR-02 | Unauthenticated access to experiences endpoint denied."""
    response = api_client.get('/api/v1/hr-eis/experiences/')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# FR-TC-05: CFR-03 - Non-staff employee only sees their own profile
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_tc05_non_staff_sees_only_own_profile(api_client, employee_user, employee_profile, staff_profile):
    """FR-TC-05 | source_id: CFR-03 | Non-staff employee sees only their own profile."""
    api_client.force_authenticate(user=employee_user)
    response = api_client.get('/api/v1/hr-eis/profiles/')
    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    pf_numbers = [p['pf_number'] for p in results]
    assert 'PF-FR-001' in pf_numbers
    assert 'PF-FR-STAFF' not in pf_numbers
    assert len(pf_numbers) == 1


# ---------------------------------------------------------------------------
# FR-TC-06: CFR-03 - Staff user sees all profiles
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_tc06_staff_sees_all_profiles(api_client, staff_user, employee_profile, staff_profile):
    """FR-TC-06 | source_id: CFR-03 | Staff user sees all employee profiles."""
    api_client.force_authenticate(user=staff_user)
    response = api_client.get('/api/v1/hr-eis/profiles/')
    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    pf_numbers = [p['pf_number'] for p in results]
    assert 'PF-FR-001' in pf_numbers
    assert 'PF-FR-STAFF' in pf_numbers


# ---------------------------------------------------------------------------
# FR-TC-07: CFR-04 - Employee can create a work experience entry
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_tc07_create_work_experience(api_client, employee_user, employee_profile):
    """FR-TC-07 | source_id: CFR-04 | Employee can create a work experience entry."""
    api_client.force_authenticate(user=employee_user)
    payload = {
        'organization': 'IIITDMJ',
        'position': 'Research Assistant',
        'start_date': '2020-01-01',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['organization'] == 'IIITDMJ'
    assert response.data['position'] == 'Research Assistant'


# ---------------------------------------------------------------------------
# FR-TC-08: CFR-04 - Employee retrieves their own work experience entries
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_tc08_list_work_experiences(api_client, employee_user, employee_profile):
    """FR-TC-08 | source_id: CFR-04 | Employee retrieves only their own work experiences."""
    WorkExperience.objects.create(
        employee=employee_profile,
        organization='Tech Corp',
        position='Engineer',
        start_date=date(2019, 1, 1),
    )
    api_client.force_authenticate(user=employee_user)
    response = api_client.get('/api/v1/hr-eis/experiences/')
    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    assert len(results) == 1
    assert results[0]['organization'] == 'Tech Corp'


# ---------------------------------------------------------------------------
# FR-TC-09: AFR-01 - pf_number uniqueness constraint enforced at model level
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_tc09_pf_number_unique(employee_profile, db):
    """FR-TC-09 | source_id: AFR-01 | pf_number uniqueness constraint is enforced."""
    another_user = User.objects.create_user(username='another_emp_fr', password='pass1234')
    with pytest.raises(Exception):
        EmployeeProfile.objects.create(
            user=another_user,
            pf_number='PF-FR-001',  # duplicate
            designation='STAFF',
            department='ECE',
            date_of_joining=date(2024, 1, 1),
        )


# ---------------------------------------------------------------------------
# FR-TC-10: AFR-02 - end_date earlier than start_date is rejected
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_tc10_end_date_before_start_date_rejected(api_client, employee_user, employee_profile):
    """FR-TC-10 | source_id: AFR-02 | end_date earlier than start_date is rejected."""
    api_client.force_authenticate(user=employee_user)
    payload = {
        'organization': 'Old Corp',
        'position': 'Intern',
        'start_date': '2024-06-01',
        'end_date': '2023-01-01',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'end_date' in str(response.data)


# ---------------------------------------------------------------------------
# FR-TC-11: AFR-02 - Valid dates (end >= start) are accepted
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_tc11_valid_date_range_accepted(api_client, employee_user, employee_profile):
    """FR-TC-11 | source_id: AFR-02 | Work experience with valid date range is accepted."""
    api_client.force_authenticate(user=employee_user)
    payload = {
        'organization': 'Valid Corp',
        'position': 'Developer',
        'start_date': '2020-01-01',
        'end_date': '2022-06-01',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_201_CREATED


# ---------------------------------------------------------------------------
# FR-TC-12: AFR-03 - Null end_date (ongoing) is accepted
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_tc12_null_end_date_accepted(api_client, employee_user, employee_profile):
    """FR-TC-12 | source_id: AFR-03 | Work experience with no end_date (ongoing) is accepted."""
    api_client.force_authenticate(user=employee_user)
    payload = {
        'organization': 'Current Employer',
        'position': 'Professor',
        'start_date': '2023-01-01',
    }
    response = api_client.post('/api/v1/hr-eis/experiences/', payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['end_date'] is None


# ---------------------------------------------------------------------------
# FR-TC-13: CFR-05 - EmployeeProfile __str__ representation
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_tc13_employee_profile_str(employee_user, employee_profile):
    """FR-TC-13 | source_id: CFR-05 | EmployeeProfile __str__ returns expected format."""
    expected = f"{employee_user.username} (PF-FR-001) - ASST_PROF"
    assert str(employee_profile) == expected


# ---------------------------------------------------------------------------
# FR-TC-14: CFR-06 - Employee can delete a work experience
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_tc14_delete_work_experience(api_client, employee_user, employee_profile):
    """FR-TC-14 | source_id: CFR-06 | Employee can delete a work experience entry."""
    exp = WorkExperience.objects.create(
        employee=employee_profile,
        organization='Old Place',
        position='Researcher',
        start_date=date(2015, 1, 1),
        end_date=date(2018, 12, 31),
    )
    api_client.force_authenticate(user=employee_user)
    response = api_client.delete(f'/api/v1/hr-eis/experiences/{exp.id}/')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not WorkExperience.objects.filter(id=exp.id).exists()
