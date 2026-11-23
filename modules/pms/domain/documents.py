"""Document rules: what may be uploaded, by whom, when, and who may read each version."""
from __future__ import annotations

from collections.abc import Iterable

from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import InvalidInput

MAX_BYTES = 50 * 1024 * 1024         # BR-PMS-015: "under 50 MB", so strictly less
PDF_MAGIC = b"%PDF-"                 # BR-PMS-014: checked in the bytes, not the name
PUBLIC_INTERNAL = "public_internal"
CONFIDENTIAL = "confidential"
RESTRICTED = "restricted"
SENSITIVITIES = (PUBLIC_INTERNAL, CONFIDENTIAL, RESTRICTED)      # ruling C16
KINDS = ("specification", "claims", "drawings", "supporting", "filing_package",
         "office_action", "other")

# How a person relates to one application; scoping decides which apply.
APPLICANT = "applicant"
INVENTOR = "inventor"
REVIEWING_DIRECTOR = "reviewing_director"
PAST_DIRECTOR = "past_director"
AREA_DIRECTOR = "area_director"
ATTORNEY = "attorney"
PCC_ADMIN = "pcc_admin"

# Ruling C16 and blueprint Q-3.
_READERS = {
    PUBLIC_INTERNAL: frozenset({APPLICANT, INVENTOR, REVIEWING_DIRECTOR, PAST_DIRECTOR,
                                AREA_DIRECTOR, ATTORNEY, PCC_ADMIN}),
    CONFIDENTIAL: frozenset({APPLICANT, INVENTOR, REVIEWING_DIRECTOR, PAST_DIRECTOR,
                             ATTORNEY, PCC_ADMIN}),
    RESTRICTED: frozenset({APPLICANT, INVENTOR, REVIEWING_DIRECTOR, ATTORNEY, PCC_ADMIN}),
}


def check_pdf(head: bytes, filename: str) -> None:
    if not filename.lower().endswith(".pdf") or not head.startswith(PDF_MAGIC):
        raise InvalidInput("Only PDF documents are accepted. Save the file as PDF and "
                           "upload it again.", code="not_pdf")


def check_size(size: int) -> None:
    if size <= 0:
        raise InvalidInput("The file is empty.", code="empty_file")
    if size >= MAX_BYTES:
        raise InvalidInput("Documents must be under 50 MB. Compress or split the PDF and "
                           "upload it again.", code="file_too_large")


def check_sensitivity(value: str) -> str:
    if value not in SENSITIVITIES:
        raise InvalidInput("Choose a sensitivity: Public-internal, Confidential or "
                           "Restricted.", code="invalid_sensitivity")
    return value


def check_kind(value: str) -> str:
    if value not in KINDS:
        raise InvalidInput("Choose what kind of document this is.", code="invalid_kind")
    return value


def next_version(highest: int | None) -> int:
    """BR-PMS-082: versions count up from 1 with no gaps."""
    return 1 if highest is None else highest + 1


def may_upload(relations: Iterable[str], status: str) -> bool:
    """BR-PMS-086 / BR-PMS-087 as ruled (B6): who may add a version, by application status."""
    rel = set(relations)
    if status in sm.TERMINAL:
        return False
    if PCC_ADMIN in rel:
        return True
    if ATTORNEY in rel and status in {sm.ATTORNEY_ASSIGNED, sm.FILED, sm.GRANTED}:
        return True
    return APPLICANT in rel and status in sm.APPLICANT_EDITABLE


def may_read(relations: Iterable[str], sensitivity: str) -> bool:
    """BR-PMS-084 / BR-PMS-130: a version is readable only by its sensitivity's readers."""
    return bool(set(relations) & _READERS.get(sensitivity, frozenset()))
