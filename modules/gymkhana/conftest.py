"""Shared by every Gymkhana test: uploads never leave the test's own directory."""

import pytest


@pytest.fixture(autouse=True)
def _private_uploads(settings, tmp_path):
    settings.PLACEMENT_UPLOAD_ROOT = str(tmp_path / "uploads")
