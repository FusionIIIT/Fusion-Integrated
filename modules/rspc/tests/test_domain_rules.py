"""Unit tests for RSPC domain business rules."""
from decimal import Decimal
from datetime import date
import pytest

from modules.rspc.domain.rules import (
    validate_research_proposal,
    validate_consultancy_project,
    validate_financial_request,
    validate_procurement_request,
    validate_project_closure,
    is_director_approval_required,
)


def test_validate_research_proposal_valid():
    valid_data = {
        "title": "AI in Smart Grid Optimization",
        "pi_id": 101,
        "department": "CSE",
        "funding_agency": "SERB",
        "budget": Decimal("2500000.00"),
        "objectives": "Optimize renewable integration",
        "start_date": "2026-04-01",
        "end_date": "2028-03-31",
    }
    errors = validate_research_proposal(valid_data)
    assert errors == []


def test_validate_research_proposal_missing_fields():
    invalid_data = {
        "title": "",
        "pi_id": 0,
        "department": "",
        "funding_agency": "",
        "budget": -500,
        "objectives": "",
        "start_date": "2026-04-01",
        "end_date": "2025-04-01",  # End before start
    }
    errors = validate_research_proposal(invalid_data)
    assert len(errors) >= 5
    assert any("title" in e.lower() for e in errors)
    assert any("pi" in e.lower() for e in errors)
    assert any("budget" in e.lower() for e in errors)
    assert any("end date" in e.lower() for e in errors)


def test_validate_consultancy_project_valid():
    data = {
        "title": "Industrial Automation Consultancy",
        "pi_id": 102,
        "client_name": "Bharat Heavy Electricals Ltd",
        "scope_of_work": "PLC Migration",
        "deliverables": "Firmware and docs",
        "total_cost": Decimal("450000.00"),
    }
    errors = validate_consultancy_project(data)
    assert errors == []


def test_is_director_approval_required():
    # Large proposal >= 10 Lakhs
    assert is_director_approval_required("proposal", 1500000) is True
    assert is_director_approval_required("proposal", 800000) is False

    # High value expenditure >= 2 Lakhs
    assert is_director_approval_required("financial", 250000) is True
    assert is_director_approval_required("financial", 150000) is False

    # Strategic flag forces Director approval
    assert is_director_approval_required("proposal", 50000, is_strategic=True) is True


def test_validate_financial_request():
    # Valid within budget
    assert validate_financial_request(50000, 100000) == []

    # Exceeding budget
    errors = validate_financial_request(150000, 100000)
    assert len(errors) == 1
    assert "exceeds available" in errors[0].lower()


def test_validate_project_closure():
    # Valid closure
    assert validate_project_closure(True, True) == []

    # Financial settlement pending
    errors = validate_project_closure(False, True)
    assert len(errors) == 1
    assert "financial settlement is pending" in errors[0].lower()

    # Asset declaration missing
    errors = validate_project_closure(True, False)
    assert len(errors) == 1
    assert "asset declaration" in errors[0].lower()
