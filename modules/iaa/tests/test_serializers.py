"""Validation-rule tests for the input serializers — no db needed."""
from decimal import Decimal

from modules.iaa.api.serializers import (
    DecisionInputSerializer, ExpenseCreateSerializer, TAClaimCreateSerializer,
)


def test_expense_create_requires_core_fields():
    s = ExpenseCreateSerializer(data={"request_type": "Travel"})
    assert not s.is_valid()
    assert "amount" in s.errors and "department" in s.errors


def test_expense_create_description_defaults_to_blank():
    s = ExpenseCreateSerializer(data={
        "request_type": "Travel", "amount": "500.00", "department": "CSE"})
    assert s.is_valid(), s.errors
    assert s.validated_data["description"] == ""


def test_ta_claim_create_rejects_end_before_start():
    s = TAClaimCreateSerializer(data={
        "trip_start": "2026-03-10", "trip_end": "2026-03-01",
        "purpose": "Conference", "claimed_amount": "3000"})
    assert not s.is_valid()
    assert "non_field_errors" in s.errors


def test_ta_claim_create_accepts_valid_range():
    s = TAClaimCreateSerializer(data={
        "trip_start": "2026-03-01", "trip_end": "2026-03-03",
        "purpose": "Conference", "claimed_amount": "3000"})
    assert s.is_valid(), s.errors
    assert s.validated_data["claimed_amount"] == Decimal("3000")


def test_decision_input_requires_remarks_field():
    s = DecisionInputSerializer(data={"approved": True})
    assert not s.is_valid()
    assert "remarks" in s.errors


def test_decision_input_valid_payload():
    s = DecisionInputSerializer(data={"approved": False, "remarks": "Insufficient evidence"})
    assert s.is_valid(), s.errors
