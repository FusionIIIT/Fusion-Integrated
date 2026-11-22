"""Pure Python domain tests: state machines, cron schedules, quota calculations."""
from datetime import UTC

import pytest

from modules.badms.domain import schedules as sched
from modules.badms.domain import state_machine as sm
from modules.badms.domain import storage as st

# ---- Archival Request State Machine ----

def test_archival_valid_workflow_happy_path():
    s1 = sm.transition_archival("none", "submit", "user")
    assert s1 == sm.ARCHIVAL_SUBMITTED

    s2 = sm.transition_archival(s1, "approve", "hod")
    assert s2 == sm.ARCHIVAL_HOD_APPROVED

    s3_non_sensitive = sm.transition_archival(s2, "classify_non_sensitive", "sysadmin")
    assert s3_non_sensitive == sm.ARCHIVAL_CLASSIFIED_NON_SENSITIVE

    s3_sensitive = sm.transition_archival(s2, "classify_sensitive", "sysadmin")
    assert s3_sensitive == sm.ARCHIVAL_CLASSIFIED_SENSITIVE

    s4_encrypted = sm.transition_archival(s3_sensitive, "encrypt_and_create", "it_security")
    assert s4_encrypted == sm.ARCHIVAL_SENSITIVE_ENCRYPTED


def test_archival_rejection():
    s1 = sm.transition_archival("none", "submit", "user")
    s2 = sm.transition_archival(s1, "reject", "hod")
    assert s2 == sm.ARCHIVAL_REJECTED


def test_archival_special_by_super_admin():
    s = sm.transition_archival("none", "special_archive", "super_admin")
    assert s == sm.ARCHIVAL_SPECIAL_ARCHIVED


def test_archival_unauthorized_actor():
    with pytest.raises(sm.UnauthorizedTransitionActorError) as exc_info:
        sm.transition_archival(sm.ARCHIVAL_SUBMITTED, "approve", "student")
    assert exc_info.value.actor_role == "student"


def test_archival_invalid_state_transition():
    with pytest.raises(sm.InvalidStateTransitionError):
        sm.transition_archival(sm.ARCHIVAL_REJECTED, "approve", "hod")


# ---- Storage Extension State Machine ----

def test_storage_extension_workflow():
    s1 = sm.transition_storage_extension("none", "submit", "user")
    assert s1 == sm.STORAGE_SUBMITTED

    s2_app = sm.transition_storage_extension(s1, "approve", "hod")
    assert s2_app == sm.STORAGE_APPROVED

    s2_rej = sm.transition_storage_extension(s1, "reject", "hod")
    assert s2_rej == sm.STORAGE_REJECTED


def test_storage_extension_unauthorized():
    with pytest.raises(sm.UnauthorizedTransitionActorError):
        sm.transition_storage_extension(sm.STORAGE_SUBMITTED, "approve", "faculty")


def test_storage_extension_invalid_transition():
    with pytest.raises(sm.InvalidStateTransitionError):
        sm.transition_storage_extension(sm.STORAGE_APPROVED, "reject", "hod")


# ---- Restoration State Machine ----

def test_restoration_standard_workflow():
    s1 = sm.transition_restoration("none", "request_non_sensitive", "user")
    assert s1 == sm.RESTORATION_REQUESTED_STANDARD

    s2 = sm.transition_restoration(s1, "execute", "sysadmin")
    assert s2 == sm.RESTORATION_RESTORED


def test_restoration_sensitive_workflow():
    s1 = sm.transition_restoration("none", "request_sensitive", "user")
    assert s1 == sm.RESTORATION_SENSITIVE_PENDING

    s2 = sm.transition_restoration(s1, "approve", "sysadmin")
    assert s2 == sm.RESTORATION_APPROVED

    s3 = sm.transition_restoration(s2, "execute", "sysadmin")
    assert s3 == sm.RESTORATION_RESTORED


def test_restoration_sensitive_rejection():
    s1 = sm.transition_restoration("none", "request_sensitive", "user")
    s2 = sm.transition_restoration(s1, "reject", "sysadmin")
    assert s2 == sm.RESTORATION_REJECTED


def test_restoration_unauthorized():
    with pytest.raises(sm.UnauthorizedTransitionActorError):
        sm.transition_restoration(sm.RESTORATION_SENSITIVE_PENDING, "approve", "student")


# ---- Schedules and Cron Resolution ----

def test_validate_cron_expression_valid():
    sched.validate_cron_expression("0 2 * * *")
    sched.validate_cron_expression("*/15 0-4 * * 1-5")
    sched.validate_cron_expression("0 0 1,15 * *")


def test_validate_cron_expression_invalid():
    with pytest.raises(sched.InvalidScheduleParametersError):
        sched.validate_cron_expression("0 2 * *")  # 4 fields

    with pytest.raises(sched.InvalidScheduleParametersError):
        sched.validate_cron_expression("invalid cron format")


def test_resolve_effective_schedule():
    local_active = {"id": 1, "is_active": True}
    local_inactive = {"id": 1, "is_active": False}
    global_active = {"id": 2, "is_active": True}
    global_inactive = {"id": 2, "is_active": False}

    assert sched.resolve_effective_schedule(local_active, global_active) == local_active
    assert sched.resolve_effective_schedule(local_inactive, global_active) == global_active
    assert sched.resolve_effective_schedule(local_inactive, global_inactive) is None
    assert sched.resolve_effective_schedule(None, None) is None


# ---- Storage Quotas ----

def test_check_storage_quota_within_limit():
    st.check_storage_quota(file_size_bytes=100, current_usage_bytes=400, allocated_quota_bytes=500)


def test_check_storage_quota_exceeded():
    with pytest.raises(st.InsufficientQuotaError) as exc_info:
        st.check_storage_quota(file_size_bytes=101, current_usage_bytes=400, allocated_quota_bytes=500)
    assert exc_info.value.current_usage == 400
    assert exc_info.value.allocated_quota == 500


def test_validate_storage_extension_eligibility():
    st.validate_storage_extension_eligibility(current_usage_bytes=500, allocated_quota_bytes=500)
    st.validate_storage_extension_eligibility(current_usage_bytes=600, allocated_quota_bytes=500)

    with pytest.raises(st.QuotaNotFullError):
        st.validate_storage_extension_eligibility(current_usage_bytes=499, allocated_quota_bytes=500)


# ---- Cryptographic Domain Logic ----

def test_crypto_sha256_computation():
    from modules.badms.domain import crypto
    h1 = crypto.compute_sha256("test-data")
    h2 = crypto.compute_sha256(b"test-data")
    assert h1 == h2
    assert len(h1) == 64


def test_crypto_key_and_nonce_generation():
    from modules.badms.domain import crypto
    k = crypto.generate_key()
    n = crypto.generate_nonce()
    assert len(k) == 32
    assert len(n) == 12


def test_crypto_aes_256_gcm_roundtrip():
    from modules.badms.domain import crypto
    key = crypto.generate_key()
    res = crypto.encrypt_aes_256_gcm("Confidential Content", key)
    assert res["key"] == key
    decrypted = crypto.decrypt_aes_256_gcm(res["ciphertext"], key, res["nonce"], res["tag"])
    assert decrypted == b"Confidential Content"


def test_crypto_invalid_parameters():
    from modules.badms.domain import crypto
    with pytest.raises(crypto.CryptoError, match="32 bytes"):
        crypto.encrypt_aes_256_gcm(b"data", key=b"short")

    with pytest.raises(crypto.CryptoError, match="12 bytes"):
        crypto.encrypt_aes_256_gcm(b"data", key=crypto.generate_key(), nonce=b"bad_nonce")

    key = crypto.generate_key()
    nonce = crypto.generate_nonce()
    with pytest.raises(crypto.CryptoError, match="32 bytes"):
        crypto.decrypt_aes_256_gcm(b"c", key=b"short", nonce=nonce, tag=b"1" * 16)

    with pytest.raises(crypto.CryptoError, match="12 bytes"):
        crypto.decrypt_aes_256_gcm(b"c", key=key, nonce=b"short", tag=b"1" * 16)

    with pytest.raises(crypto.CryptoError, match="16 bytes"):
        crypto.decrypt_aes_256_gcm(b"c", key=key, nonce=nonce, tag=b"short")


def test_crypto_tampered_tag_rejection():
    from modules.badms.domain import crypto
    res = crypto.encrypt_aes_256_gcm(b"Authentic Data")
    tampered_tag = bytes([res["tag"][0] ^ 0xFF]) + res["tag"][1:]
    with pytest.raises(crypto.CryptoError, match="authentication verification failed"):
        crypto.decrypt_aes_256_gcm(res["ciphertext"], res["key"], res["nonce"], tampered_tag)


def test_crypto_pure_python_fallback(monkeypatch):
    from modules.badms.domain import crypto
    monkeypatch.setattr(crypto, "_LIBCRYPTO", None)

    key = crypto.generate_key()
    large_payload = b"A" * 120
    res = crypto.encrypt_aes_256_gcm(large_payload, key)
    dec = crypto.decrypt_aes_256_gcm(res["ciphertext"], key, res["nonce"], res["tag"])
    assert dec == large_payload

    tampered_tag = bytes([res["tag"][0] ^ 0xFF]) + res["tag"][1:]
    with pytest.raises(crypto.CryptoError, match="authentication verification failed"):
        crypto.decrypt_aes_256_gcm(res["ciphertext"], key, res["nonce"], tampered_tag)


def test_crypto_get_libcrypto_fallback(monkeypatch):
    import ctypes.util

    from modules.badms.domain import crypto

    monkeypatch.setattr(ctypes.util, "find_library", lambda name: None)
    lib = crypto._get_libcrypto()
    assert lib is None or hasattr(lib, "EVP_aes_256_gcm")


# ---- Retention Policy Domain Logic ----

def test_retention_duration_resolution():
    from modules.badms.domain import retention

    assert retention.resolve_retention_duration("Routine") == 30
    assert retention.resolve_retention_duration("Sensitive") == 365
    assert retention.resolve_retention_duration("Critical") == 2555
    assert retention.resolve_retention_duration("Archival") == 3650

    # Policy override
    assert retention.resolve_retention_duration("Routine", policy_override_days=99) == 99

    # Unknown classification error
    with pytest.raises(retention.RetentionPolicyError, match="Unknown data classification"):
        retention.resolve_retention_duration("NonExistent")


def test_retention_expiry_calculation():
    from datetime import datetime, timedelta

    from modules.badms.domain import retention

    base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    expiry = retention.calculate_retention_expiry(base, "Routine")
    assert expiry == base + timedelta(days=30)

    expiry_custom = retention.calculate_retention_expiry(base, "Routine", policy_override_days=15)
    assert expiry_custom == base + timedelta(days=15)


def test_retention_is_expired():
    from datetime import datetime

    from modules.badms.domain import retention

    base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    # Routine expires after 30 days -> 2026-01-31
    before_expiry = datetime(2026, 1, 15, tzinfo=UTC)
    after_expiry = datetime(2026, 2, 5, tzinfo=UTC)

    assert retention.is_retention_expired(base, "Routine", now=before_expiry) is False
    assert retention.is_retention_expired(base, "Routine", now=after_expiry) is True
    assert (
        retention.is_retention_expired(
            datetime(2020, 1, 1, tzinfo=UTC), "Routine", now=datetime(2026, 1, 1, tzinfo=UTC)
        )
        is True
    )

