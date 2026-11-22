import pytest
from freezegun import freeze_time

from modules.mms.models import MmsNotification
from modules.mms.tests.helpers import NOW


@pytest.fixture(autouse=True)
def frozen_clock():
    """Wall-clock time is injected, never read: a test that depends on the real date
    fails at midnight, once, and gets marked flaky (testing-strategy.md)."""
    with freeze_time(NOW):
        yield NOW


@pytest.fixture
def sent():
    """`sent("registration_approved")` -> notifications of that event type."""
    def _sent(event_type=None, user_id=None):
        qs = MmsNotification.objects.all()
        if event_type:
            qs = qs.filter(event_type=event_type)
        if user_id:
            qs = qs.filter(recipient_user_id=user_id)
        return list(qs)
    return _sent
