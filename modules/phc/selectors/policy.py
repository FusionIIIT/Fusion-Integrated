"""Reads of the effective-dated reimbursement policy (PHC-BR-06)."""
from __future__ import annotations

from datetime import date

from modules.phc.models import ReimbursementPolicy


def active_policy(on: date) -> ReimbursementPolicy | None:
    return (ReimbursementPolicy.objects.filter(effective_from__lte=on)
            .order_by("-effective_from").first())
