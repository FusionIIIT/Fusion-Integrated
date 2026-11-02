import unittest
from modules.visitor_hostel.domain.inventory_policy import is_threshold_breached, validate_replenishment_request

class TestInventoryPolicy(unittest.TestCase):
    def test_threshold_breached(self):
        self.assertTrue(is_threshold_breached(3, 5))
        self.assertFalse(is_threshold_breached(10, 5))
        self.assertFalse(is_threshold_breached(5, 5))

    def test_replenishment_validation(self):
        self.assertTrue(validate_replenishment_request(10))
        with self.assertRaises(ValueError):
            validate_replenishment_request(0)
        with self.assertRaises(ValueError):
            validate_replenishment_request(-5)

if __name__ == '__main__':
    unittest.main()
