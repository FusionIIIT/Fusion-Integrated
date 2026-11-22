import os
from io import BytesIO

import pytest
from django.test import override_settings

from modules.badms.services import storage


class FakeKms:
    def __init__(self):
        self.data_key = os.urandom(32)

    def generate_data_key(self, **kwargs):
        return {"Plaintext": self.data_key, "CiphertextBlob": b"wrapped"}

    def decrypt(self, **kwargs):
        assert kwargs["CiphertextBlob"] == b"wrapped"
        return {"Plaintext": self.data_key}


@override_settings(BADMS_KMS_KEY_ID="test-key")
def test_envelope_encryption_round_trips_and_rejects_tampering(tmp_path):
    kms = FakeKms()
    context = storage._context_for("badms/test.enc", "test-owner")
    encrypted_path = tmp_path / "artifact.enc"
    plaintext = b"BADMS archive data" * 100

    with encrypted_path.open("wb") as target:
        storage._write_encrypted(
            BytesIO(plaintext),
            target,
            key_id="test-key",
            kms=kms,
            encryption_context=context,
        )

    restored = BytesIO()
    storage._decrypt_file(
        encrypted_path, restored, kms=kms, expected_context=context,
    )
    assert restored.getvalue() == plaintext

    damaged = bytearray(encrypted_path.read_bytes())
    damaged[-17] ^= 0x01
    encrypted_path.write_bytes(damaged)
    with pytest.raises(storage.StorageError, match="integrity check"):
        storage._decrypt_file(
            encrypted_path, BytesIO(), kms=kms, expected_context=context,
        )
