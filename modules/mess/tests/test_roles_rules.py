import pytest
from datetime import datetime, timedelta
from decimal import Decimal

def test_overlaps():
    start1 = datetime(2020, 1, 1)
    end1 = datetime(2020, 1, 3)
    start2 = datetime(2020, 1, 2)
    end2 = datetime(2020, 1, 4)
    assert overlaps(start1, end1, start2, end2) == False

    start1 = datetime(2020, 1, 1)
    end1 = datetime(2020, 1, 3)
    start2 = datetime(2020, 1, 3)
    end2 = datetime(2020, 1, 5)
    assert overlaps(start1, end1, start2, end2) == True

def test_can_assign():
    assert can_assign('CARETAKER', datetime(2020, 1, 1), datetime(2020, 1, 3), None) == False
    assert can_assign('CARETAKER', datetime(2020, 1, 1), datetime(2020, 1, 3), datetime(2020, 1, 2)) == False
    assert can_assign('CARETAKER', datetime(2020, 1, 1), datetime(2020, 1, 3), datetime(2020, 1, 3)) == True
    assert can_assign('WARDEN', datetime(2020, 1, 1), datetime(2020, 1, 3), None) == True
    assert can_assign('WARDEN', datetime(2020, 1, 1), datetime(2020, 1, 3), datetime(2020, 1, 2)) == False

def test_is_active():
    start = datetime(2020, 1, 1)
    end = datetime(2020, 1, 3)
    now = datetime(2020, 1, 2)
    assert is_active(start, end, now) == True

    now = datetime(2020, 1, 4)
    assert is_active(start, end, now) == False
