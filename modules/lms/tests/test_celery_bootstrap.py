import os
import subprocess
import sys


def test_fresh_django_process_binds_release_task_to_configured_app():
    code = """import django
django.setup()
from config.celery import app
from modules.lms.tasks import release_content
from django.conf import settings
assert release_content.app is app
assert release_content.app.conf.broker_url == settings.CELERY_BROKER_URL
print("configured release app: fusion_integrated")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings.test"},
        check=True,
    )
    assert "configured release app: fusion_integrated" in result.stdout
