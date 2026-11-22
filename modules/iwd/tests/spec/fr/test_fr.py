import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_fr_01_submit_valid_complaint():
    """
    Test ID: test_fr_01_submit_valid_complaint
    Source ID: AFR-IWD-001 submission
    """
    client = APIClient()
    payload = {
        "title": "Water leakage in Lab 3",
        "description": "Pipe is leaking continuously near the main bench.",
        "category": "CIVIL",
        "location": "Core Lab 3, Ground Floor",
        "department": "CSE"
    }
    response = client.post("/api/iwd/complaints/", payload, format="json", HTTP_X_ROLE="employee", HTTP_X_USER_ID="emp_101")
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "ASSIGNED"
    assert data["assigned_engineer_id"] == "eng_civil_01"

@pytest.mark.django_db
def test_fr_02_refuse_short_title():
    """
    Test ID: test_fr_02_refuse_short_title
    Source ID: AFR-IWD-002 validation
    """
    client = APIClient()
    payload = {
        "title": "W",
        "description": "Pipe is leaking continuously.",
        "category": "CIVIL",
        "location": "Room 101"
    }
    response = client.post("/api/iwd/complaints/", payload, format="json", HTTP_X_ROLE="employee")
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_fr_03_refuse_short_description():
    """
    Test ID: test_fr_03_refuse_short_description
    Source ID: AFR-IWD-003 validation
    """
    client = APIClient()
    payload = {
        "title": "Water leakage",
        "description": "Leak",
        "category": "CIVIL",
        "location": "Room 101"
    }
    response = client.post("/api/iwd/complaints/", payload, format="json", HTTP_X_ROLE="employee")
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_fr_04_auto_assignment_civil():
    """
    Test ID: test_fr_04_auto_assignment_civil
    Source ID: AFR-IWD-005 assignment-civil
    """
    client = APIClient()
    payload = {
        "title": "Door latch broken",
        "description": "Main entrance door latch broken and needs fixing.",
        "category": "CIVIL",
        "location": "Hall 3"
    }
    response = client.post("/api/iwd/complaints/", payload, format="json", HTTP_X_ROLE="employee")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["assigned_engineer_id"] == "eng_civil_01"

@pytest.mark.django_db
def test_fr_05_auto_assignment_electrical():
    """
    Test ID: test_fr_05_auto_assignment_electrical
    Source ID: AFR-IWD-006 assignment-electrical
    """
    client = APIClient()
    payload = {
        "title": "Switchboard sparking",
        "description": "Main power switchboard sparking when turned on.",
        "category": "ELECTRICAL",
        "location": "Hostel 1, Room 12"
    }
    response = client.post("/api/iwd/complaints/", payload, format="json", HTTP_X_ROLE="employee")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["assigned_engineer_id"] == "eng_elec_01"

@pytest.mark.django_db
def test_fr_06_non_employee_cannot_submit():
    """
    Test ID: test_fr_06_non_employee_cannot_submit
    Source ID: AFR-IWD-060 active-role-submission
    """
    client = APIClient()
    payload = {
        "title": "General Repair",
        "description": "General repair of building corridor lighting.",
        "category": "ELECTRICAL",
        "location": "Admin Block"
    }
    response = client.post("/api/iwd/complaints/", payload, format="json", HTTP_X_ROLE="auditor")
    assert response.status_code == status.HTTP_403_FORBIDDEN
