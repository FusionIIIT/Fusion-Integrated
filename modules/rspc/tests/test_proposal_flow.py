import pytest
from rest_framework.test import APIClient
from conftest import make_session
from modules.rspc.models import ProposalDecision, ResearchProposal

pytestmark = pytest.mark.django_db

def _client(stub_iam, perms, uid):
    stub_iam(make_session(user_id=uid, kind="faculty", modules=("rspc",), permissions=perms))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c

def test_full_flow(stub_iam):
    c = _client(stub_iam, ("rspc.proposal.submit",), 1)
    
    # Submit proposal
    proposal_data = {
        "title": "Sample Proposal",
        "objectives": "To study...",
        "start_date": "2027-01-01",
        "end_date": "2027-12-31",
        "budget": "1000.00",
        "funding_agency": "Funding Agency",
        "resource_requirements": "Resources needed...",
        "department": "Department"
    }
    response = c.post("/api/v1/rspc/proposals/", proposal_data, format="json")
    assert response.status_code == 201
    proposal_id = response.data['id']
    
    # Recommend proposal
    c = _client(stub_iam, ("rspc.proposal.recommend",), 2)
    response = c.post(f"/api/v1/rspc/proposals/{proposal_id}/recommend/", {"outcome": "recommended", "remarks": "Looks good"}, format="json")
    assert response.status_code == 200
    
    # Verify proposal
    c = _client(stub_iam, ("rspc.proposal.verify",), 3)
    response = c.post(f"/api/v1/rspc/proposals/{proposal_id}/verify/", {"outcome": "eligible", "remarks": "Eligible for funding"}, format="json")
    assert response.status_code == 200
    
    # Decide proposal
    c = _client(stub_iam, ("rspc.proposal.decide",), 4)
    response = c.post(f"/api/v1/rspc/proposals/{proposal_id}/decide/", {"outcome": "forward", "remarks": "Approved by Dean"}, format="json")
    assert response.status_code == 200
    
    # Authorize proposal
    c = _client(stub_iam, ("rspc.proposal.authorize",), 5)
    response = c.post(f"/api/v1/rspc/proposals/{proposal_id}/authorize/", {"outcome": "approve", "remarks": "Approved by Director"}, format="json")
    assert response.status_code == 200
    
    # Check final status and pi_id
    proposal = ResearchProposal.objects.get(id=proposal_id)
    assert proposal.status == "approved"
    assert proposal.pi_id == 1

def test_decision_stored_with_remarks(stub_iam):
    c = _client(stub_iam, ("rspc.proposal.submit",), 1)
    
    # Submit proposal
    proposal_data = {
        "title": "Sample Proposal",
        "objectives": "To study...",
        "start_date": "2027-01-01",
        "end_date": "2027-12-31",
        "budget": "1000.00",
        "funding_agency": "Funding Agency",
        "resource_requirements": "Resources needed...",
        "department": "Department"
    }
    response = c.post("/api/v1/rspc/proposals/", proposal_data, format="json")
    assert response.status_code == 201
    proposal_id = response.data['id']
    
    # Recommend proposal
    c = _client(stub_iam, ("rspc.proposal.recommend",), 2)
    response = c.post(f"/api/v1/rspc/proposals/{proposal_id}/recommend/", {"outcome": "recommended", "remarks": "Looks good"}, format="json")
    assert response.status_code == 200
    
    # Check ProposalDecision
    decisions = ProposalDecision.objects.filter(proposal_id=proposal_id)
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.stage == "HoD"
    assert decision.outcome == "recommended"
    assert decision.remarks == "Looks good"
    assert decision.actor_id == 2

def test_wrong_state_returns_400(stub_iam):
    c = _client(stub_iam, ("rspc.proposal.submit", "rspc.proposal.decide"), 1)
    
    # Submit proposal
    proposal_data = {
        "title": "Sample Proposal",
        "objectives": "To study...",
        "start_date": "2027-01-01",
        "end_date": "2027-12-31",
        "budget": "1000.00",
        "funding_agency": "Funding Agency",
        "resource_requirements": "Resources needed...",
        "department": "Department"
    }
    response = c.post("/api/v1/rspc/proposals/", proposal_data, format="json")
    assert response.status_code == 201
    proposal_id = response.data['id']
    
    # Decide proposal immediately
    c = _client(stub_iam, ("rspc.proposal.decide",), 4)
    response = c.post(f"/api/v1/rspc/proposals/{proposal_id}/decide/", {"outcome": "approve", "remarks": "Approved by Dean"}, format="json")
    assert response.status_code == 400
    proposal = ResearchProposal.objects.get(id=proposal_id)
    assert proposal.status == "submitted"
