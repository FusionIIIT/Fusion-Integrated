import unittest
from decimal import Decimal
from modules.visitor_hostel.domain.meal_policy import MealPolicy

class TestMealPolicy(unittest.TestCase):
    def test_full_day_meal(self):
        meal_policy = MealPolicy()
        self.assertEqual(
            meal_policy.calculate_single_day_meal_charge(
                full_day=True, breakfast=False, lunch=False, dinner=False, tea_count=2, milk_count=1), 
            Decimal("305.00")) # 250 + 2*15 + 1*25
    
    def test_individual_meals(self):
        meal_policy = MealPolicy()
        self.assertEqual(
            meal_policy.calculate_single_day_meal_charge(
                full_day=False, breakfast=True, lunch=True, dinner=False, tea_count=1, milk_count=0), 
            Decimal("175.00")) # 60 + 100 + 15
    
    def test_no_meals(self):
        meal_policy = MealPolicy()
        self.assertEqual(
            meal_policy.calculate_single_day_meal_charge(
                full_day=False, breakfast=False, lunch=False, dinner=False, tea_count=0, milk_count=0), 
            Decimal("0.00")) # No meals selected
