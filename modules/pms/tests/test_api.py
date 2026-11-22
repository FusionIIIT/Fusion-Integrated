from decimal import Decimal
import pytest
from rest_framework.test import APIClient

from modules.pms.models.application import ApplicationStatus, PatentApplication


@pytest.mark.django_db
def test_application_api_endpoints():
    client = APIClient()
    headers = {"HTTP_X_USER_ID": "101", "HTTP_X_USER_ROLES": "student"}

    # 1. Create Draft
    resp = client.post(
        "/api/v1/pms/applications/",
        {
            "title": "Quantum Dot Biosensor",
            "abstract": "Fluorescence resonance energy transfer biosensor array.",
            "detailed_description": "Cadmium-free quantum dots functionalized with aptamers.",
            "claims": "Claim 1: An aptamer-functionalized biosensor.",
            "field_of_invention": "Biotechnology",
        },
        format="json",
        **headers,
    )
    assert resp.status_code == 201
    app_id = resp.data["id"]

    # 2. Get Detail
    resp = client.get(f"/api/v1/pms/applications/{app_id}/", **headers)
    assert resp.status_code == 200
    assert resp.data["title"] == "Quantum Dot Biosensor"

    # 3. Submit
    resp = client.post(f"/api/v1/pms/applications/{app_id}/submit/", **headers)
    assert resp.status_code == 200
    assert resp.data["status"] == ApplicationStatus.SUBMITTED

    # 4. Out-of-scope access from another student returns 404
    other_headers = {"HTTP_X_USER_ID": "999", "HTTP_X_USER_ROLES": "student"}
    resp = client.get(f"/api/v1/pms/applications/{app_id}/", **other_headers)
    assert resp.status_code == 404
