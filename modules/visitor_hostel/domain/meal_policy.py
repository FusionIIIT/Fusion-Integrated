from decimal import Decimal

class MealPolicy:
    FULL_DAY_MEAL = Decimal("250.00")  # includes breakfast, lunch, dinner
    BREAKFAST = Decimal("60.00")
    LUNCH = Decimal("100.00")
    DINNER = Decimal("100.00")
    TEA = Decimal("15.00")
    MILK = Decimal("25.00")

    @classmethod
    def calculate_single_day_meal_charge(cls, full_day: bool, breakfast: bool, lunch: bool, dinner: bool, tea_count: int = 0, milk_count: int = 0) -> Decimal:
        if full_day:
            base_charge = cls.FULL_DAY_MEAL + (cls.TEA * tea_count) + (cls.MILK * milk_count)
        else:
            base_charge = 0
            if breakfast:
                base_charge += cls.BREAKFAST
            if lunch:
                base_charge += cls.LUNCH
            if dinner:
                base_charge += cls.DINNER
            base_charge += (cls.TEA * tea_count) + (cls.MILK * milk_count)
        return base_charge
