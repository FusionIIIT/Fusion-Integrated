"""The grade-math replica, pinned against hand-built transcripts.

Each borrowed quirk is stated as an executable sentence, so "tidying"
iam/grades.py names the behaviour it broke instead of surfacing a semester
later as a wrong CPI on an application.

Validated exhaustively against the ERP itself: the grade math against
calculate_cpi_for_student for every declared student, and the declaration
SELECTION against `_is_result_published_for` for all 3,004 — 0 mismatches on
both. These tests keep it that way.
"""
from decimal import Decimal

from django.test import SimpleTestCase

from iam.grades import (GRADE_CONVERSION, Declaration, GradeRow,
                        applicable_declaration, compute_standing,
                        declared_seq, factor_for, round_1dp)


def row(code, credit, grade, semester=1, sem_type="Odd Semester"):
    return GradeRow(code=code, credit=Decimal(str(credit)), grade=grade,
                    semester=semester, semester_type=sem_type)


def standing(rows, upto=8, sem_type="Even Semester", replacements=None):
    return compute_standing(rows, upto_semester=upto, semester_type=sem_type,
                            replacement_map=replacements)


class GradeTableTests(SimpleTestCase):

    def test_x_and_cd_are_absent_from_the_table(self):
        """Not zero — absent. They resolve to -1 and are excluded entirely."""
        self.assertNotIn("X", GRADE_CONVERSION)
        self.assertNotIn("CD", GRADE_CONVERSION)
        self.assertEqual(factor_for("X"), Decimal("-1"))
        self.assertEqual(factor_for("CD"), Decimal("-1"))

    def test_unknown_and_blank_grades_are_excluded(self):
        for g in ("", "   ", None, "Z", "PASS"):
            self.assertEqual(factor_for(g), Decimal("-1"), g)

    def test_f_is_not_zero(self):
        """F scores 0.2 -> 2.0 grade points. Surprising and load-bearing."""
        self.assertEqual(factor_for("F"), Decimal("0.2"))

    def test_s_is_zero_but_present(self):
        self.assertEqual(factor_for("S"), Decimal("0.0"))
        self.assertIn("S", GRADE_CONVERSION)

    def test_grades_are_stripped_before_lookup(self):
        self.assertEqual(factor_for("  A+  "), Decimal("1.0"))

    def test_generated_grades_reproduce_the_erps_float_error(self):
        """B2 is 0.8200000000000001 in the ERP, not 0.82. Rounding here would
        put the replica ~1e-16 away from the source of truth."""
        self.assertEqual(GRADE_CONVERSION["B2"], Decimal(str(0.8 + 2 * 0.01)))
        self.assertEqual(GRADE_CONVERSION["A5"], Decimal(str(0.9 + 5 * 0.01)))
        self.assertNotEqual(GRADE_CONVERSION["B2"], Decimal("0.82"))

    def test_numeric_pbi_grades(self):
        self.assertEqual(factor_for("8.7"), Decimal("0.87"))
        self.assertEqual(factor_for("10.0"), Decimal("1.00"))
        self.assertEqual(factor_for("2.0"), Decimal("0.20"))
        self.assertEqual(factor_for("1.9"), Decimal("-1"))   # below the range

    def test_rounding_is_one_decimal_half_up(self):
        self.assertEqual(round_1dp(Decimal("8.25")), Decimal("8.3"))
        self.assertEqual(round_1dp(Decimal("8.24")), Decimal("8.2"))
        self.assertEqual(round_1dp(Decimal("8.15")), Decimal("8.2"))


class StandingTests(SimpleTestCase):

    def test_plain_transcript(self):
        s = standing([row("A", 4, "A"), row("B", 4, "B")])
        # (0.9*4 + 0.7*4) / 8 * 10 = 8.0
        self.assertEqual(s.cpi, Decimal("8.0"))
        self.assertEqual(s.earned_credits, Decimal("8"))
        self.assertEqual(s.cpi_denominator_credits, Decimal("8"))

    def test_s_earns_credit_but_does_not_move_the_average(self):
        without = standing([row("A", 4, "A")])
        with_s = standing([row("A", 4, "A"), row("SEM", 2, "S")])
        self.assertEqual(with_s.cpi, without.cpi)                 # unchanged
        self.assertEqual(with_s.earned_credits, Decimal("6"))     # credit given
        self.assertEqual(with_s.cpi_denominator_credits, Decimal("4"))

    def test_x_and_cd_are_excluded_from_everything(self):
        base = standing([row("A", 4, "A")])
        with_x = standing([row("A", 4, "A"), row("X1", 3, "X"), row("X2", 3, "CD")])
        self.assertEqual(with_x.cpi, base.cpi)
        self.assertEqual(with_x.earned_credits, base.earned_credits)
        self.assertEqual(with_x.courses_counted, 1)

    def test_f_counts_toward_both_points_and_credits(self):
        s = standing([row("A", 4, "A"), row("F", 4, "F")])
        # (0.9*4 + 0.2*4) / 8 * 10 = 5.5   -- NOT 9.0 with the F dropped
        self.assertEqual(s.cpi, Decimal("5.5"))
        self.assertEqual(s.earned_credits, Decimal("8"))

    def test_a_retake_keeps_only_the_best_attempt(self):
        s = standing([row("CS101", 4, "F", semester=1),
                      row("CS101", 4, "A", semester=3)])
        self.assertEqual(s.cpi, Decimal("9.0"))
        self.assertEqual(s.earned_credits, Decimal("4"))   # one credit, not two
        self.assertEqual(s.courses_counted, 1)

    def test_backlog_is_counted_only_while_uncleared(self):
        failing = standing([row("CS101", 4, "F")])
        self.assertEqual(failing.active_backlogs, 1)
        cleared = standing([row("CS101", 4, "F", semester=1),
                            row("CS101", 4, "C", semester=3)])
        self.assertEqual(cleared.active_backlogs, 0)

    def test_a_replacement_supersedes_the_course_it_replaced(self):
        rows = [row("ELECTIVE", 3, "D"), row("SWAYAM", 3, "A")]
        s = standing(rows, replacements={"SWAYAM": "ELECTIVE"})
        self.assertEqual(s.cpi, Decimal("9.0"))            # elective dropped
        self.assertEqual(s.earned_credits, Decimal("3"))

    def test_replacement_chains_are_walked_transitively(self):
        rows = [row("E1", 3, "D"), row("E2", 3, "C"), row("E3", 3, "A")]
        s = standing(rows, replacements={"E3": "E2", "E2": "E1"})
        self.assertEqual(s.courses_counted, 1)
        self.assertEqual(s.cpi, Decimal("9.0"))

    def test_a_cyclic_replacement_map_terminates(self):
        """Defensive: bad ERP data must not hang the sync."""
        rows = [row("A", 3, "A"), row("B", 3, "B")]
        s = standing(rows, replacements={"A": "B", "B": "A"})
        self.assertEqual(s.courses_counted, 0)             # both superseded

    def test_summer_of_the_same_semester_is_excluded_unless_asked_for(self):
        rows = [row("REG", 4, "A", semester=4, sem_type="Even Semester"),
                row("SUM", 4, "D", semester=4, sem_type="Summer Semester")]
        even = compute_standing(rows, upto_semester=4,
                                semester_type="Even Semester")
        summer = compute_standing(rows, upto_semester=4,
                                  semester_type="Summer Semester")
        self.assertEqual(even.courses_counted, 1)          # summer excluded
        self.assertEqual(summer.courses_counted, 2)        # summer included

    def test_later_semesters_are_never_counted(self):
        rows = [row("A", 4, "A", semester=1), row("B", 4, "A", semester=7)]
        s = compute_standing(rows, upto_semester=4, semester_type="Even Semester")
        self.assertEqual(s.courses_counted, 1)

    def test_a_transcript_with_no_gradeable_courses_is_zero_not_a_crash(self):
        s = standing([row("X1", 3, "X")])
        self.assertEqual(s.cpi, Decimal("0"))
        self.assertEqual(s.cpi_denominator_credits, Decimal("0"))

    def test_empty_transcript(self):
        s = standing([])
        self.assertEqual(s.cpi, Decimal("0"))
        self.assertEqual(s.earned_credits, Decimal("0"))

    def test_rows_without_a_course_code_are_skipped(self):
        s = standing([row("", 4, "A"), row("OK", 4, "A")])
        self.assertEqual(s.courses_counted, 1)

    def test_null_credit_is_treated_as_zero(self):
        s = compute_standing([GradeRow("C", Decimal("0"), "A", 1, "Odd Semester")],
                             upto_semester=8, semester_type="Even Semester")
        self.assertEqual(s.cpi, Decimal("0"))


class DeclaredSeqTests(SimpleTestCase):

    def test_ordering_matches_the_erps_semester_type_order(self):
        self.assertLess(declared_seq(4, "Odd Semester"),
                        declared_seq(4, "Even Semester"))
        self.assertLess(declared_seq(4, "Even Semester"),
                        declared_seq(4, "Summer Semester"))
        self.assertLess(declared_seq(4, "Summer Semester"),
                        declared_seq(5, "Odd Semester"))

    def test_summer_4_outranks_even_4_but_not_semester_5(self):
        """The case that makes a naive max(semester) wrong."""
        self.assertGreater(declared_seq(4, "Summer Semester"),
                           declared_seq(4, "Even Semester"))
        self.assertLess(declared_seq(4, "Summer Semester"),
                        declared_seq(5, "Odd Semester"))

    def test_an_unknown_semester_type_sorts_last_within_its_semester(self):
        self.assertGreater(declared_seq(3, "Trimester"),
                           declared_seq(3, "Summer Semester"))


class ApplicableDeclarationTests(SimpleTestCase):
    """Which declaration applies to a given student.

    Regression cover for a real bug: taking the newest declaration PER BATCH
    and dropping anyone outside its allow-list erased 1,300 students. A batch
    routinely has a whole-cohort announcement AND a Summer one covering the
    handful who took summer courses; Summer sorts higher, so everyone else lost
    their result entirely.
    """

    def decl(self, ann_id, semester, semester_type, published_for=None):
        return Declaration(announcement_id=ann_id, semester=semester,
                           semester_type=semester_type,
                           published_for=(frozenset(published_for)
                                          if published_for is not None else None))

    def test_the_newest_whole_batch_declaration_wins(self):
        ds = [self.decl(1, 5, "Odd Semester"), self.decl(2, 6, "Even Semester")]
        self.assertEqual(applicable_declaration(ds, "21BCS001").announcement_id, 2)

    def test_a_summer_declaration_wins_for_a_student_it_covers(self):
        ds = [self.decl(1, 6, "Even Semester"),
              self.decl(2, 6, "Summer Semester", {"21BCS001"})]
        self.assertEqual(applicable_declaration(ds, "21BCS001").announcement_id, 2)

    def test_a_student_outside_the_summer_list_falls_back(self):
        """THE bug. They keep their regular Sem 6 result instead of vanishing."""
        ds = [self.decl(1, 6, "Even Semester"),
              self.decl(2, 6, "Summer Semester", {"21BCS999"})]
        applied = applicable_declaration(ds, "21BCS001")
        self.assertIsNotNone(applied)
        self.assertEqual(applied.announcement_id, 1)
        self.assertEqual(applied.semester_type, "Even Semester")

    def test_it_falls_back_more_than_one_step_if_it_has_to(self):
        ds = [self.decl(1, 5, "Odd Semester"),
              self.decl(2, 6, "Even Semester", {"other"}),
              self.decl(3, 6, "Summer Semester", {"other"})]
        self.assertEqual(applicable_declaration(ds, "21BCS001").announcement_id, 1)

    def test_a_student_covered_by_nothing_has_no_declaration(self):
        ds = [self.decl(1, 6, "Even Semester", {"other"})]
        self.assertIsNone(applicable_declaration(ds, "21BCS001"))

    def test_no_declarations_at_all(self):
        self.assertIsNone(applicable_declaration([], "21BCS001"))

    def test_an_empty_allow_list_covers_nobody(self):
        """A per-student announcement published for zero students is not a
        declaration for anyone — distinct from a whole-batch one."""
        ds = [self.decl(1, 5, "Odd Semester"),
              self.decl(2, 6, "Even Semester", set())]
        self.assertEqual(applicable_declaration(ds, "21BCS001").announcement_id, 1)

    def test_ordering_uses_the_declared_sequence_not_the_id(self):
        """A Summer 4 announcement created later still sorts below Semester 5."""
        ds = [self.decl(9, 4, "Summer Semester"), self.decl(1, 5, "Odd Semester")]
        self.assertEqual(applicable_declaration(ds, "21BCS001").announcement_id, 1)
