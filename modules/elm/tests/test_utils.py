"""Unit tests for ELM API utility helpers."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from modules.elm.api.utils import get_caller_id


class TestGetCallerId:
    def test_none_request_returns_none(self):
        assert get_caller_id(None) is None

    def test_unauthenticated_request_returns_none(self):
        req = SimpleNamespace()
        assert get_caller_id(req) is None

    def test_principal_user_id_resolved(self):
        principal = SimpleNamespace(user_id=1042)
        req = SimpleNamespace(principal=principal)
        assert get_caller_id(req) == 1042

    def test_authenticated_django_user_resolved(self):
        user = MagicMock()
        user.is_authenticated = True
        user.pk = 2055
        req = SimpleNamespace(user=user)
        assert get_caller_id(req) == 2055

    def test_unauthenticated_django_user_returns_none(self):
        user = MagicMock()
        user.is_authenticated = False
        user.pk = 2055
        req = SimpleNamespace(user=user)
        assert get_caller_id(req) is None
