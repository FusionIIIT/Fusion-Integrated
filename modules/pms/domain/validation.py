"""Content rules for what people submit; each refusal says what to fix."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from modules.pms.domain.errors import InvalidInput

MIN_JUSTIFICATION = 50          # BR-PMS-030
MIN_FEEDBACK_RESPONSE = 50      # ruling C12
LIMITS = {"title": 300, "abstract": 5000, "description": 100_000, "claims": 50_000}
FIELD_LABELS = {"title": "title", "abstract": "abstract", "description": "detailed description",
                "claims": "claims", "domain_code": "technical area"}
RECOMMENDATIONS = ("file_patent", "do_not_file", "needs_amendment")   # BR-PMS-046
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
HUNDRED = Decimal("100.00")


def _text(value) -> str:
    return (value or "").strip() if isinstance(value, str) or value is None else str(value)


def check_lengths(fields: dict) -> None:
    for name, limit in LIMITS.items():
        if len(_text(fields.get(name))) > limit:
            raise InvalidInput(f"The {FIELD_LABELS[name]} is longer than {limit:,} characters.",
                               code="field_too_long")


def missing_fields(fields: dict, *, inventors: int, documents: int,
                   domain_codes: frozenset[str]) -> list[str]:
    """BR-PMS-017 / PMS-AFR-038: what is still needed before submission, by name."""
    missing = [FIELD_LABELS[name] for name in ("title", "abstract", "description", "claims")
               if not _text(fields.get(name))]
    code = _text(fields.get("domain_code"))
    if not code:
        missing.append(FIELD_LABELS["domain_code"])
    elif code not in domain_codes:
        missing.append("a technical area that is currently offered")
    if inventors == 0:
        missing.append("inventor information")
    if documents == 0:
        missing.append("at least one supporting document")
    return missing


def check_justification(text) -> str:
    """BR-PMS-030: a decision explains itself in at least 50 characters."""
    cleaned = _text(text)
    if len(cleaned) < MIN_JUSTIFICATION:
        raise InvalidInput(
            f"Write a justification of at least {MIN_JUSTIFICATION} characters "
            f"({len(cleaned)} so far) so the applicant knows why.",
            code="justification_too_short")
    if len(cleaned) > 10_000:
        raise InvalidInput("Keep the justification under 10,000 characters.",
                           code="justification_too_long")
    return cleaned


def check_revision_responses(feedback_keys: tuple[str, ...], responses: dict,
                             *, changed: bool) -> dict[str, str]:
    """BR-PMS-036 as ruled (C12): answer every piece of feedback and change something."""
    if not isinstance(responses, dict):
        raise InvalidInput("Send one response for each piece of feedback.",
                           code="feedback_unanswered")
    cleaned = {}
    for key in feedback_keys:
        text = _text(responses.get(key))
        if len(text) < MIN_FEEDBACK_RESPONSE:
            raise InvalidInput(
                f"Explain how you addressed the {key.replace('_', ' ')} feedback in at least "
                f"{MIN_FEEDBACK_RESPONSE} characters before resubmitting.",
                code="feedback_unanswered")
        cleaned[key] = text[:10_000]
    if not changed:
        raise InvalidInput("Change at least one field or upload a revised document before "
                           "resubmitting; the resubmission is otherwise identical.",
                           code="revision_unchanged")
    return cleaned


def check_withdrawal_reason(reason) -> str:
    """BR-PMS-069."""
    cleaned = _text(reason)
    if not cleaned:
        raise InvalidInput("Give a reason for withdrawing the application.",
                           code="reason_required")
    return cleaned[:2000]


def check_appeal_grounds(grounds, justification) -> tuple[str, str]:
    """BR-PMS-094."""
    g, j = _text(grounds), _text(justification)
    if not g:
        raise InvalidInput("State the grounds for your appeal.", code="grounds_required")
    if not j:
        raise InvalidInput("Explain why the grounds justify a different decision.",
                           code="justification_required")
    return g[:5000], j[:10_000]


def check_decline_reason(reason) -> str:
    cleaned = _text(reason)
    if not cleaned:
        raise InvalidInput("Say why you are declining, so PCC_ADMIN can reassign sensibly.",
                           code="reason_required")
    return cleaned[:2000]


@dataclass(frozen=True)
class InventorInput:
    name: str
    share_percent: Decimal
    user_id: int | None = None
    email: str = ""
    affiliation: str = ""


def parse_share(value) -> Decimal:
    try:
        share = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InvalidInput("Each ownership share must be a percentage, like 50 or 33.34.",
                           code="invalid_share") from exc
    if not share.is_finite() or share != share.quantize(Decimal("0.01")):
        raise InvalidInput("Ownership shares allow at most two decimal places.",
                           code="invalid_share")
    return share


def check_inventors(inventors: list[InventorInput]) -> None:
    """BR-PMS-073 / BR-PMS-074 as ruled (C11): named people, shares above 0 totalling 100."""
    if not inventors:
        raise InvalidInput("List at least one inventor.", code="inventors_required")
    if len(inventors) > 50:
        raise InvalidInput("An application can list at most 50 inventors.",
                           code="too_many_inventors")
    seen: set[int] = set()
    for inv in inventors:
        if not _text(inv.name) or len(inv.name) > 200:
            raise InvalidInput("Every inventor needs a name of at most 200 characters.",
                               code="inventor_name_required")
        if inv.user_id is None and not _text(inv.affiliation):
            raise InvalidInput(f"Give {inv.name}'s affiliation, since they are not an "
                               f"institute member.", code="affiliation_required")
        if inv.email and (len(inv.email) > 254 or not EMAIL.match(inv.email)):
            raise InvalidInput(f"{inv.name}'s email address is not valid.",
                               code="invalid_email")
        if len(_text(inv.affiliation)) > 200:
            raise InvalidInput("Keep each affiliation under 200 characters.",
                               code="affiliation_too_long")
        if not Decimal("0") < inv.share_percent <= HUNDRED:
            raise InvalidInput(f"{inv.name}'s share must be above 0 and at most 100.",
                               code="invalid_share")
        if inv.user_id is not None:
            if inv.user_id in seen:
                raise InvalidInput("The same person is listed twice as an inventor.",
                                   code="duplicate_inventor")
            seen.add(inv.user_id)
    total = sum((i.share_percent for i in inventors), Decimal("0"))
    if total != HUNDRED:
        raise InvalidInput(f"Ownership shares must add up to exactly 100; they add up to "
                           f"{total}.", code="shares_not_100")


def check_opinion(*, analysis, novelty, non_obviousness, utility, recommendation) -> None:
    """BR-PMS-046 / PMS-AFR-084: a final opinion evaluates all three tests and recommends once."""
    for label, value in (("legal and patentability analysis", analysis),
                         ("novelty evaluation", novelty),
                         ("non-obviousness evaluation", non_obviousness),
                         ("utility evaluation", utility)):
        if not _text(value):
            raise InvalidInput(f"Complete the {label} before finalizing the opinion.",
                               code="opinion_incomplete")
    if recommendation not in RECOMMENDATIONS:
        raise InvalidInput("Choose exactly one recommendation: File Patent, Do Not File or "
                           "Needs Amendment.", code="recommendation_required")


def check_international_justification(jurisdiction: str, justification) -> str:
    """BR-PMS-056: a filing outside India records why."""
    text = _text(justification)
    if jurisdiction != "IN" and not text:
        raise InvalidInput("An international filing needs a recorded justification.",
                           code="international_justification_required")
    return text[:5000]
