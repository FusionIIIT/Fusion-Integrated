"""The creator's side: drafts, submission, documents and query responses (UC-101/102/104/401)."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError, DomainError
from modules.iaa.domain import roles
from modules.iaa.domain import state_machine as sm
from modules.iaa.domain.validation import Submission, submission_errors
from modules.iaa.models import ClarificationQuery, FinancialRecord, SupportingDocument
from modules.iaa.selectors import policy as policy_selectors
from modules.iaa.selectors import scoping
from modules.iaa.services import notify, trail
from modules.iaa.services.authz import require
from modules.iaa.services.common import current_policy, domain_errors, lock, now

P_CREATE = "iaa.request.create"
P_RESPOND = "iaa.clarification.update"
EDITABLE_FIELDS = ("department", "request_type", "title", "description", "amount")


class SubmissionIncomplete(DomainError):
    code = "submission_incomplete"
    message = "Some required details are missing. Complete the highlighted fields and submit again."


def _owned(actor):
    return scoping.records_for(actor).filter(user_id=actor.user_id)


def _check_submission(record: FinancialRecord, documents: int) -> None:
    policy = current_policy()
    errors = submission_errors(
        Submission(kind=record.kind, title=record.title, department=record.department,
                   request_type=record.request_type, amount=record.amount,
                   description=record.description, purpose=record.purpose,
                   trip_start=record.trip_start, trip_end=record.trip_end,
                   documents=documents),
        policy.request_types, policy.required_documents.get(record.kind, 0))
    if errors:
        raise SubmissionIncomplete(details=errors)


def _attach_financial_year(record: FinancialRecord) -> None:
    year = policy_selectors.financial_year_on(now().date())
    if year is None:
        raise ConflictError(
            "No financial year covers today, so nothing can be submitted. Ask the IAA System "
            "Admin to add the current financial year.", code="financial_year_missing")
    record.financial_year = year


def _announce_submission(actor, record: FinancialRecord) -> None:
    label = "TA claim" if record.kind == sm.TA else "Request"
    notify.to_role(roles.FINANCE, "submitted",
                   f"{label} #{record.pk} for {record.amount} from {record.department} "
                   f"is waiting for Finance review.", "record", record.pk)
    notify.to_user(actor.user_id, "submitted",
                   f"{label} #{record.pk} was submitted to Finance.", "record", record.pk)


@transaction.atomic
def create_expense(actor, *, department: str = "", request_type: str = "", title: str = "",
                   description: str = "", amount: Decimal | None = None) -> FinancialRecord:
    require(actor, P_CREATE)
    record = FinancialRecord.objects.create(
        kind=sm.EXPENSE, status=sm.DRAFT, user_id=actor.user_id, department=department,
        request_type=request_type, title=title, description=description, amount=amount)
    trail.log("record", record.pk, "create", actor=actor, to=sm.DRAFT)
    return record


@transaction.atomic
def update_draft(actor, pk: int, **changes) -> FinancialRecord:
    require(actor, P_CREATE)
    record = lock(_owned(actor), pk)
    if record.status != sm.DRAFT:
        raise ConflictError(
            "This request has been submitted and can no longer be edited. Answer Finance's "
            "query if one is open.", code="record_locked")
    for field in EDITABLE_FIELDS:
        if field in changes:
            setattr(record, field, changes[field])
    record.save()
    trail.log("record", record.pk, "update_draft", actor=actor, frm=sm.DRAFT, to=sm.DRAFT)
    return record


@transaction.atomic
def add_document(actor, pk: int, *, title: str, link: str) -> SupportingDocument:
    require(actor, P_CREATE, P_RESPOND)
    record = lock(_owned(actor), pk)
    # Before submission anything goes; afterwards only as part of a query response (BR-104).
    if record.status not in (sm.DRAFT, sm.QUERY_RAISED):
        raise ConflictError(
            "Documents can be added to a draft, or while answering a Finance query.",
            code="record_locked")
    doc = SupportingDocument.objects.create(record=record, title=title, link=link,
                                            added_by=actor.user_id)
    trail.log("record", record.pk, "add_document", actor=actor, frm=record.status,
              to=record.status, remarks=title)
    return doc


@transaction.atomic
def submit(actor, pk: int) -> FinancialRecord:
    require(actor, P_CREATE)
    record = lock(_owned(actor), pk)
    with domain_errors():
        t = sm.resolve_record(record.kind, record.status, sm.SUBMIT, roles.OWNER)
    _check_submission(record, record.documents.count())
    _attach_financial_year(record)
    record.status, record.submitted_at = t.to, now()
    record.save()
    trail.log("record", record.pk, "submit", actor=actor, frm=t.frm, to=t.to)
    _announce_submission(actor, record)
    return record


@transaction.atomic
def create_ta(actor, *, department: str, amount: Decimal, purpose: str, trip_start, trip_end,
              documents: list[dict]) -> FinancialRecord:
    require(actor, P_CREATE)
    record = FinancialRecord(kind=sm.TA, status=sm.SUBMITTED, user_id=actor.user_id,
                             department=department, amount=amount, purpose=purpose,
                             trip_start=trip_start, trip_end=trip_end,
                             title=f"TA: {purpose[:180]}")
    _check_submission(record, len(documents))
    _attach_financial_year(record)
    record.submitted_at = now()
    record.save()
    SupportingDocument.objects.bulk_create(
        SupportingDocument(record=record, title=d["title"], link=d["link"],
                           added_by=actor.user_id) for d in documents)
    trail.log("record", record.pk, "submit", actor=actor, to=sm.SUBMITTED)
    _announce_submission(actor, record)
    return record


@transaction.atomic
def respond_query(actor, pk: int, *, response: str) -> FinancialRecord:
    require(actor, P_RESPOND)
    if not response.strip():
        raise DomainError("Write a response to Finance's question.", code="response_required")
    record = lock(_owned(actor), pk)
    with domain_errors():
        t = sm.resolve_record(record.kind, record.status, sm.RESPOND_QUERY, roles.OWNER)
    query = ClarificationQuery.objects.filter(record=record, responded_at__isnull=True).first()
    if query is None:
        raise ConflictError("There is no open query on this item.", code="no_open_query")
    query.response, query.responded_by, query.responded_at = response, actor.user_id, now()
    query.save()
    record.status = t.to
    record.save(update_fields=["status", "updated_at"])
    trail.log("record", record.pk, "respond_query", actor=actor, frm=t.frm, to=t.to,
              remarks=response)
    notify.to_role(roles.FINANCE, "query_responded",
                   f"#{record.pk}: the creator answered your query.", "record", record.pk)
    return record
