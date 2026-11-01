from decimal import Decimal, getcontext

def compute_bill(daily_rate, served_days, special_food_charges, rebate_days):
    getcontext().prec = 3
    base_amount = Decimal(str(daily_rate)) * Decimal(str(served_days))
    rebate_deduction = Decimal(str(daily_rate)) * Decimal(str(rebate_days))
    total_amount = base_amount + special_food_charges - rebate_deduction
    return {
        'base_amount': round(base_amount, 2),
        'special_food_charges': round(special_food_charges, 2),
        'rebate_deduction': round(rebate_deduction, 2),
        'total_amount': round(total_amount, 2)
    }
