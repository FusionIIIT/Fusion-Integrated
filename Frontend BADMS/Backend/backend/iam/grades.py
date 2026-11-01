"""A faithful replica of the ERP's CPI computation.

Copied from `calculate_cpi_for_student` in the Fusion monolith's
`applications/examination/api/views.py`, because Fusion is not to be modified
and exposes no endpoint for it. Pure functions over plain data, so the
algorithm can be diffed against the original and tested in microseconds.

Every quirk below is load-bearing. The numbers must match the ERP exactly, not
be "more correct":

  * **F scores 0.2 (2.0 points) AND contributes its credit.** Not excluded
    from the average. Surprising, and must not be "fixed".
  * **S contributes credit but not the average** — factor 0.0 passes the `>= 0`
    credit test, and the `!= 0` guard keeps it out of the CPI.
  * **X and CD are absent from the table** — they resolve to -1 and are
    excluded from points, credits and earned credits alike.
  * **One row per course CODE**, best attempt, collapsing retakes.
  * **Replacement chains supersede**, transitively.
  * **Rounded to ONE decimal place**, half-up. Not two.

`test_grades_match_erp` is what fails if the ERP's algorithm changes.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

# Exactly the ERP's `grade_conversion`, including the generated entries.
# Anything NOT in here (X, CD, blanks, typos) resolves to -1 and is excluded.
GRADE_CONVERSION: dict[str, Decimal] = {
    "O": Decimal("1.0"), "A+": Decimal("1.0"), "A": Decimal("0.9"),
    "B+": Decimal("0.8"), "B": Decimal("0.7"), "C+": Decimal("0.6"),
    "C": Decimal("0.5"), "D+": Decimal("0.4"), "D": Decimal("0.3"),
    "F": Decimal("0.2"), "S": Decimal("0.0"),
}
# A1..A10 and B1..B10. The ERP builds these with FLOAT arithmetic and str()s
# the result, which leaks binary error on 8 of the 20 — B2 is
# 0.8200000000000001. Rounding to two places would be tidier and would put this
# replica ~1e-16 off the ERP. Copied verbatim. Do not "clean" it.
GRADE_CONVERSION.update({f"A{i}": Decimal(str(0.9 + i * 0.01))
                         for i in range(1, 11)})
GRADE_CONVERSION.update({f"B{i}": Decimal(str(0.8 + i * 0.01))
                         for i in range(1, 11)})
# Numeric PBI/BTP grades "2.0".."10.0" -> 0.20..1.00
GRADE_CONVERSION.update({f"{x / 10:.1f}": Decimal(f"{x / 100:.2f}")
                         for x in range(20, 101)})

MISSING = Decimal("-1")

SEMESTER_TYPE_ORDER = {"Odd Semester": 0, "Even Semester": 1,
                       "Summer Semester": 2}


def semester_type_order(semester_type: str | None) -> int:
    """The ERP's ordering. Anything unrecognised sorts last, as `default=3`."""
    return SEMESTER_TYPE_ORDER.get(semester_type or "", 3)


def declared_seq(semester: int, semester_type: str | None) -> int:
    """A single sortable key for "how far through the degree is this result".

    Reproduces the ERP's own (semester, semester_type_order) ordering, which is
    what makes "the latest declared semester" answerable with a max().
    """
    return semester * 10 + semester_type_order(semester_type)


def factor_for(grade: str | None) -> Decimal:
    return GRADE_CONVERSION.get((grade or "").strip(), MISSING)


@dataclass(frozen=True)
class Declaration:
    """An announced result, and who it covers."""

    announcement_id: int
    semester: int
    semester_type: str | None
    #: None means the whole batch. A set means only those roll numbers were
    #: selected (the ERP's per_student_selection + PublishedResultStudent).
    published_for: frozenset[str] | None = None

    @property
    def seq(self) -> int:
        return declared_seq(self.semester, self.semester_type)

    def covers(self, roll: str) -> bool:
        return self.published_for is None or roll in self.published_for


def applicable_declaration(declarations, roll: str) -> Declaration | None:
    """The newest declaration that actually covers this student.

    NOT the newest in the batch: a batch routinely has a regular announcement
    for the whole cohort and a Summer one covering only a handful. Summer sorts
    higher, so "latest per batch" erases everyone outside its allow-list —
    students who do have a declared result, just the previous one.

    Mirrors the ERP's `_is_result_published_for`, checked newest-first.
    """
    return max(
        (d for d in declarations if d.covers(roll)),
        key=lambda d: d.seq, default=None,
    )


def round_1dp(value: Decimal) -> Decimal:
    """The ERP's `round_from_last_decimal` — one decimal place, half up."""
    return Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class GradeRow:
    code: str
    credit: Decimal
    grade: str
    semester: int
    semester_type: str | None


@dataclass(frozen=True)
class Standing:
    # Replicated from the ERP — these three must match it exactly.
    cpi: Decimal
    earned_credits: Decimal           # the ERP's `total_unit`
    cpi_denominator_credits: Decimal  # `total_credits` — excludes S
    total_points: Decimal             # the ERP's third return value (already x10)

    # Derived here, not from the ERP, which has no backlog count. Defined as
    # "the course's best attempt is still an F", so a fail cleared by a retake
    # is not an active backlog — the reading the placement office uses.
    active_backlogs: int
    courses_counted: int


def _select_rows(rows: list[GradeRow], upto_semester: int,
                 semester_type: str | None) -> list[GradeRow]:
    """The ERP's two-branch grade selection.

    For a Summer result on an even semester, summer rows of that same semester
    are included. Otherwise they are excluded — a summer result is not part of
    the even-semester result for the same number.
    """
    if upto_semester % 2 == 0 and semester_type == "Summer Semester":
        return [r for r in rows if r.semester <= upto_semester]
    return [r for r in rows
            if r.semester <= upto_semester
            and not (r.semester_type == "Summer Semester"
                     and r.semester == upto_semester)]


def compute_standing(rows: list[GradeRow], *, upto_semester: int,
                     semester_type: str | None,
                     replacement_map: dict[str, str] | None = None) -> Standing:
    """CPI, earned credits and backlogs at a given point in the degree.

    `replacement_map` maps a replacement course code to the code it replaced.
    """
    selected = _select_rows(rows, upto_semester, semester_type)

    # Best-graded attempt per course code. Collapses retakes; keeps genuinely
    # different courses apart.
    best: dict[str, GradeRow] = {}
    for r in selected:
        code = (r.code or "").strip()
        if not code:
            continue
        prev = best.get(code)
        if prev is None or factor_for(r.grade) > factor_for(prev.grade):
            best[code] = r

    # Walk replacement chains: if a swayam course was graded, the elective it
    # replaced drops out, and so does whatever THAT replaced.
    superseded: set[str] = set()
    rmap = replacement_map or {}
    for graded_code in best:
        old = rmap.get(graded_code)
        while old and old not in superseded:
            superseded.add(old)
            old = rmap.get(old)

    total_points = Decimal("0")
    total_credits = Decimal("0")     # CPI denominator; S excluded
    earned = Decimal("0")            # total_unit; S included
    backlogs = 0
    counted = 0

    for code, row in best.items():
        if code in superseded:
            continue
        factor = factor_for(row.grade)
        credit = row.credit if row.credit is not None else Decimal("0")
        if factor < 0:
            continue                 # X, CD, unknown — excluded entirely
        counted += 1
        if factor != 0:              # S is 0.0: credit only, no average
            total_points += factor * credit
            total_credits += credit
        earned += credit
        if (row.grade or "").strip() == "F":
            backlogs += 1

    cpi = (round_1dp(Decimal("10") * (total_points / total_credits))
           if total_credits else Decimal("0"))
    return Standing(cpi=cpi, earned_credits=earned,
                    cpi_denominator_credits=total_credits,
                    total_points=total_points * 10,
                    active_backlogs=backlogs, courses_counted=counted)
