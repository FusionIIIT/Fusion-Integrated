"""LMS test configuration and fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _isolate_media_root(tmp_path, settings):
    """Isolate MEDIA_ROOT to a temporary directory for each test."""
    media_dir = tmp_path / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    settings.MEDIA_ROOT = str(media_dir)
