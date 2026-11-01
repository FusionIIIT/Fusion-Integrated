import pytest
from rest_framework.test import APIClient
from conftest import make_session
from modules.rspc.models import ResearchProposal

pytestmark = pytest.mark.django_db

def _client(stub_iam, perms, uid):
    stub_iam(make_session(user_id=uid, kind="faculty", modules=("rspc",), permissions=perms))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c

def test_missing_mandatory_fields_rejected(stub_iam):
    c = _client(stub_iam, ("rspc.proposal.submit",), 1)
    response = c.post("/api/v1/rspc/proposals/", {"title": "t", "objectives": "o"}, format="json")
    assert response.status_code == 400
    assert ResearchProposal.objects.count() == 0

def test_action_on_missing_proposal_returns_404(stub_iam):
    c = _client(stub_iam, ("rspc.proposal.recommend",), 2)
    response = c.post("/api/v1/rspc/proposals/999/recommend/", {"outcome": "recommended", "remarks": ""}, format="json")
    assert response.status_code == 404
