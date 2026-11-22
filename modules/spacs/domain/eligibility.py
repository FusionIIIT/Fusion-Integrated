"""Pure Python eligibility evaluation engine (BR-SPACS-001).

Evaluates configured scholarship or award criteria against student facts.
Fail-closed: missing required facts or unsatisfied criteria result in ineligibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CriterionOutcome:
    criterion: str
    passed: bool
    expected: Any
    actual: Any
    reason: str = ""


@dataclass(frozen=True)
class EligibilityResult:
    is_eligible: bool
    failed_reasons: tuple[str, ...] = field(default_factory=tuple)
    outcomes: tuple[CriterionOutcome, ...] = field(default_factory=tuple)


def evaluate_criteria(rule: dict[str, Any], facts: dict[str, Any]) -> EligibilityResult:
    """Evaluates rule against facts in a fail-closed manner."""
    if not rule:
        return EligibilityResult(is_eligible=True)

    outcomes: list[CriterionOutcome] = []
    failed_reasons: list[str] = []

    # 1. Min CPI
    if "min_cpi" in rule:
        req = float(rule["min_cpi"])
        actual_val = facts.get("cpi")
        if actual_val is None:
            failed_reasons.append("Missing CPI record")
            outcomes.append(CriterionOutcome("min_cpi", False, req, None, "CPI not available"))
        else:
            actual = float(actual_val)
            passed = actual >= req
            if not passed:
                failed_reasons.append(f"CPI {actual:.2f} is below minimum {req:.2f}")
            outcomes.append(CriterionOutcome(
                "min_cpi", passed, req, actual,
                "" if passed else "cpi_below_minimum"
            ))

    # 2. Max Parental / Family Income
    if "max_parental_income" in rule:
        req = float(rule["max_parental_income"])
        actual_val = facts.get("parental_income")
        if actual_val is None:
            failed_reasons.append("Missing parental income information")
            outcomes.append(CriterionOutcome("max_parental_income", False, req, None, "Income not declared"))
        else:
            actual = float(actual_val)
            passed = actual <= req
            if not passed:
                failed_reasons.append(f"Parental income Rs. {actual:.0f} exceeds ceiling Rs. {req:.0f}")
            outcomes.append(CriterionOutcome(
                "max_parental_income", passed, req, actual,
                "" if passed else "income_exceeds_ceiling"
            ))

    # 3. Disciplines
    if "disciplines" in rule and rule["disciplines"]:
        allowed = set(rule["disciplines"])
        actual = facts.get("discipline")
        passed = actual in allowed
        if not passed:
            failed_reasons.append(f"Discipline '{actual}' not eligible (eligible: {', '.join(sorted(allowed))})")
        outcomes.append(CriterionOutcome(
            "disciplines", passed, list(allowed), actual,
            "" if passed else "discipline_not_eligible"
        ))

    # 4. Batch Years
    if "batch_years" in rule and rule["batch_years"]:
        allowed = set(rule["batch_years"])
        actual = facts.get("batch_year")
        passed = actual in allowed
        if not passed:
            failed_reasons.append(f"Batch year '{actual}' not eligible (eligible: {', '.join(map(str, sorted(allowed)))})")
        outcomes.append(CriterionOutcome(
            "batch_years", passed, list(allowed), actual,
            "" if passed else "batch_not_eligible"
        ))

    # 5. Categories (GEN, OBC, SC, ST, EWS)
    if "categories" in rule and rule["categories"]:
        allowed = set(rule["categories"])
        actual = facts.get("category")
        passed = actual in allowed
        if not passed:
            failed_reasons.append(f"Category '{actual}' not eligible")
        outcomes.append(CriterionOutcome(
            "categories", passed, list(allowed), actual,
            "" if passed else "category_not_eligible"
        ))

    # 6. Max Active Backlogs
    if "max_active_backlogs" in rule:
        max_b = int(rule["max_active_backlogs"])
        actual_val = facts.get("active_backlogs", 0)
        actual = int(actual_val)
        passed = actual <= max_b
        if not passed:
            failed_reasons.append(f"Active backlogs count ({actual}) exceeds maximum allowed ({max_b})")
        outcomes.append(CriterionOutcome(
            "max_active_backlogs", passed, max_b, actual,
            "" if passed else "backlogs_exceed_limit"
        ))

    # 7. Gender
    if "gender" in rule and rule["gender"] and rule["gender"] != "all":
        req = rule["gender"].lower()
        actual = str(facts.get("gender", "")).lower()
        passed = actual == req
        if not passed:
            failed_reasons.append(f"Gender requirement '{req}' not satisfied")
        outcomes.append(CriterionOutcome(
            "gender", passed, req, actual,
            "" if passed else "gender_mismatch"
        ))

    is_eligible = len(failed_reasons) == 0
    return EligibilityResult(
        is_eligible=is_eligible,
        failed_reasons=tuple(failed_reasons),
        outcomes=tuple(outcomes),
    )
