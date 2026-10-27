import pytest
from rest_framework.test import APIClient
from rest_framework import status
from conftest import make_session
from modules.leave.services.ledger import credit_annual_entitlements


def auth_client(stub_iam, user_id=601, perms=None):
    if perms is None:
        perms = (
            "leave.application.apply",
            "leave.application.view_self",
            "leave.application.review",
        )
    stub_iam(make_session(user_id=user_id, kind="faculty", modules=("leave",), permissions=perms))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token-601")
    return client


@pytest.mark.django_db
def test_api_list_create_and_withdraw(stub_iam):
    user_id = 601
    credit_annual_entitlements(user_id, 2026)
    client = auth_client(stub_iam, user_id=user_id)

    # 1. Create and submit application via API
    payload = {
        "category": "CL",
        "start_date": "2026-11-20",
        "end_date": "2026-11-20",
        "reason": "Family engagement",
        "unit_head_id": 999,
        "submit_now": True,
    }

    response = client.post(
        "/api/v1/leave/applications/",
        data=payload,
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    app_id = response.data["id"]
    assert response.data["category"] == "CL"
    assert response.data["status"] == "unit_head_pending"

    # 2. Retrieve application detail
    detail_res = client.get(f"/api/v1/leave/applications/{app_id}/")
    assert detail_res.status_code == status.HTTP_200_OK
    assert detail_res.data["category"] == "CL"
    assert len(detail_res.data["audits"]) >= 1

    # 3. Withdraw application (BR-EL-022)
    withdraw_res = client.post(f"/api/v1/leave/applications/{app_id}/withdraw/")
    assert withdraw_res.status_code == status.HTTP_200_OK
    assert withdraw_res.data["status"] == "withdrawn"


@pytest.mark.django_db
def test_api_balances_and_holidays(stub_iam):
    user_id = 701
    credit_annual_entitlements(user_id, 2026)
    client = auth_client(stub_iam, user_id=user_id)

    bal_res = client.get("/api/v1/leave/balances/?year=2026")
    assert bal_res.status_code == status.HTTP_200_OK
    assert len(bal_res.data) >= 5

    holidays_res = client.get("/api/v1/leave/holidays/?year=2026")
    assert holidays_res.status_code == status.HTTP_200_OK
