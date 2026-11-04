"""Pure Python renewal logic and document reuse validation for SPACS.

Enforces:
- BR-SPACS-003 (Reuse of previously uploaded documents)
- BR-SPACS-017 (Renewal uses scheme-specific rules and fresh decision)
- CFR-SPACS-012 / AFR-SPACS-037 through AFR-SPACS-041
"""
from __future__ import annotations

from datetime import date
from typing import Any


def check_renewal_eligibility(
    policy_config: dict[str, Any],
    prior_application: dict[str, Any],
    current_cycle_number: int,
) -> tuple[bool, list[str]]:
    """Checks whether an awarded scholarship can enter a new renewal cycle."""
    deficiencies: list[str] = []

    if not policy_config.get("is_renewable", False):
        deficiencies.append("The selected scholarship scheme is not configured as renewable.")

    max_cycles = policy_config.get("max_renewal_cycles", 0)
    if max_cycles and current_cycle_number > max_cycles:
        deficiencies.append(
            f"Maximum renewal cycle limit ({max_cycles}) reached for this scholarship."
        )

    prior_status = prior_application.get("status")
    if prior_status != "approved":
        deficiencies.append("A renewal requires a previously approved scholarship record.")

    return (len(deficiencies) == 0, deficiencies)


def is_document_reusable(
    document: dict[str, Any],
    required_doc_type: str,
    as_of_date: date,
) -> bool:
    """Evaluates whether a previously uploaded document satisfies reuse criteria (BR-SPACS-003)."""
    if document.get("doc_type") != required_doc_type:
        return False

    validity_date_raw = document.get("declared_validity_date")
    if validity_date_raw:
        if isinstance(validity_date_raw, str):
            try:
                validity_date = date.fromisoformat(validity_date_raw)
            except ValueError:
                return False
        else:
            validity_date = validity_date_raw

        if validity_date < as_of_date:
            return False  # Expired document cannot be reused

    # Drive reference must be valid
    if not document.get("drive_url") or not document.get("drive_file_id"):
        return False

    return True
