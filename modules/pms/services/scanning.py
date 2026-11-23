"""Malware scanning (BR-PMS-016): ClamAV over its socket protocol, or the DEBUG-only stand-in."""
from __future__ import annotations

import socket
import struct
from pathlib import Path

from django.conf import settings
from rest_framework import status

from core.api.exceptions import DomainError
from modules.pms.domain.errors import InvalidInput

CHUNK = 64 * 1024
TIMEOUT = 120
# The industry-standard harmless test string every scanner reports as infected.
EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


class ScannerUnavailable(DomainError):
    code = "scanner_unavailable"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message = ("The malware scanner is not available, so documents cannot be accepted right "
               "now. Try again later or tell the PCC_ADMIN.")


def configured() -> str | None:
    """Why scanning cannot run, as a sentence, or None when it can."""
    backend = settings.PMS_MALWARE_SCANNER
    if backend == "development":
        return None if settings.DEBUG else "PMS_MALWARE_SCANNER=development needs DEBUG on."
    if backend != "clamd":
        return f"PMS_MALWARE_SCANNER is '{backend}'; set it to clamd."
    if not (settings.PMS_CLAMD_SOCKET or settings.PMS_CLAMD_HOST):
        return "Set PMS_CLAMD_SOCKET (or PMS_CLAMD_HOST and PORT) to the clamd daemon."
    return None


def _connect() -> socket.socket:
    if settings.PMS_CLAMD_SOCKET:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect(settings.PMS_CLAMD_SOCKET)
        return sock
    return socket.create_connection((settings.PMS_CLAMD_HOST, settings.PMS_CLAMD_PORT),
                                    timeout=TIMEOUT)


def _clamd(path: Path) -> str:
    try:
        with _connect() as sock, path.open("rb") as fh:
            sock.sendall(b"zINSTREAM\0")
            while chunk := fh.read(CHUNK):
                sock.sendall(struct.pack("!L", len(chunk)) + chunk)
            sock.sendall(struct.pack("!L", 0))
            reply = b""
            while not reply.endswith(b"\0"):
                part = sock.recv(4096)
                if not part:
                    break
                reply += part
    except OSError as exc:
        raise ScannerUnavailable() from exc
    answer = reply.rstrip(b"\0").decode("utf-8", "replace")
    if answer.endswith("OK"):
        return "clamd"
    if answer.endswith("FOUND"):
        raise InvalidInput("The document failed the malware check and was not accepted.",
                           code="malware_found")
    raise ScannerUnavailable()


def _development(path: Path) -> str:
    if not settings.DEBUG:
        raise ScannerUnavailable()
    with path.open("rb") as fh:
        if EICAR in fh.read():
            raise InvalidInput("The document failed the malware check and was not accepted.",
                               code="malware_found")
    return "development"


def scan(path: Path) -> str:
    """The scanner's name on a clean result; anything else refuses the document."""
    if configured() is not None:
        raise ScannerUnavailable()
    if settings.PMS_MALWARE_SCANNER == "development":
        return _development(path)
    return _clamd(path)


def ping() -> str | None:
    """For readiness: None when clamd answers PONG, else what is wrong."""
    problem = configured()
    if problem or settings.PMS_MALWARE_SCANNER == "development":
        return problem
    try:
        with _connect() as sock:
            sock.sendall(b"zPING\0")
            return None if sock.recv(64).startswith(b"PONG") else "clamd did not answer PONG."
    except OSError as exc:
        return f"clamd is not reachable ({type(exc).__name__})."
