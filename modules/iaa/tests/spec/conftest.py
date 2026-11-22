import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.iaa.models import (
    ApprovalRoute,
    BudgetAllocation,
    IaaPolicy,
    IaaSupportingDocument,
)
from modules.iaa.permissions import ROLE_PERMISSIONS


@pytest.fixture
def auth_client(stub_iam):
    """Helper to generate an authenticated APIClient for any IAA role."""

    def _make(user_id=1001, role="basic_user", department="CSE", permissions=None):
        if permissions is None:
            permissions = tuple(ROLE_PERMISSIONS.get(role, set()))
        session = make_session(
            user_id=user_id,
            modules=("iaa",),
            active_role=role,
            roles=(role,),
            permissions=permissions,
        )
        stub_iam(session)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token tok-test")
        return client

    return _make


@pytest.fixture
def basic_policy(db):
    """Provides standard active IAA policy."""
    return IaaPolicy.objects.create(
        name="Standard Institute Policy",
        financial_year_start_month=4,
        ta_high_value_threshold=25000.00,
        approval_timeout_hours=48,
        is_active=True,
    )


@pytest.fixture
def sample_approval_route(db):
    """Provides a sample active HoD approval route."""
    return ApprovalRoute.objects.create(
        request_type="general_expense",
        department="CSE",
        amount_from=0,
        amount_through=100000,
        level=1,
        authority_role="hod",
        assignee_user_id=2001,
        is_active=True,
    )


@pytest.fixture
def sample_budget(db):
    """Provides a sample departmental budget allocation."""
    return BudgetAllocation.objects.create(
        department="CSE",
        financial_year="2026-2027",
        budget_code="CSE-OPERATING",
        allocated_amount=500000.00,
        committed_amount=0.00,
        available_amount=500000.00,
    )


@pytest.fixture
def sample_document(db):
    """Provides a supporting document for user 1001."""
    return IaaSupportingDocument.objects.create(
        user_id=1001,
        kind="expense",
        title="Quotation Invoice",
        drive_url="https://drive.google.com/file/d/test-doc-file-id-123/view",
        drive_file_id="test-doc-file-id-123",
        is_active=True,
    )
