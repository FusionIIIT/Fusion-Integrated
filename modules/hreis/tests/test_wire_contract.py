"""Committed TypeScript contracts must follow actual OpenAPI fields, optionality and enums."""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize("script", ["hreis_client_types.py", "hreis_reference.py"])
def test_types_and_enforcement_reference_are_derived_without_drift(script):
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, str(root / "ops/docs" / script), "--check"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_http_operation_has_synthetic_request_and_response_examples():
    root = Path(__file__).resolve().parents[3]
    schema = yaml.safe_load((root / "openapi/fusion-integrated.v1.yaml").read_text())
    operations = 0
    for path, item in schema["paths"].items():
        if not path.startswith("/api/v1/hreis/"):
            continue
        for method in ("get", "post", "patch"):
            if method not in item:
                continue
            operation = item[method]
            for code, response in operation["responses"].items():
                if code in ("200", "201"):
                    assert response["content"]["application/json"]["examples"], (method, path)
            if "requestBody" in operation:
                assert operation["requestBody"]["content"]["application/json"]["examples"], (
                    method,
                    path,
                )
            operations += 1
    assert operations == 26
