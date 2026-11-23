"""Prior-art search aids over references people record; no outside source is connected."""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from modules.pms.domain.errors import InvalidInput

# BR-PMS-141 / gap G-3: listed so the screen says plainly what was not searched.
SOURCES = (("patent_databases", "Patent databases"),
           ("publication_databases", "Publication databases"))
NOT_CONNECTED = "not connected"
IPC_CODE = re.compile(r"^[A-H][0-9]{2}[A-Z](?: ?[0-9]{1,4}/[0-9]{2,6})?$")
_WORD = re.compile(r"[a-z0-9][a-z0-9-]{2,}")
STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "in",
    "into", "is", "it", "its", "of", "on", "or", "that", "the", "their", "this", "to", "was",
    "were", "which", "with", "using", "use", "used", "method", "system", "device", "apparatus",
    "means", "wherein", "said", "such",
})


@dataclass(frozen=True)
class ReferenceText:
    reference_id: int
    title: str
    notes: str
    identifier: str


def keywords(text: str) -> list[str]:
    return [w for w in _WORD.findall((text or "").lower()) if w not in STOPWORDS]


def optimise_keywords(query: str, context: str, limit: int = 8) -> tuple[list[str], list[str]]:
    """PMS-AFR-148: the query's significant terms, plus frequent terms from the application."""
    terms = list(dict.fromkeys(keywords(query)))
    counts = Counter(w for w in keywords(context) if w not in terms)
    suggestions = [w for w, _ in counts.most_common(limit)]
    return terms, suggestions


def check_classification(codes: Iterable[str]) -> list[str]:
    """PMS-AFR-149: IPC codes such as G06F or G06F 16/30."""
    out = []
    for code in codes:
        cleaned = (code or "").strip().upper()
        if not IPC_CODE.match(cleaned):
            raise InvalidInput(f"'{code}' is not an IPC classification; write it like G06F or "
                               f"G06F 16/30.", code="invalid_classification")
        out.append(cleaned)
    if len(out) > 20:
        raise InvalidInput("Use at most 20 classification codes.", code="too_many_codes")
    return list(dict.fromkeys(out))


def rank(terms: Iterable[str], references: Iterable[ReferenceText]) -> list[tuple[int, int]]:
    """PMS-AFR-145: (reference id, score), title matches weigh twice, best first."""
    wanted = set(terms)
    scored = []
    for ref in references:
        title, notes = Counter(keywords(ref.title)), Counter(keywords(ref.notes))
        score = sum(2 * title[t] + notes[t] for t in wanted)
        if ref.identifier and ref.identifier.lower() in wanted:
            score += 5
        if score > 0:
            scored.append((ref.reference_id, score))
    return sorted(scored, key=lambda pair: (-pair[1], pair[0]))
