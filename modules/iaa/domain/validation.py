"""What a formal submission needs (BR-101); a Draft may lack any of it."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from modules.iaa.domain.state_machine import TA


@dataclass(frozen=True)
class Submission:
    kind: str
    title: str
    department: str
    request_type: str
    amount: Decimal | None
    description: str
    purpose: str
    trip_start: date | None
    trip_end: date | None
    documents: int


def submission_errors(s: Submission, request_types: tuple[str, ...],
                      required_documents: int) -> list[dict]:
    errors: list[dict] = []

    def need(field: str, ok: bool, message: str) -> None:
        if not ok:
            errors.append({"field": field, "message": message})

    need("department", bool(s.department.strip()), "Enter the department this is charged to.")
    need("amount", s.amount is not None and s.amount > 0, "Enter an amount above zero.")
    if s.kind == TA:
        need("purpose", bool(s.purpose.strip()), "Enter the purpose of the trip.")
        need("trip_start", s.trip_start is not None, "Enter the date the trip started.")
        need("trip_end", s.trip_end is not None, "Enter the date the trip ended.")
        if s.trip_start and s.trip_end:
            need("trip_end", s.trip_end >= s.trip_start, "The trip cannot end before it starts.")
    else:
        need("title", bool(s.title.strip()), "Enter a title for the request.")
        need("description", bool(s.description.strip()), "Describe what the money is for.")
        need("request_type", s.request_type in request_types,
             f"Choose a request type: {', '.join(request_types)}.")
    need("documents", s.documents >= required_documents,
         f"Attach at least {required_documents} supporting document(s).")
    return errors
