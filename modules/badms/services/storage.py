from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.conf import settings

MAGIC = b"BADMSENC1"
TAG_LENGTH = 16
CHUNK_SIZE = 1024 * 1024
MAX_HEADER_BYTES = 16 * 1024


class StorageError(Exception):
    def __init__(self, message: str, *, code: str = "storage_unavailable"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class StoredObject:
    key: str
    sha256: str
    size_bytes: int


def _configuration() -> tuple[str, str, str]:
    bucket = getattr(settings, "BADMS_S3_BUCKET", "")
    key_id = getattr(settings, "BADMS_KMS_KEY_ID", "")
    region = getattr(settings, "BADMS_AWS_REGION", "")
    if not bucket or not key_id or not region:
        raise StorageError(
            "BADMS object storage and key management are not configured.",
            code="storage_not_configured",
        )
    return bucket, key_id, region


def _clients():
    _, _, region = _configuration()
    session = boto3.session.Session()
    config = Config(connect_timeout=3, read_timeout=30, retries={"max_attempts": 2})
    try:
        return (
            session.client(
                "s3", region_name=region, use_ssl=True, verify=True, config=config,
            ),
            session.client(
                "kms", region_name=region, use_ssl=True, verify=True, config=config,
            ),
        )
    except BotoCoreError as exc:
        raise StorageError("BADMS AWS clients could not be initialized.",
                           code="aws_client_unavailable") from exc


def new_object_key(*, user_id: int, category: str, suffix: str = ".enc") -> str:
    if category not in {"archives", "backups"}:
        raise ValueError("Unsupported BADMS storage category.")
    return f"badms/users/{user_id}/{category}/{uuid4().hex}{suffix}"


def _context_for(key: str, owner: str) -> dict[str, str]:
    return {"application": "badms", "object_key": key, "owner": owner}


def _write_encrypted(source: BinaryIO, destination: BinaryIO, *, key_id: str,
                     kms, encryption_context: dict[str, str]) -> None:
    try:
        generated = kms.generate_data_key(
            KeyId=key_id,
            KeySpec="AES_256",
            EncryptionContext=encryption_context,
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError(
            "BADMS could not obtain an AES-256 data key.",
            code="key_generation_failed",
        ) from exc

    data_key = bytearray(generated["Plaintext"])
    try:
        nonce = os.urandom(12)
        header = json.dumps({
            "version": 1,
            "key_id": key_id,
            "wrapped_key": base64.b64encode(generated["CiphertextBlob"]).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "context": encryption_context,
        }, separators=(",", ":"), sort_keys=True).encode("utf-8")
        if len(header) > MAX_HEADER_BYTES:
            raise StorageError("BADMS encryption metadata is too large.",
                               code="invalid_encryption_header")
        encryptor = Cipher(
            algorithms.AES(bytes(data_key)), modes.GCM(nonce),
        ).encryptor()
        destination.write(MAGIC)
        destination.write(struct.pack(">I", len(header)))
        destination.write(header)
        while chunk := source.read(CHUNK_SIZE):
            destination.write(encryptor.update(chunk))
        destination.write(encryptor.finalize())
        destination.write(encryptor.tag)
    finally:
        data_key[:] = b"\x00" * len(data_key)


def _decrypt_file(source_path: str | Path, destination: BinaryIO, *,
                  kms, expected_context: dict[str, str]) -> None:
    with Path(source_path).open("rb") as source:
        if source.read(len(MAGIC)) != MAGIC:
            raise StorageError("Stored artifact has an invalid format.",
                               code="invalid_artifact")
        raw_length = source.read(4)
        if len(raw_length) != 4:
            raise StorageError("Stored artifact has an incomplete header.",
                               code="invalid_artifact")
        header_length = struct.unpack(">I", raw_length)[0]
        if not 0 < header_length <= MAX_HEADER_BYTES:
            raise StorageError("Stored artifact has an invalid header length.",
                               code="invalid_artifact")
        encoded_header = source.read(header_length)
        if len(encoded_header) != header_length:
            raise StorageError("Stored artifact has incomplete encryption metadata.",
                               code="invalid_artifact")
        try:
            header = json.loads(encoded_header)
            wrapped_key = base64.b64decode(header["wrapped_key"], validate=True)
            nonce = base64.b64decode(header["nonce"], validate=True)
            context = header["context"]
            key_id = header["key_id"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise StorageError("Stored artifact has invalid encryption metadata.",
                               code="invalid_artifact") from exc
        if (not isinstance(header, dict) or header.get("version") != 1
                or context != expected_context
                or key_id != settings.BADMS_KMS_KEY_ID):
            raise StorageError("Stored artifact metadata does not match the request.",
                               code="artifact_context_mismatch")
        if len(nonce) != 12:
            raise StorageError("Stored artifact has an invalid nonce.",
                               code="invalid_artifact")

        source.seek(0, os.SEEK_END)
        encrypted_end = source.tell()
        ciphertext_start = len(MAGIC) + 4 + header_length
        if encrypted_end < ciphertext_start + TAG_LENGTH:
            raise StorageError("Stored artifact is truncated.", code="invalid_artifact")
        source.seek(encrypted_end - TAG_LENGTH)
        tag = source.read(TAG_LENGTH)
        source.seek(ciphertext_start)

        try:
            decrypted = kms.decrypt(
                CiphertextBlob=wrapped_key,
                KeyId=key_id,
                EncryptionContext=expected_context,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(
                "BADMS could not unwrap the artifact data key.",
                code="key_decryption_failed",
            ) from exc
        data_key = bytearray(decrypted["Plaintext"])
        try:
            decryptor = Cipher(
                algorithms.AES(bytes(data_key)), modes.GCM(nonce, tag),
            ).decryptor()
            remaining = encrypted_end - TAG_LENGTH - ciphertext_start
            while remaining:
                chunk = source.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    raise StorageError("Stored artifact is truncated.",
                                       code="invalid_artifact")
                remaining -= len(chunk)
                destination.write(decryptor.update(chunk))
            try:
                destination.write(decryptor.finalize())
            except InvalidTag as exc:
                raise StorageError(
                    "Stored artifact failed its AES-GCM integrity check.",
                    code="artifact_integrity_failed",
                ) from exc
        finally:
            data_key[:] = b"\x00" * len(data_key)


def store_stream(source: BinaryIO, *, key: str, owner: str) -> StoredObject:
    bucket, key_id, _ = _configuration()
    s3, kms = _clients()
    context = _context_for(key, owner)
    try:
        with tempfile.NamedTemporaryFile() as encrypted:
            _write_encrypted(
                source, encrypted, key_id=key_id, kms=kms,
                encryption_context=context,
            )
            encrypted.flush()
            encrypted.seek(0)
            digest = hashlib.sha256()
            size = 0
            for block in iter(lambda: encrypted.read(CHUNK_SIZE), b""):
                digest.update(block)
                size += len(block)
            encrypted.seek(0)
            checksum = digest.hexdigest()
            s3.upload_fileobj(
                encrypted,
                bucket,
                key,
                ExtraArgs={
                    "ServerSideEncryption": "aws:kms",
                    "SSEKMSKeyId": key_id,
                    "Metadata": {"sha256": checksum, "owner": owner},
                },
            )
        try:
            verify_object(key=key, expected_sha256=checksum, expected_size=size)
        except StorageError:
            try:
                s3.delete_object(Bucket=bucket, Key=key)
            except (BotoCoreError, ClientError) as cleanup_error:
                raise StorageError(
                    "BADMS failed verification and could not clean up the object.",
                    code="object_cleanup_failed",
                ) from cleanup_error
            raise
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("BADMS could not store or verify the encrypted artifact.",
                           code="object_storage_failed") from exc
    return StoredObject(key=key, sha256=checksum, size_bytes=size)


def verify_object(*, key: str, expected_sha256: str,
                  expected_size: int | None = None) -> None:
    bucket, _, _ = _configuration()
    s3, _ = _clients()
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        digest = hashlib.sha256()
        size = 0
        for block in response["Body"].iter_chunks(chunk_size=CHUNK_SIZE):
            digest.update(block)
            size += len(block)
        if (digest.hexdigest() != expected_sha256
                or (expected_size is not None and size != expected_size)):
            raise StorageError(
                "Stored artifact checksum or size did not match the upload.",
                code="artifact_integrity_failed",
            )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("BADMS could not verify the stored artifact.",
                           code="object_verification_failed") from exc


def decrypt_object_to_temp(*, key: str, owner: str) -> str:
    bucket, _, _ = _configuration()
    s3, kms = _clients()
    context = _context_for(key, owner)
    path = ""
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        with tempfile.NamedTemporaryFile(delete=False) as encrypted:
            path = encrypted.name
            for block in response["Body"].iter_chunks(chunk_size=CHUNK_SIZE):
                encrypted.write(block)
        plaintext_path = f"{path}.plain"
        try:
            with open(plaintext_path, "wb") as plaintext:
                _decrypt_file(path, plaintext, kms=kms, expected_context=context)
        except Exception:
            Path(plaintext_path).unlink(missing_ok=True)
            raise
        else:
            return plaintext_path
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("BADMS could not retrieve the encrypted artifact.",
                           code="object_retrieval_failed") from exc
    finally:
        if path:
            Path(path).unlink(missing_ok=True)


def delete_object(key: str) -> None:
    bucket, _, _ = _configuration()
    s3, _ = _clients()
    try:
        s3.delete_object(Bucket=bucket, Key=key)
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("BADMS could not remove an orphaned artifact.",
                           code="object_cleanup_failed") from exc


def user_usage_bytes(user_id: int) -> int:
    bucket, _, _ = _configuration()
    s3, _ = _clients()
    prefix = f"badms/users/{user_id}/"
    total = 0
    try:
        pages = s3.get_paginator("list_objects_v2").paginate(
            Bucket=bucket, Prefix=prefix,
        )
        for page in pages:
            total += sum(item["Size"] for item in page.get("Contents", []))
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("BADMS could not measure user storage usage.",
                           code="capacity_measurement_failed") from exc
    return total
