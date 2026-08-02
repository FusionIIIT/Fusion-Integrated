"""Placement Policy 2026-27, rule by rule.

Each class names the clause it covers, so a revision to the signed document
can be diffed against this file. The recurring theme: an unenforceable or
unmapped situation denies — a rule nobody configured is not an open door.
"""
from decimal import Decimal as D

from django.test import SimpleTestCase

from modules.placement.domain.offer_policy import (
    CORE,
    CORE_SECTOR,
    CSE_ECE,
    DESIGN,
    IT,
    CategorySpec,
    OfferSpec,
    PolicySpec,
    StudentState,
    can_accept,
    can_apply,
    group_for,
    participation_is_mandatory,
)


def policy(**kw):
    return PolicySpec(season="2026-27", **kw)


def student(discipline="CSE", **kw):
    return StudentState(discipline=discipline, is_registered=True, **kw)


def offer(**kw):
    return OfferSpec(offer_id=1, **kw)


class GroupMappingTests(SimpleTestCase):
    """Rule 2 is written per discipline group, not per discipline."""

    def test_the_signed_groups(self):
        self.assertEqual(group_for("CSE"), CSE_ECE)
        self.assertEqual(group_for("ECE"), CSE_ECE)
        self.assertEqual(group_for("ME"), CORE)
        self.assertEqual(group_for("SM"), CORE)
        self.assertEqual(group_for("MT"), CORE)
        self.assertEqual(group_for("Des."), DESIGN)

    def test_matching_ignores_case_and_spacing(self):
        self.assertEqual(group_for(" cse "), CSE_ECE)

    def test_an_unmapped_discipline_is_none_not_a_guess(self):
        """Inventing a group would apply CSE's switch limits to someone the
        policy says nothing about."""
        self.assertIsNone(group_for("PHD"))
        self.assertIsNone(group_for(None))

    def test_a_season_can_override_the_mapping(self):
        p = policy(group_map={"AI": CSE_ECE})
        self.assertEqual(group_for("AI", p.group_map), CSE_ECE)


class HardBarTests(SimpleTestCase):

    def test_a_debarred_student_may_not_accept(self):
        d = can_accept(policy(), student(is_debarred=True), offer())
        self.assertFalse(d.allowed)
        self.assertEqual(d.rule, "debarred")

    def test_an_unregistered_student_may_not_accept(self):
        """Rule 1: only registered students participate."""
        d = can_accept(policy(), StudentState(discipline="CSE"), offer())
        self.assertFalse(d.allowed)
        self.assertEqual(d.rule, "not_registered")

    def test_debarment_outranks_everything(self):
        d = can_accept(policy(),
                       StudentState(discipline="CSE", is_debarred=True),
                       offer(is_dream_slot=True))
        self.assertEqual(d.rule, "debarred")


class FirstOfferTests(SimpleTestCase):
    """Rule 2.A: the category is chosen once, based on the companies."""

    def test_a_first_offer_is_always_allowed(self):
        d = can_accept(policy(), student(), offer(ctc_lpa=D("8")))
        self.assertTrue(d.allowed)
        self.assertEqual(d.rule, "first_offer")

    def test_it_locks_the_category_from_the_band(self):
        low = can_accept(policy(), student(), offer(ctc_lpa=D("8")))
        high = can_accept(policy(), student(), offer(ctc_lpa=D("14")))
        self.assertEqual(low.facts["category_locked_to"], 1)
        self.assertEqual(high.facts["category_locked_to"], 2)

    def test_the_boundary_belongs_to_category_one(self):
        """Cat 1 is 'upto 10 LPA'; Cat 2 begins above it."""
        at_ten = can_accept(policy(), student(), offer(ctc_lpa=D("10")))
        just_over = can_accept(policy(), student(), offer(ctc_lpa=D("10.5")))
        self.assertEqual(at_ten.facts["category_locked_to"], 1)
        self.assertEqual(just_over.facts["category_locked_to"], 2)


class CseEceSwitchTests(SimpleTestCase):
    """Rule 2.A — Cat 1 switches at 1.5x, Cat 2 at 2x, one switch then out."""

    def test_cat1_needs_one_and_a_half_times(self):
        s = student(category_number=1, accepted_offer_count=1,
                    held_ctc_lpa=D("8"), held_offer_id=7)
        self.assertFalse(can_accept(policy(), s, offer(ctc_lpa=D("11"))).allowed)
        ok = can_accept(policy(), s, offer(ctc_lpa=D("12")))
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.supersedes_offer_id, 7)

    def test_cat2_needs_double(self):
        s = student(category_number=2, accepted_offer_count=1,
                    held_ctc_lpa=D("12"), held_offer_id=7)
        self.assertFalse(can_accept(policy(), s, offer(ctc_lpa=D("20"))).allowed)
        self.assertTrue(can_accept(policy(), s, offer(ctc_lpa=D("24"))).allowed)

    def test_the_refusal_states_both_numbers(self):
        s = student(category_number=1, accepted_offer_count=1,
                    held_ctc_lpa=D("8"))
        d = can_accept(policy(), s, offer(ctc_lpa=D("10")))
        self.assertEqual(d.rule, "below_switch_multiple")
        self.assertIn("12", d.message)          # the required figure
        self.assertIn("10", d.message)          # what was offered

    def test_one_switch_and_you_are_out(self):
        s = student(category_number=1, accepted_offer_count=2, switches_used=1,
                    held_ctc_lpa=D("12"))
        d = can_accept(policy(), s, offer(ctc_lpa=D("30")))
        self.assertFalse(d.allowed)
        self.assertEqual(d.rule, "switch_allowance_used")

    def test_moving_into_a_higher_category_is_allowed_but_final(self):
        """Rule 3: securing a job in a higher category ends the season."""
        s = student(category_number=1, accepted_offer_count=1,
                    held_ctc_lpa=D("8"), held_offer_id=7)
        d = can_accept(policy(), s, offer(ctc_lpa=D("14")))
        self.assertTrue(d.allowed)
        self.assertEqual(d.rule, "higher_category")
        self.assertIn("rule 3", d.message)

    def test_a_higher_category_offer_still_has_to_clear_the_multiple(self):
        s = student(category_number=1, accepted_offer_count=1,
                    held_ctc_lpa=D("9"))
        d = can_accept(policy(), s, offer(ctc_lpa=D("11")))
        self.assertFalse(d.allowed)
        self.assertEqual(d.rule, "below_switch_multiple")


class CoreSwitchTests(SimpleTestCase):
    """Rule 2.B — 1.5x AND the result must exceed 11.5 LPA."""

    def base(self, held="8"):
        return student(discipline="ME", category_number=1,
                       accepted_offer_count=1, held_ctc_lpa=D(held),
                       held_offer_id=7, held_sector=CORE_SECTOR)

    def test_clearing_the_multiple_is_not_enough_on_its_own(self):
        # 1.5 x 7 = 10.5, which clears the multiple but not the 11.5 floor.
        d = can_accept(policy(), self.base("7"), offer(ctc_lpa=D("10.5")))
        self.assertFalse(d.allowed)
        self.assertEqual(d.rule, "below_switch_floor")
        self.assertIn("11.5", d.message)

    def test_exceeding_the_floor_and_the_multiple_is_allowed(self):
        d = can_accept(policy(), self.base("8"), offer(ctc_lpa=D("13")))
        self.assertTrue(d.allowed)

    def test_exactly_the_floor_is_not_exceeding_it(self):
        d = can_accept(policy(), self.base("7"), offer(ctc_lpa=D("11.5")))
        self.assertFalse(d.allowed)

    def test_a_core_placement_may_never_move_to_it(self):
        """Rule 2.B, 'irrespective of any package'."""
        d = can_accept(policy(), self.base("8"),
                       offer(ctc_lpa=D("99"), sector=IT))
        self.assertFalse(d.allowed)
        self.assertEqual(d.rule, "no_core_to_it")

    def test_core_to_core_is_unaffected(self):
        d = can_accept(policy(), self.base("8"),
                       offer(ctc_lpa=D("13"), sector=CORE_SECTOR))
        self.assertTrue(d.allowed)


class DesignSwitchTests(SimpleTestCase):
    """Rule 2.C — 1.5x repeatedly, out once above 12 LPA."""

    def test_repeat_switches_are_allowed_below_the_ceiling(self):
        s = student(discipline="Des.", category_number=1,
                    accepted_offer_count=3, switches_used=2,
                    held_ctc_lpa=D("6"), held_offer_id=7)
        self.assertTrue(can_accept(policy(), s, offer(ctc_lpa=D("9"))).allowed)

    def test_holding_above_twelve_ends_the_season(self):
        s = student(discipline="Des.", category_number=2,
                    accepted_offer_count=2, held_ctc_lpa=D("12.5"))
        d = can_accept(policy(), s, offer(ctc_lpa=D("30")))
        self.assertFalse(d.allowed)
        self.assertEqual(d.rule, "exited_above_ceiling")

    def test_exactly_twelve_is_not_above_twelve(self):
        s = student(discipline="Des.", category_number=2,
                    accepted_offer_count=1, held_ctc_lpa=D("12"),
                    held_offer_id=7)
        self.assertTrue(can_accept(policy(), s, offer(ctc_lpa=D("18"))).allowed)


class MarqueeTests(SimpleTestCase):
    """Rule 8 — no switching out of a Marquee company, ever."""

    def test_a_marquee_placement_cannot_be_switched(self):
        s = student(category_number=1, accepted_offer_count=1,
                    held_ctc_lpa=D("6"), held_is_marquee=True)
        d = can_accept(policy(), s, offer(ctc_lpa=D("100")))
        self.assertFalse(d.allowed)
        self.assertEqual(d.rule, "marquee_no_switch")

    def test_it_outranks_the_switch_maths(self):
        """Even an offer that comfortably clears the multiple is refused."""
        s = student(category_number=1, accepted_offer_count=1,
                    held_ctc_lpa=D("8"), held_is_marquee=True)
        self.assertEqual(
            can_accept(policy(), s, offer(ctc_lpa=D("50"))).rule,
            "marquee_no_switch")

    def test_a_marquee_student_may_not_even_apply_elsewhere(self):
        s = student(category_number=1, accepted_offer_count=1,
                    held_ctc_lpa=D("8"), held_is_marquee=True)
        self.assertFalse(can_apply(policy(), s, offer(ctc_lpa=D("50"))).allowed)


class UnmappedTests(SimpleTestCase):

    def test_an_unmapped_discipline_denies_a_switch(self):
        s = student(discipline="PHD", category_number=1,
                    accepted_offer_count=1, held_ctc_lpa=D("8"))
        d = can_accept(policy(), s, offer(ctc_lpa=D("30")))
        self.assertFalse(d.allowed)
        self.assertEqual(d.rule, "no_category_for_discipline")

    def test_a_missing_ctc_denies_rather_than_guessing(self):
        s = student(category_number=1, accepted_offer_count=1,
                    held_ctc_lpa=D("8"))
        self.assertEqual(can_accept(policy(), s, offer()).rule,
                         "offer_ctc_unknown")

    def test_a_season_with_no_categories_falls_back_to_the_signed_defaults(self):
        """Not to 'anything goes'."""
        p = PolicySpec(season="2026-27")
        s = student(category_number=1, accepted_offer_count=1,
                    held_ctc_lpa=D("8"))
        self.assertFalse(can_accept(p, s, offer(ctc_lpa=D("9"))).allowed)


class ApplyTests(SimpleTestCase):

    def test_an_unplaced_registered_student_may_apply(self):
        self.assertTrue(can_apply(policy(), student()).allowed)

    def test_an_unregistered_student_may_not(self):
        self.assertFalse(
            can_apply(policy(), StudentState(discipline="CSE")).allowed)

    def test_a_dream_slot_is_open_to_a_placed_student(self):
        """Rule 7."""
        s = student(category_number=1, accepted_offer_count=1,
                    switches_used=1, held_ctc_lpa=D("12"))
        d = can_apply(policy(), s, offer(is_dream_slot=True))
        self.assertTrue(d.allowed)
        self.assertEqual(d.rule, "dream_slot")

    def test_a_spent_allowance_closes_ordinary_companies(self):
        s = student(category_number=1, accepted_offer_count=2,
                    switches_used=1, held_ctc_lpa=D("12"))
        self.assertFalse(can_apply(policy(), s, offer(ctc_lpa=D("40"))).allowed)

    def test_a_placed_student_is_told_what_it_would_take(self):
        s = student(category_number=1, accepted_offer_count=1,
                    held_ctc_lpa=D("8"))
        d = can_apply(policy(), s, offer(ctc_lpa=D("20")))
        self.assertTrue(d.allowed)
        self.assertIn("12", d.message)          # 1.5 x 8

    def test_rule_10_needs_the_written_undertaking(self):
        s = student(discipline="ME", category_number=1,
                    accepted_offer_count=1, held_ctc_lpa=D("9"),
                    held_sector=IT)
        without = can_apply(policy(), s, offer(sector=CORE_SECTOR))
        self.assertFalse(without.allowed)
        self.assertEqual(without.rule, "core_undertaking_required")

        with_it = can_apply(policy(), s,
                            offer(sector=CORE_SECTOR, has_core_undertaking=True))
        self.assertTrue(with_it.allowed)
        self.assertEqual(with_it.rule, "core_exception")

    def test_rule_10_does_not_apply_to_cse(self):
        """It is written for 'any Non CSE students'."""
        s = student(discipline="CSE", category_number=1,
                    accepted_offer_count=1, switches_used=1,
                    held_ctc_lpa=D("12"), held_sector=IT)
        d = can_apply(policy(), s,
                      offer(sector=CORE_SECTOR, has_core_undertaking=True))
        self.assertFalse(d.allowed)


class MandatoryParticipationTests(SimpleTestCase):
    """Rule 6 — mandatory from September for eligible unplaced students."""

    import datetime
    SEPT = datetime.date(2026, 9, 1)
    AUG = datetime.date(2026, 8, 20)

    def test_not_mandatory_before_the_date(self):
        p = policy(mandatory_from=self.SEPT)
        self.assertFalse(participation_is_mandatory(p, student(), self.AUG))

    def test_mandatory_from_the_date_for_the_unplaced(self):
        p = policy(mandatory_from=self.SEPT)
        self.assertTrue(participation_is_mandatory(p, student(), self.SEPT))

    def test_a_placed_student_is_not_compelled(self):
        p = policy(mandatory_from=self.SEPT)
        s = student(accepted_offer_count=1, held_ctc_lpa=D("8"))
        self.assertFalse(participation_is_mandatory(p, s, self.SEPT))

    def test_a_debarred_student_is_not_compelled(self):
        p = policy(mandatory_from=self.SEPT)
        self.assertFalse(participation_is_mandatory(
            p, student(is_debarred=True), self.SEPT))

    def test_no_date_configured_means_never_mandatory(self):
        self.assertFalse(participation_is_mandatory(policy(), student(),
                                                    self.SEPT))


class DecisionShapeTests(SimpleTestCase):

    def test_every_decision_is_persistable_and_carries_its_facts(self):
        s = student(category_number=1, accepted_offer_count=1,
                    held_ctc_lpa=D("8"))
        d = can_accept(policy(), s, offer(ctc_lpa=D("9")))
        body = d.as_json()
        self.assertIn("rule", body)
        self.assertIn("facts", body)
        self.assertEqual(body["facts"]["held_ctc_lpa"], "8")
        self.assertEqual(body["facts"]["offer_ctc_lpa"], "9")
        self.assertEqual(body["facts"]["required_ctc_lpa"], "12")

    def test_a_custom_category_table_is_honoured(self):
        """The bands are data. A revised policy is a data change."""
        p = policy(categories=(
            CategorySpec(CSE_ECE, 1, None, D("20"), D("3"), max_switches=2),))
        s = student(category_number=1, accepted_offer_count=1,
                    held_ctc_lpa=D("10"))
        self.assertFalse(can_accept(p, s, offer(ctc_lpa=D("25"))).allowed)
        self.assertTrue(can_accept(p, s, offer(ctc_lpa=D("30"))).allowed)
