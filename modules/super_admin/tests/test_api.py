import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from conftest import make_session
from core.api import csrf
from modules.super_admin.models import UserAccount, RoleAssignment, SystemAuditLog
@pytest.fixture
def client(stub_iam):
    stub_iam(make_session(
        user_id=1,
        kind="staff",
        modules=("super_admin",),
        permissions=(
            "super_admin.user.manage",
            "super_admin.role.manage",
            "super_admin.audit.view",
        ),
    ))
    c = APIClient()
    c.cookies["fusion_session"] = "tok-123"
    c.credentials(HTTP_X_CSRF_TOKEN=csrf.token_for("tok-123"))
    return c
@pytest.mark.django_db
def test_create_user_account(client):
    user_data = {
        "institute_id": "2026BCS001",
        "username": "test_student",
        "email": "student@iiitdmj.ac.in",
        "user_type": "student",
    }
    response = client.post(reverse("sa-users"), user_data)
    assert response.status_code == status.HTTP_201_CREATED
    assert SystemAuditLog.objects.filter(action="CREATE_USER").exists()
@pytest.mark.django_db
def test_deactivate_user(client):
    user = UserAccount.objects.create(
        institute_id="2026BCS001",
        username="deact_user",
        email="deact@iiitdmj.ac.in",
        user_type="student",
        status="active",
    )
    update_data = {"status": "deactivated"}
    url = reverse("sa-user-status", kwargs={"pk": user.pk})
    response = client.patch(url, update_data)
    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.status == "deactivated"
    assert SystemAuditLog.objects.filter(action="UPDATE_USER_STATUS", target=user.username).exists()
@pytest.mark.django_db
def test_assign_role(client):
    user = UserAccount.objects.create(
        institute_id="2026BCS001",
        username="role_user",
        email="role@iiitdmj.ac.in",
        user_type="student",
        status="active",
    )
    role_data = {
        "user": user.pk,
        "role_name": "acadadmin",
        "assigned_by": "super_admin",
        "start_date": "2026-11-01",
    }
    url = reverse("sa-role-assign")
    response = client.post(url, role_data)
    assert response.status_code == status.HTTP_201_CREATED
    assert SystemAuditLog.objects.filter(action="ASSIGN_ROLE", target="acadadmin").exists()
@pytest.mark.django_db
def test_revoke_role(client):
    user = UserAccount.objects.create(
        institute_id="2026BCS001",
        username="revoke_user",
        email="r@iiitdmj.ac.in",
        user_type="student",
        status="active",
    )
    role_assignment = RoleAssignment.objects.create(
        user=user,
        role_name="temporary_role",
        assigned_by="super_admin",
        start_date="2026-10-01",
        end_date="2026-12-31",
        reason="Test revoke",
        status="active",
    )
    url = reverse("sa-role-revoke", kwargs={"pk": role_assignment.pk})
    response = client.post(url)
    assert response.status_code == status.HTTP_200_OK
    role_assignment.refresh_from_db()
    assert role_assignment.status == "revoked"
    assert SystemAuditLog.objects.filter(action="REVOKE_ROLE", target="temporary_role").exists()
@pytest.mark.django_db
def test_get_audit_logs(client):
    SystemAuditLog.objects.create(
        actor_username="test_user",
        action="TEST_ACTION",
        target="test_target",
        details={"info": "test"},
    )
    url = reverse("sa-audit-logs")
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1