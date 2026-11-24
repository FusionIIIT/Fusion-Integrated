# PSM public cross-module surface; all getters are plural by signature (ADR-0013).
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from django.db.models import Count, Q

from modules.psm.domain import state_machine as sm
from modules.psm.models import GoodsReceiptNote, Indent


@dataclass(frozen=True)
class IndentSummaryDTO:
    user_id: int
    open_count: int
    fulfilled_count: int
    rejected_count: int


@dataclass(frozen=True)
class PendingReceiptDTO:
    user_id: int
    unconfirmed_grn_count: int


def get_indent_summaries(user_ids: Sequence[int]) -> dict[int, IndentSummaryDTO]:
    """Return batched indent status counts per requestor user_id."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = (
        Indent.objects.filter(user_id__in=ids)
        .values("user_id")
        .annotate(
            open_count=Count("id", filter=~Q(status__in=sm.INDENT_TERMINAL)),
            fulfilled_count=Count("id", filter=Q(status=sm.FULFILLED)),
            rejected_count=Count("id", filter=Q(status=sm.REJECTED)),
        )
    )
    by_uid = {r["user_id"]: r for r in rows}
    return {
        uid: IndentSummaryDTO(
            user_id=uid,
            open_count=by_uid.get(uid, {}).get("open_count", 0),
            fulfilled_count=by_uid.get(uid, {}).get("fulfilled_count", 0),
            rejected_count=by_uid.get(uid, {}).get("rejected_count", 0),
        )
        for uid in ids
    }


def get_pending_receipt_obligations(user_ids: Sequence[int]) -> dict[int, PendingReceiptDTO]:
    """Return batched counts of unconfirmed accepted GRNs per requestor user_id."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    po_counts = dict(
        GoodsReceiptNote.objects.filter(
            purchase_order__indent__user_id__in=ids,
            status__in=("accepted", "partial"),
        )
        .values_list("purchase_order__indent__user_id")
        .annotate(c=Count("id"))
    )
    issue_counts = dict(
        GoodsReceiptNote.objects.filter(
            internal_issue__indent__user_id__in=ids,
            status__in=("accepted", "partial"),
        )
        .values_list("internal_issue__indent__user_id")
        .annotate(c=Count("id"))
    )
    return {
        uid: PendingReceiptDTO(
            user_id=uid, unconfirmed_grn_count=po_counts.get(uid, 0) + issue_counts.get(uid, 0)
        )
        for uid in ids
    }
