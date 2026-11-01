import pytest
from decimal import Decimal
from modules.mess.domain.billing_rules import compute_bill

@pytest.mark.parametrize(
    "daily_rate, served_days, special_food_charges, rebate_days, expected_base_amount, expected_special_food_charges, expected_rebate_deduction, expected_total_amount",
    [
        (100, 20, 250, 3, Decimal('2000.00'), Decimal('250.00'), Decimal('300.00'), Decimal('1950.00')),
        (85.50, 10, 0, 0, Decimal('855.00'), Decimal('0.00'), Decimal('855.00'), Decimal('855.00')),
        (100, 20, 0, 0, Decimal('2000.00'), Decimal('0.00'), Decimal('2000.00'), Decimal('2000.00')),
    ]
)
def test_compute_bill(daily_rate, served_days, special_food_charges, rebate_days, expected_base_amount, expected_special_food_charges, expected_rebate_deduction, expected_total_amount):
    result = compute_bill(daily_rate, served_days, special_food_charges, rebate_days)
    assert result['base_amount'] == expected_base_amount
    assert result['special_food_charges'] == expected_special_food_charges
    assert result['rebate_deduction'] == expected_rebate_deduction
    assert result['total_amount'] == expected_total_amount
