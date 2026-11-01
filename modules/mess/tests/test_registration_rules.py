import pytest
from datetime import date, timedelta
from decimal import Decimal

def test_window_is_open():
    assert window_is_open('OPEN', date(2026,7,1), date(2026,7,10), date(2026,7,5))
    assert not window_is_open('CLOSED', date(2026,7,1), date(2026,7,10), date(2026,7,5))
    assert window_is_open('OPEN', date(2026,7,1), date(2026,7,10), date(2026,7,6))
    assert not window_is_open('CLOSED', date(2026,7,1), date(2026,7,10), date(2026,7,6))

def test_deregistration_effective_date():
    assert deregistration_effective_date(date(2026,2,28)) == date(2026,3,1)

def test_validate_window():
    with pytest.raises(ValueError):
        validate_window('')
    with pytest.raises(ValueError):
        validate_window('Closes on before opens on')
    assert validate_window('Valid input') == []

def test_closes_on_before_opens_on():
    with pytest.raises(ValueError):
        validate_window('Closes on before opens on', 'Closes on before opens on')
