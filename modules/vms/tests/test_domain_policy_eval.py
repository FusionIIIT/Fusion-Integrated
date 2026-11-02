import random
from datetime import datetime, time, timedelta

from modules.vms.domain import policy_eval as pe

D = datetime(2026, 1, 5, 9, 0)


def test_within_visiting_hours():
    s, e = time(8), time(18)
    assert pe.within_visiting_hours(time(8), s, e) and pe.within_visiting_hours(time(18), s, e)
    assert not pe.within_visiting_hours(time(7, 59), s, e)
    assert not pe.within_visiting_hours(D.replace(hour=19), s, e)
    assert pe.within_visiting_hours(D, s, e)


def test_visiting_hours_wrap_midnight():
    s, e = time(22), time(6)
    assert pe.within_visiting_hours(time(23), s, e) and pe.within_visiting_hours(time(5), s, e)
    assert not pe.within_visiting_hours(time(12), s, e)


def test_capped_end_examples():
    assert pe.capped_end(D, D + timedelta(hours=10), 8) == D + timedelta(hours=8)
    assert pe.capped_end(D, D + timedelta(hours=3), 8) == D + timedelta(hours=3)
    assert pe.capped_end(D, D - timedelta(hours=1), 8) == D


def test_capped_end_properties():
    rnd = random.Random(42)
    for _ in range(500):
        end = D + timedelta(minutes=rnd.randint(-600, 2000))
        cap = rnd.choice([0, 0.5, 1, 8, 24])
        out = pe.capped_end(D, end, cap)
        assert D <= out <= D + timedelta(hours=cap)
        assert out <= max(end, D)
        assert pe.capped_end(D, out, cap) == out  # idempotent


def test_advance_ok_boundary():
    assert pe.advance_ok(D, D + timedelta(hours=2), 2)
    assert not pe.advance_ok(D, D + timedelta(hours=2) - timedelta(seconds=1), 2)
    assert not pe.advance_ok(D, D - timedelta(hours=1), 2)


def test_is_same_day():
    assert pe.is_same_day(D, D.replace(hour=23))
    assert not pe.is_same_day(D, D + timedelta(days=1))
