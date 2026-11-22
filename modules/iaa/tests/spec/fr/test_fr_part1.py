import pytest
from rest_framework import status

from modules.iaa.domain.workflow import expense_completeness
from modules.iaa.models import ExpenseRequest, IaaAuditEvent

pytestmark = pytest.mark.django_db


def test_tc_fr_001_afr_iaa_001(auth_client):
    """TC_FR_001 (source_id: AFR-IAA-001)

    Verify that an authorized Basic User can create an expense/voucher request
    and save it as Draft.
    """
    client = auth_client(user_id=1001, role="basic_user")
    payload = {
        "request_type": "contingency",
        "description": "Stationery supplies",
    }
    response = client.post("/api/v1/iaa/expenses", payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "draft"
    assert data["creator_user_id"] == 1001
    assert data["request_type"] == "contingency"

    expense = ExpenseRequest.objects.get(pk=data["id"])
    assert expense.status == "draft"
    assert expense.creator_user_id == 1001


def test_tc_fr_002_afr_iaa_002(auth_client):
    """TC_FR_002 (source_id: AFR-IAA-002)

    Verify that the request creator can enter request type, amount, department,
    description, and supporting information.
    """
    client = auth_client(user_id=1001, role="basic_user")
    expense = ExpenseRequest.objects.create(
        creator_user_id=1001,
        status="draft",
        request_type="",
    )
    payload = {
        "request_type": "lab_consumables",
        "amount": "1500.50",
        "department": "CSE",
        "description": "Lab equipment purchase",
    }
    response = client.patch(f"/api/v1/iaa/expenses/{expense.pk}", payload, format="json")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["request_type"] == "lab_consumables"
    assert float(data["amount"]) == 1500.50
    assert data["department"] == "CSE"
    assert data["description"] == "Lab equipment purchase"

    expense.refresh_from_db()
    assert expense.request_type == "lab_consumables"
    assert float(expense.amount) == 1500.50
    assert expense.department == "CSE"
    assert expense.description == "Lab equipment purchase"


def test_tc_fr_003_afr_iaa_003(auth_client, sample_document):
    """TC_FR_003 (source_id: AFR-IAA-003)

    Verify that the request creator can attach supporting documents to an
    expense/voucher request.
    """
    client = auth_client(user_id=1001, role="basic_user")
    expense = ExpenseRequest.objects.create(
        creator_user_id=1001,
        status="draft",
        request_type="hardware",
    )
    payload = {
        "supporting_documents": [{"document_id": sample_document.pk}],
    }
    response = client.patch(f"/api/v1/iaa/expenses/{expense.pk}", payload, format="json")
    assert response.status_code == status.HTTP_200_OK

    expense.refresh_from_db()
    assert len(expense.supporting_documents) == 1
    assert expense.supporting_documents[0]["document_id"] == sample_document.pk


def test_tc_fr_004_afr_iaa_004(auth_client):
    """TC_FR_004 (source_id: AFR-IAA-004)

    Verify that saving a Draft with missing submission-mandatory information is
    permitted and missing information is identified.
    """
    client = auth_client(user_id=1001, role="basic_user")
    payload = {
        "request_type": "travel",
        "description": "Incomplete draft test",
    }
    response = client.post("/api/v1/iaa/expenses", payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "draft"

    # Identify missing submission-mandatory fields via completeness validator
    completeness = expense_completeness(data)
    assert not completeness.complete
    assert "amount" in completeness.missing
    assert "department" in completeness.missing
    assert "documents" in completeness.missing


def test_tc_fr_005_afr_iaa_005(auth_client, sample_document):
    """TC_FR_005 (source_id: AFR-IAA-005)

    Verify that a Basic User can submit a complete Draft expense/voucher
    request for formal processing.
    """
    client = auth_client(user_id=1001, role="basic_user")
    expense = ExpenseRequest.objects.create(
        creator_user_id=1001,
        request_type="consumables",
        amount=5000.00,
        department="CSE",
        description="Printer cartridges",
        supporting_documents=[{"document_id": sample_document.pk}],
        status="draft",
    )
    response = client.post(f"/api/v1/iaa/expenses/{expense.pk}/submit")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "submitted"

    expense.refresh_from_db()
    assert expense.status == "submitted"


def test_tc_fr_006_01_afr_iaa_006(auth_client):
    """TC_FR_006_01 (source_id: AFR-IAA-006)

    Verify that formal submission of an expense/voucher request is blocked when
    mandatory fields are missing.
    """
    client = auth_client(user_id=1001, role="basic_user")
    expense = ExpenseRequest.objects.create(
        creator_user_id=1001,
        request_type="",
        amount=None,
        department="",
        description="",
        status="draft",
    )
    response = client.post(f"/api/v1/iaa/expenses/{expense.pk}/submit")
    assert response.status_code == status.HTTP_409_CONFLICT
    expense.refresh_from_db()
    assert expense.status == "draft"


def test_tc_fr_006_02_afr_iaa_006(auth_client):
    """TC_FR_006_02 (source_id: AFR-IAA-006)

    Verify that formal submission of an expense/voucher request is blocked when
    required documents are missing.
    """
    client = auth_client(user_id=1001, role="basic_user")
    expense = ExpenseRequest.objects.create(
        creator_user_id=1001,
        request_type="consumables",
        amount=2500.00,
        department="CSE",
        description="Office stationary",
        supporting_documents=[],  # missing documents
        status="draft",
    )
    response = client.post(f"/api/v1/iaa/expenses/{expense.pk}/submit")
    assert response.status_code == status.HTTP_409_CONFLICT
    expense.refresh_from_db()
    assert expense.status == "draft"


def test_tc_fr_007_afr_iaa_007(auth_client, sample_document):
    """TC_FR_007 (source_id: AFR-IAA-007)

    Verify that upon successful submission, the request status becomes
    Submitted and it is routed to Finance Staff.
    """
    client = auth_client(user_id=1001, role="basic_user")
    expense = ExpenseRequest.objects.create(
        creator_user_id=1001,
        request_type="workshop",
        amount=12000.00,
        department="CSE",
        description="Student workshop expenses",
        supporting_documents=[{"document_id": sample_document.pk}],
        status="draft",
    )
    response = client.post(f"/api/v1/iaa/expenses/{expense.pk}/submit")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "submitted"

    # Verify visible in Finance Staff review queue
    finance_client = auth_client(user_id=3001, role="finance_staff")
    finance_res = finance_client.get("/api/v1/iaa/notifications")
    assert finance_res.status_code == status.HTTP_200_OK
    feed = finance_res.json()["results"]
    assert any(
        item.get("event") == "pending_finance_review"
        and item.get("record_type") == "expense"
        and item.get("record_id") == expense.pk
        for item in feed
    )


def test_tc_fr_008_01_afr_iaa_008(auth_client, sample_document):
    """TC_FR_008_01 (source_id: AFR-IAA-008)

    Verify that ordinary creator editing of an expense/voucher request is
    prevented after submission.
    """
    client = auth_client(user_id=1001, role="basic_user")
    expense = ExpenseRequest.objects.create(
        creator_user_id=1001,
        request_type="workshop",
        amount=10000.00,
        department="CSE",
        description="Original text",
        supporting_documents=[{"document_id": sample_document.pk}],
        status="submitted",
    )
    payload = {"description": "Altered description attempt"}
    response = client.patch(f"/api/v1/iaa/expenses/{expense.pk}", payload, format="json")
    assert response.status_code == status.HTTP_409_CONFLICT

    expense.refresh_from_db()
    assert expense.description == "Original text"
    assert expense.status == "submitted"


def test_tc_fr_008_02_afr_iaa_008(auth_client):
    """TC_FR_008_02 (source_id: AFR-IAA-008)

    Verify that creator editing/correction of an expense/voucher request is
    permitted through supported clarification/correction response.
    """
    client = auth_client(user_id=1001, role="basic_user")
    expense = ExpenseRequest.objects.create(
        creator_user_id=1001,
        request_type="workshop",
        amount=10000.00,
        department="CSE",
        description="Workshop description",
        status="query_raised",
        clarification="Please clarify invoice item breakdown.",
    )
    payload = {"response": "Here is the clarified item breakdown."}
    response = client.post(
        f"/api/v1/iaa/expenses/{expense.pk}/clarification-response",
        payload,
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "query_responded"

    expense.refresh_from_db()
    assert expense.status == "query_responded"


def test_tc_fr_009_afr_iaa_009(auth_client, sample_document):
    """TC_FR_009 (source_id: AFR-IAA-009)

    Verify that the system preserves a complete action and status history for an
    expense/voucher request.
    """
    client = auth_client(user_id=1001, role="basic_user")
    # Step 1: create draft
    res1 = client.post(
        "/api/v1/iaa/expenses",
        {
            "request_type": "event",
            "amount": "2000.00",
            "department": "CSE",
            "description": "Techfest expense",
            "supporting_documents": [{"document_id": sample_document.pk}],
        },
        format="json",
    )
    expense_id = res1.json()["id"]

    # Step 2: submit
    res2 = client.post(f"/api/v1/iaa/expenses/{expense_id}/submit")
    assert res2.status_code == status.HTTP_200_OK

    # Query history endpoint
    history_res = client.get(f"/api/v1/iaa/expense/{expense_id}/history")
    assert history_res.status_code == status.HTTP_200_OK
    history = history_res.json()
    actions = [h["action"] for h in history]
    assert "draft_created" in actions
    assert "submitted" in actions

    # Also verify audit table records directly
    audit_actions = list(
        IaaAuditEvent.objects.filter(record_type="expense", record_id=expense_id)
        .order_by("occurred_at")
        .values_list("action", flat=True)
    )
    assert "draft_created" in audit_actions
    assert "submitted" in audit_actions


def test_tc_fr_010_afr_iaa_010(auth_client, sample_document):
    """TC_FR_010 (source_id: AFR-IAA-010)

    Verify that Finance Staff can review submitted expense/voucher request
    details and supporting documents.
    """
    expense = ExpenseRequest.objects.create(
        creator_user_id=1001,
        request_type="lab_equipment",
        amount=8500.00,
        department="CSE",
        description="Oscilloscopes",
        supporting_documents=[{"document_id": sample_document.pk}],
        status="submitted",
    )
    finance_client = auth_client(user_id=3001, role="finance_staff")
    response = finance_client.get(f"/api/v1/iaa/expenses/{expense.pk}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == expense.pk
    assert data["request_type"] == "lab_equipment"
    assert float(data["amount"]) == 8500.00
    assert len(data["supporting_documents"]) == 1
    assert data["supporting_documents"][0]["title"] == sample_document.title


def test_tc_fr_011_afr_iaa_011(
    auth_client, sample_document, basic_policy, sample_approval_route, sample_budget
):
    """TC_FR_011 (source_id: AFR-IAA-011)

    Verify that Finance Staff can validate expense/voucher requests against
    applicable financial and policy requirements.
    """
    expense = ExpenseRequest.objects.create(
        creator_user_id=1001,
        request_type="general_expense",
        amount=5000.00,
        department="CSE",
        description="Departmental consumables",
        supporting_documents=[{"document_id": sample_document.pk}],
        status="submitted",
    )
    finance_client = auth_client(user_id=3001, role="finance_staff")
    payload = {
        "decision": "validate",
        "notes": "Verified against departmental budget CSE-OPERATING.",
    }
    response = finance_client.post(
        f"/api/v1/iaa/expenses/{expense.pk}/finance-review",
        payload,
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "approval_pending"
    assert data["assigned_finance_user_id"] == 3001
    assert (
        data["finance_notes"]
        == "Verified against departmental budget CSE-OPERATING."
    )

    expense.refresh_from_db()
    assert expense.status == "approval_pending"
    assert expense.assigned_finance_user_id == 3001


def test_tc_fr_012_afr_iaa_012(auth_client, sample_document):
    """TC_FR_012 (source_id: AFR-IAA-012)

    Verify that Finance Staff can request clarification or additional evidence
    during validation.
    """
    expense = ExpenseRequest.objects.create(
        creator_user_id=1001,
        request_type="general_expense",
        amount=5000.00,
        department="CSE",
        description="Departmental consumables",
        supporting_documents=[{"document_id": sample_document.pk}],
        status="submitted",
    )
    finance_client = auth_client(user_id=3001, role="finance_staff")
    payload = {
        "decision": "query",
        "clarification": "Please provide proof of vendor tax invoice.",
    }
    response = finance_client.post(
        f"/api/v1/iaa/expenses/{expense.pk}/finance-review",
        payload,
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "query_raised"

    expense.refresh_from_db()
    assert expense.status == "query_raised"
    assert expense.clarification == "Please provide proof of vendor tax invoice."


def test_tc_fr_013_afr_iaa_013(auth_client, sample_document):
    """TC_FR_013 (source_id: AFR-IAA-013)

    Verify that the concerned Basic User can respond to a Finance clarification
    query with information or evidence.
    """
    expense = ExpenseRequest.objects.create(
        creator_user_id=1001,
        request_type="general_expense",
        amount=5000.00,
        department="CSE",
        description="Departmental consumables",
        supporting_documents=[],
        status="query_raised",
        clarification="Please attach invoice.",
    )
    client = auth_client(user_id=1001, role="basic_user")
    payload = {
        "response": "Attached requested vendor tax invoice.",
        "supporting_documents": [{"document_id": sample_document.pk}],
    }
    response = client.post(
        f"/api/v1/iaa/expenses/{expense.pk}/clarification-response",
        payload,
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "query_responded"

    expense.refresh_from_db()
    assert expense.status == "query_responded"
    assert len(expense.supporting_documents) == 1
    assert expense.supporting_documents[0]["document_id"] == sample_document.pk
