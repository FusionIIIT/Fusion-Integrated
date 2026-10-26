import pytest
from freezegun import freeze_time


@pytest.fixture(autouse=True)
def elm_test_clock():
    with freeze_time("2026-10-26"):
        yield
