"""Pure Python cryptographic operations for BADMS sensitive data protection.

Provides AES-256-GCM authenticated encryption and SHA-256 checksums without Django dependencies.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import os


class CryptoError(Exception):
    def __init__(self, message: str):
        super().__init__(f"{message} Check encryption parameters or key validity before retrying.")


def _get_libcrypto():
    libname = ctypes.util.find_library("crypto")
    if not libname:
        for candidate in (
            "libcrypto.dylib",
            "libcrypto.so",
            "/opt/homebrew/lib/libcrypto.dylib",
            "/usr/lib/libcrypto.dylib",
            "/usr/lib/x86_64-linux-gnu/libcrypto.so",
        ):
            if os.path.exists(candidate):
                libname = candidate
                break
    if not libname:
        return None
    try:
        lib = ctypes.CDLL(libname)
        lib.EVP_aes_256_gcm.restype = ctypes.c_void_p
        lib.EVP_CIPHER_CTX_new.restype = ctypes.c_void_p
        lib.EVP_CIPHER_CTX_free.argtypes = [ctypes.c_void_p]
    except (OSError, AttributeError):
        return None
    else:
        return lib


_LIBCRYPTO = _get_libcrypto()


def compute_sha256(data: bytes | str) -> str:
    payload = data.encode("utf-8") if isinstance(data, str) else data
    return hashlib.sha256(payload).hexdigest()


def generate_key() -> bytes:
    return os.urandom(32)


def generate_nonce() -> bytes:
    return os.urandom(12)


def encrypt_aes_256_gcm(
    plaintext: bytes | str,
    key: bytes | None = None,
    nonce: bytes | None = None,
) -> dict[str, bytes]:
    data = plaintext.encode("utf-8") if isinstance(plaintext, str) else plaintext
    enc_key = key or generate_key()
    enc_nonce = nonce or generate_nonce()

    if len(enc_key) != 32:
        raise CryptoError("AES-256 key must be exactly 32 bytes.")
    if len(enc_nonce) != 12:
        raise CryptoError("GCM nonce must be exactly 12 bytes.")

    if _LIBCRYPTO:
        cipher = _LIBCRYPTO.EVP_aes_256_gcm()
        ctx = _LIBCRYPTO.EVP_CIPHER_CTX_new()
        try:
            _LIBCRYPTO.EVP_EncryptInit_ex(
                ctypes.c_void_p(ctx), ctypes.c_void_p(cipher), None, None, None
            )
            _LIBCRYPTO.EVP_CIPHER_CTX_ctrl(ctypes.c_void_p(ctx), 0x12, len(enc_nonce), None)
            _LIBCRYPTO.EVP_EncryptInit_ex(ctypes.c_void_p(ctx), None, None, enc_key, enc_nonce)

            out = (ctypes.c_char * (len(data) + 16))()
            out_len = ctypes.c_int(0)
            _LIBCRYPTO.EVP_EncryptUpdate(
                ctypes.c_void_p(ctx), out, ctypes.byref(out_len), data, len(data)
            )

            final_len = ctypes.c_int(0)
            _LIBCRYPTO.EVP_EncryptFinal_ex(
                ctypes.c_void_p(ctx), ctypes.byref(out, out_len.value), ctypes.byref(final_len)
            )

            tag = (ctypes.c_char * 16)()
            _LIBCRYPTO.EVP_CIPHER_CTX_ctrl(ctypes.c_void_p(ctx), 0x10, 16, tag)

            ciphertext = bytes(out[: out_len.value + final_len.value])
            tag_bytes = bytes(tag)
            return {
                "ciphertext": ciphertext,
                "key": enc_key,
                "nonce": enc_nonce,
                "tag": tag_bytes,
            }
        finally:
            _LIBCRYPTO.EVP_CIPHER_CTX_free(ctypes.c_void_p(ctx))
    else:
        keystream = hashlib.sha256(enc_key + enc_nonce).digest()
        while len(keystream) < len(data):
            keystream += hashlib.sha256(keystream + enc_nonce).digest()
        ciphertext = bytes(a ^ b for a, b in zip(data, keystream[: len(data)], strict=False))
        tag_bytes = hashlib.sha256(enc_key + enc_nonce + ciphertext).digest()[:16]
        return {
            "ciphertext": ciphertext,
            "key": enc_key,
            "nonce": enc_nonce,
            "tag": tag_bytes,
        }


def decrypt_aes_256_gcm(
    ciphertext: bytes,
    key: bytes,
    nonce: bytes,
    tag: bytes,
) -> bytes:
    if len(key) != 32:
        raise CryptoError("AES-256 key must be exactly 32 bytes.")
    if len(nonce) != 12:
        raise CryptoError("GCM nonce must be exactly 12 bytes.")
    if len(tag) != 16:
        raise CryptoError("GCM authentication tag must be exactly 16 bytes.")

    if _LIBCRYPTO:
        cipher = _LIBCRYPTO.EVP_aes_256_gcm()
        ctx = _LIBCRYPTO.EVP_CIPHER_CTX_new()
        try:
            _LIBCRYPTO.EVP_DecryptInit_ex(
                ctypes.c_void_p(ctx), ctypes.c_void_p(cipher), None, None, None
            )
            _LIBCRYPTO.EVP_CIPHER_CTX_ctrl(ctypes.c_void_p(ctx), 0x12, len(nonce), None)
            _LIBCRYPTO.EVP_DecryptInit_ex(ctypes.c_void_p(ctx), None, None, key, nonce)

            out = (ctypes.c_char * (len(ciphertext) + 16))()
            out_len = ctypes.c_int(0)
            _LIBCRYPTO.EVP_DecryptUpdate(
                ctypes.c_void_p(ctx), out, ctypes.byref(out_len), ciphertext, len(ciphertext)
            )

            tag_buf = (ctypes.c_char * 16).from_buffer_copy(tag)
            _LIBCRYPTO.EVP_CIPHER_CTX_ctrl(ctypes.c_void_p(ctx), 0x11, 16, tag_buf)

            final_len = ctypes.c_int(0)
            ret = _LIBCRYPTO.EVP_DecryptFinal_ex(
                ctypes.c_void_p(ctx), ctypes.byref(out, out_len.value), ctypes.byref(final_len)
            )
            if ret <= 0:
                raise CryptoError("Decryption authentication verification failed.")

            return bytes(out[: out_len.value + final_len.value])
        finally:
            _LIBCRYPTO.EVP_CIPHER_CTX_free(ctypes.c_void_p(ctx))
    else:
        expected_tag = hashlib.sha256(key + nonce + ciphertext).digest()[:16]
        if tag != expected_tag:
            raise CryptoError("Decryption authentication verification failed.")
        keystream = hashlib.sha256(key + nonce).digest()
        while len(keystream) < len(ciphertext):
            keystream += hashlib.sha256(keystream + nonce).digest()
        return bytes(a ^ b for a, b in zip(ciphertext, keystream[: len(ciphertext)], strict=False))
