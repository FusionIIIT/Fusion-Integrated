"""Pure Python eligibility evaluator for SPACS.

Enforces:
- BR-SPACS-001 (Eligibility must be satisfied against active policy)
- CFR-SPACS-003 / AFR-SPACS-009 (Machine-checkable criteria evaluation)
- No hardcoded thresholds or policies; all logic is driven by policy schema.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any


def evaluate_machine_eligibility(
    criteria_schema: dict[str, Any],
    student_snapshot: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Evaluates student academic snapshot against policy criteria schema.

    Returns (is_eligible, list_of_deficiencies).
    """
    if not criteria_schema:
        # Scheme has no machine-checkable constraints configured
        return True, []

    deficiencies: list[str] = []

    # 1. CPI Floor Check
    min_cpi = criteria_schema.get("min_cpi")
    if min_cpi is not None:
        student_cpi = student_snapshot.get("cpi")
        if student_cpi is None:
            deficiencies.append("Student CPI is not available in academic record.")
        else:
            try:
                if Decimal(str(student_cpi)) < Decimal(str(min_cpi)):
                    deficiencies.append(
                        f"CPI {student_cpi} is below the minimum required cutoff of {min_cpi}."
                    )
            except Exception:
                deficiencies.append("Unable to parse student CPI for eligibility comparison.")

    # 2. Maximum Annual Family Income Ceiling Check
    max_income = criteria_schema.get("max_annual_income")
    if max_income is not None:
        student_income = student_snapshot.get("declared_annual_income")
        if student_income is None:
            deficiencies.append("Annual family income declaration is missing.")
        else:
            try:
                if Decimal(str(student_income)) > Decimal(str(max_income)):
                    deficiencies.append(
                        f"Declared annual income {student_income} exceeds the policy ceiling of {max_income}."
                    )
            except Exception:
                deficiencies.append("Unable to parse annual income for comparison.")

    # 3. Allowed Programmes Filter
    allowed_programmes = criteria_schema.get("allowed_programmes")
    if allowed_programmes:
        student_prog = student_snapshot.get("programme")
        if not student_prog or student_prog not in allowed_programmes:
            deficiencies.append(
                f"Programme '{student_prog or 'Unknown'}' is not eligible for this scheme."
            )

    # 4. Allowed Disciplines Filter
    allowed_disciplines = criteria_schema.get("allowed_disciplines")
    if allowed_disciplines:
        student_disc = student_snapshot.get("discipline")
        if not student_disc or student_disc not in allowed_disciplines:
            deficiencies.append(
                f"Discipline '{student_disc or 'Unknown'}' is not eligible for this scheme."
            )

    # 5. Allowed Batch Years Filter
    allowed_batches = criteria_schema.get("allowed_batch_years")
    if allowed_batches:
        student_batch = student_snapshot.get("batch_year")
        if not student_batch or int(student_batch) not in [int(b) for b in allowed_batches]:
            deficiencies.append(
                f"Batch year '{student_batch or 'Unknown'}' is not eligible for this scheme."
            )

    # 6. Maximum Allowed Backlogs Check
    max_backlogs = criteria_schema.get("max_active_backlogs")
    if max_backlogs is not None:
        student_backlogs = student_snapshot.get("active_backlogs")
        if student_backlogs is not None:
            try:
                if int(student_backlogs) > int(max_backlogs):
                    deficiencies.append(
                        f"Active backlogs ({student_backlogs}) exceed the maximum allowable ({max_backlogs})."
                    )
            except Exception:
                pass

    return (len(deficiencies) == 0, deficiencies)
