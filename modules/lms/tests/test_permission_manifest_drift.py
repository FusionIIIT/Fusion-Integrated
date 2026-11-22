"""Tests asserting zero permission manifest or catalogue drift for LMS (R1-04)."""

import json
from pathlib import Path

from django.core.management import call_command

from modules.lms import registry

MANIFEST_PATH = (
    Path(__file__).resolve().parents[3] / "registry" / "permissions.json"
)


def test_permission_manifest_has_no_drift():
    call_command("permission_manifest", check=True)


def test_all_lms_permissions_are_present_in_manifest():
    assert MANIFEST_PATH.exists(), f"Manifest file missing: {MANIFEST_PATH}"
    data = json.loads(MANIFEST_PATH.read_text())
    lms_section = data.get("modules", {}).get("lms", {})
    manifest_codes = {p["code"] for p in lms_section.get("permissions", [])}

    declared_codes = {code for code, _ in registry.PERMISSIONS}
    missing = declared_codes - manifest_codes
    assert not missing, f"Permissions in registry.py missing from manifest: {missing}"
    extra = manifest_codes - declared_codes
    assert not extra, f"Permissions in manifest not declared in registry.py: {extra}"
