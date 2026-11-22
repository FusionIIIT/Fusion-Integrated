"""Tests for check_badms_readiness management command."""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
import pytest

from modules.badms.registry import readiness

pytestmark = pytest.mark.django_db


def test_readiness_in_debug_returns_empty():
    with override_settings(DEBUG=True):
        assert readiness() == []
        out = StringIO()
        call_command("check_badms_readiness", stdout=out)
        assert "prerequisites are configured" in out.getvalue()


def test_readiness_in_production_unconfigured_raises():
    with override_settings(DEBUG=False, BADMS_STORAGE_BACKEND="local"):
        unmet = readiness()
        assert len(unmet) > 0
        with pytest.raises(CommandError) as exc_info:
            call_command("check_badms_readiness", stderr=StringIO())
        assert "prerequisite(s) unmet" in str(exc_info.value)
