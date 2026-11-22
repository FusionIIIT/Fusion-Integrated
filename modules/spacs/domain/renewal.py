"""Renewal eligibility rules and validations (CFR-SPACS-012, BR-SPACS-017).

Pure Python — no Django, DRF or Celery.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RenewalEligibilityResult:
    can_renew: bool
    reasons: tuple[str, ...]
    prefill_fields: tuple[str, ...]
    refreshed_evidence_required: tuple[str, ...]


def evaluate_renewal_eligibility(
    *,
    is_renewable: bool,
    prior_application_status: str,
    renewal_window_open: bool,
    renewal_rules: dict[str, Any],
    current_facts: dict[str, Any],
    previous_renewal_count: int = 0,
) -> RenewalEligibilityResult:
    """Evaluates whether an existing awarded scholarship can be renewed."""
    reasons = []

    if not is_renewable:
        reasons.append("This scholarship scheme is not designated as renewable.")

    if prior_application_status != "approved":
        reasons.append("Only previously approved/awarded scholarships are eligible for renewal.")

    if not renewal_window_open:
        reasons.append("The renewal application window is currently closed.")

    max_years = renewal_rules.get("max_years", 4)
    if previous_renewal_count >= max_years:
        reasons.append(f"Maximum renewal limit of {max_years} years has been reached.")

    min_cpi = renewal_rules.get("min_cpi")
    if min_cpi is not None:
        cpi = current_facts.get("cpi")
        if cpi is None or float(cpi) < float(min_cpi):
            reasons.append(f"Current CPI does not meet the renewal threshold of {min_cpi}.")

    max_backlogs = renewal_rules.get("max_backlogs", 0)
    actual_backlogs = current_facts.get("active_backlogs", 0)
    if int(actual_backlogs) > int(max_backlogs):
        reasons.append(f"Student has active backlogs ({actual_backlogs}), exceeding renewal allowance ({max_backlogs}).")

    refreshed_evidence = tuple(renewal_rules.get("required_refresh_documents", ["grade_sheet", "income_certificate"]))
    prefill_fields = tuple(renewal_rules.get("reusable_fields", ["bank_account", "ifsc_code", "category", "permanent_address"]))

    return RenewalEligibilityResult(
        can_renew=len(reasons) == 0,
        reasons=tuple(reasons),
        prefill_fields=prefill_fields,
        refreshed_evidence_required=refreshed_evidence,
    )
