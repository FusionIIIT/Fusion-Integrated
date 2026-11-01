"""Authenticated AES-256-GCM encryption for uploaded archive payloads."""
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.files.base import ContentFile
from rest_framework.exceptions import ValidationError


MAX_ARCHIVE_BYTES = 25 * 1024 * 1024


def _key():
    configured = getattr(settings, "BADMS_ARCHIVE_ENCRYPTION_KEY", "")
    if configured:
        try:
            key = bytes.fromhex(configured)
        except ValueError as exc:
            raise RuntimeError("BADMS_ARCHIVE_ENCRYPTION_KEY must be 64 hexadecimal characters.") from exc
        if len(key) != 32:
            raise RuntimeError("BADMS_ARCHIVE_ENCRYPTION_KEY must decode to 32 bytes.")
        return key
    return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()


def encrypt_upload(upload):
    if upload.size > MAX_ARCHIVE_BYTES:
        raise ValidationError({"attachment": "Files must be 25 MB or smaller."})
    nonce = os.urandom(12)
    ciphertext = AESGCM(_key()).encrypt(nonce, upload.read(), None)
    return ContentFile(nonce + ciphertext, name=f"{upload.name}.aesgcm")


def decrypt_payload(blob):
    payload = blob.read()
    if len(payload) < 29:
        raise ValueError("Encrypted archive is incomplete.")
    return AESGCM(_key()).decrypt(payload[:12], payload[12:], None)
