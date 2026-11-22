"""Tests for gymkhana system checks and readiness command."""
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from modules.gymkhana import checks, registry

pytestmark = pytest.mark.django_db


def test_check_upload_root_inside_base_dir(tmp_path):
    # If upload root is inside BASE_DIR, check returns an Error
    fake_inside = Path(settings.BASE_DIR) / "inside_uploads"
    with override_settings(GYMKHANA_UPLOAD_ROOT=str(fake_inside)):
        errors = checks.check_upload_root(None)
        assert len(errors) == 1
        assert errors[0].id == "gymkhana.files.E001"


def test_check_upload_root_outside_base_dir():
    with TemporaryDirectory() as tmp_dir, override_settings(GYMKHANA_UPLOAD_ROOT=tmp_dir):
        errors = checks.check_upload_root(None)
        # May return W001 if permissions are loose, but never E001
        assert not any(e.id == "gymkhana.files.E001" for e in errors)


def test_readiness_function():
    with TemporaryDirectory() as tmp_dir:
        with override_settings(GYMKHANA_UPLOAD_ROOT=tmp_dir, GYMKHANA_VENUES=("Hall 1",)):
            unmet = registry.readiness()
            assert unmet == []

        # If venues empty
        with override_settings(GYMKHANA_UPLOAD_ROOT=tmp_dir, GYMKHANA_VENUES=()):
            unmet = registry.readiness()
            assert any("venues" in msg.lower() for msg in unmet)

        # If upload root missing
        with override_settings(GYMKHANA_UPLOAD_ROOT="/path/that/does/not/exist/surely"):
            unmet = registry.readiness()
            assert any("upload directory" in msg.lower() for msg in unmet)


def test_readiness_management_command():
    with TemporaryDirectory() as tmp_dir:
        with override_settings(GYMKHANA_UPLOAD_ROOT=tmp_dir, GYMKHANA_VENUES=("Hall 1",)):
            # Ready: exits 0
            call_command("gymkhana_readiness")

        # Not ready: raises CommandError
        with (
            override_settings(GYMKHANA_UPLOAD_ROOT="/nonexistent/dir", GYMKHANA_VENUES=()),
            pytest.raises(CommandError),
        ):
            call_command("gymkhana_readiness")
