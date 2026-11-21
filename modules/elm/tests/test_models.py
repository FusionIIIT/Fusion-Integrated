"""Architecture and metadata tests for ELM's initial database models."""

from django.db import models

from modules.elm.domain.leave_policy import LeaveCategory
from modules.elm.models import (
    LEAVE_CATEGORY_CHOICES,
    SUBSTITUTE_RESPONSE_CHOICES,
    TRANSACTION_TYPE_CHOICES,
    LeaveAccountTransaction,
    LeaveApplication,
    LeaveApplicationTransition,
    LeaveBalance,
    SubstituteConsent,
)


def test_leave_category_choices_contain_the_six_supported_categories():
    assert {value for value, _label in LEAVE_CATEGORY_CHOICES} == {
        category.value for category in LeaveCategory
    }
    assert len(LEAVE_CATEGORY_CHOICES) == 6


def test_employee_references_are_plain_integer_fields():
    for model in (LeaveBalance, LeaveApplication):
        assert isinstance(model._meta.get_field("user_id"), models.IntegerField)

    assert isinstance(
        SubstituteConsent._meta.get_field("substitute_user_id"),
        models.IntegerField,
    )
    assert isinstance(
        SubstituteConsent._meta.get_field("nominated_by_user_id"),
        models.IntegerField,
    )
    assert isinstance(
        LeaveApplicationTransition._meta.get_field("actor_user_id"),
        models.IntegerField,
    )
    assert isinstance(
        LeaveAccountTransaction._meta.get_field("actor_user_id"),
        models.IntegerField,
    )


def test_all_elm_foreign_keys_target_elm_models():
    elm_models = (
        LeaveBalance,
        LeaveApplication,
        LeaveApplicationTransition,
        SubstituteConsent,
        LeaveAccountTransaction,
    )

    for model in elm_models:
        for field in model._meta.get_fields():
            if (
                getattr(field, "concrete", False)
                and getattr(field, "is_relation", False)
                and field.related_model is not None
            ):
                assert field.related_model._meta.app_label == "elm"


def test_leave_account_has_nonzero_transaction_constraint():
    names = {constraint.name for constraint in LeaveAccountTransaction._meta.constraints}
    assert "elm_tx_delta_nonzero" in names


def test_substitute_response_choices_are_complete():
    assert {value for value, _label in SUBSTITUTE_RESPONSE_CHOICES} == {
        "pending",
        "accepted",
        "declined",
        "cancelled",
    }


def test_all_required_transaction_types_are_available():
    assert {value for value, _label in TRANSACTION_TYPE_CHOICES} == {
        "annual_grant",
        "leave_debit",
        "restoration",
        "carry_forward_in",
        "carry_forward_out",
        "lapse",
        "vl_conversion_in",
        "vl_conversion_out",
        "manual_adjustment",
        "offline_sanction",
    }


def test_leave_balance_current_balance_uses_transaction_ledger():
    assert isinstance(
        LeaveBalance.current_balance,
        property,
    )
    assert LeaveAccountTransaction._meta.get_field("balance").remote_field.model is LeaveBalance
