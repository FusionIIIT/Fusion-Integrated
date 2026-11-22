import pytest
from django.test import override_settings
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.badms.services.storage import require_secure_storage, retention_deadline

pytestmark = pytest.mark.django_db


def test_sensitive_storage_requires_private_aes256_and_tls():
    with (
        override_settings(
            BADMS_STORAGE_BACKEND="s3",
            BADMS_STORAGE_PRIVATE=False,
            BADMS_STORAGE_AES256=True,
            BADMS_STORAGE_TLS=True,
        ),
        pytest.raises(ConflictError) as exc,
    ):
        require_secure_storage()
    assert exc.value.code == "storage_not_configured"

    with (
        override_settings(
            BADMS_STORAGE_BACKEND="s3",
            BADMS_STORAGE_PRIVATE=True,
            BADMS_STORAGE_AES256=False,
            BADMS_STORAGE_TLS=True,
        ),
        pytest.raises(ConflictError) as exc,
    ):
        require_secure_storage()
    assert exc.value.code == "storage_encryption_not_configured"

    with (
        override_settings(
            BADMS_STORAGE_BACKEND="s3",
            BADMS_STORAGE_PRIVATE=True,
            BADMS_STORAGE_AES256=True,
            BADMS_STORAGE_TLS=False,
        ),
        pytest.raises(ConflictError) as exc,
    ):
        require_secure_storage()
    assert exc.value.code == "storage_tls_not_configured"


@pytest.mark.parametrize("policy", [{}, {"Sensitive": 0}, {"Sensitive": -4}, {"Sensitive": "365"}])
def test_missing_or_invalid_retention_policy_fails_closed(policy):
    with override_settings(BADMS_RETENTION_DAYS=policy), pytest.raises(ConflictError) as exc:
        retention_deadline("Sensitive")
    assert exc.value.code == "retention_policy_missing"


def test_retention_uses_configured_institute_duration():
    with override_settings(BADMS_RETENTION_DAYS={"Sensitive": 365}):
        deadline = retention_deadline("Sensitive")
    assert 364 <= (deadline - timezone.now()).days <= 365


def test_saved_policy_takes_precedence_over_environment_defaults():
    from modules.badms.models import SecurityPolicy

    SecurityPolicy.objects.create(
        retention_days={"Critical": 1, "Sensitive": 30, "Routine": 1, "Archival": 1}
    )
    with override_settings(BADMS_RETENTION_DAYS={"Sensitive": 365}):
        deadline = retention_deadline("Sensitive")
    assert 29 <= (deadline - timezone.now()).days <= 30


def test_production_readiness_names_unmet_prerequisites():
    from modules.badms.registry import readiness

    with override_settings(
        DEBUG=False,
        BADMS_STORAGE_BACKEND="local",
        BADMS_STORAGE_PRIVATE=False,
        BADMS_STORAGE_AES256=False,
        BADMS_STORAGE_TLS=False,
        BADMS_RETENTION_DAYS={},
        BADMS_USER_QUOTA_BYTES=None,
        BADMS_AVAILABLE_STORAGE_BYTES=None,
        BADMS_SYSADMIN_ALERT_EMAILS=[],
        BADMS_IT_SECURITY_EMAILS=[],
        BADMS_HOD_EMAILS={},
    ):
        unmet = readiness()

    assert any("BADMS_STORAGE_BACKEND" in item for item in unmet)
    assert any("retention days" in item for item in unmet)
    assert any("BADMS_USER_QUOTA_BYTES" in item for item in unmet)
    assert any("BADMS_HOD_EMAILS" in item for item in unmet)
