import pytest
from datetime import datetime, timedelta
from decimal import Decimal

def test_validate_lead_time():
    assert validate_lead_time(datetime(2026,3,1), datetime(2026,3,2)) == True
    assert validate_lead_time(datetime(2026,3,1), datetime(2026,3,1)) == False
    assert validate_lead_time(datetime(2026,3,2), datetime(2026,3,1)) == False

def test_is_decision_expired():
    now = datetime.now()
    assert is_decision_expired(now, now + timedelta(hours=11)) == False
    assert is_decision_expired(now, now + timedelta(hours=12)) == True
    assert is_decision_expired(now, now + timedelta(hours=13)) == True

def test_DECISION_PERIOD_HOURS():
    assert DECISION_PERIOD_HOURS == Decimal('12.00')
