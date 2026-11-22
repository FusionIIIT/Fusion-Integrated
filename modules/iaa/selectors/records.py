"""Reads that serve the record pages: detail with its children, and its trail."""
from __future__ import annotations

from django.db.models import Prefetch, QuerySet

from modules.iaa.models import ApprovalStep, FinancialRecord, TrailEntry
from modules.iaa.selectors import scoping


def with_children(qs: QuerySet[FinancialRecord]) -> QuerySet[FinancialRecord]:
    return qs.select_related("financial_year").prefetch_related(
        "documents", "queries",
        Prefetch("steps", queryset=ApprovalStep.objects.order_by("assigned_at", "id")))


def visible_record(actor, pk: int) -> FinancialRecord | None:
    return with_children(scoping.records_for(actor)).filter(pk=pk).first()


def trail(entity: str, entity_id: int) -> QuerySet[TrailEntry]:
    return TrailEntry.objects.filter(entity=entity, entity_id=entity_id).order_by("created_at",
                                                                                   "id")
