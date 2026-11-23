"""Pure rules, no database: every branch of every rule in domain/."""
from datetime import date
from decimal import Decimal

import pytest

from modules.pms.domain import (
    appeals,
    assignment,
    budget,
    calendar,
    deadlines,
    documents,
    filing,
    licensing,
    office_actions,
    policy,
    post_grant,
    prior_art,
    reports,
    validation,
    withdrawal,
)
from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import InvalidInput, RuleViolation

MON = date(2026, 11, 16)


# -- calendar: BR-PMS-031, BR-PMS-035 ------------------------------------------
# BR-PMS-031
def test_review_due_is_fifteen_business_days_skipping_weekends_br_pms_031():
    assert calendar.review_due(MON, []) == date(2026, 12, 7)


# BR-PMS-031
def test_review_due_skips_holidays_br_pms_031():
    assert calendar.review_due(MON, [date(2026, 11, 17)]) == date(2026, 12, 8)


def test_add_business_days_refuses_negative():
    with pytest.raises(ValueError):
        calendar.add_business_days(MON, -1, [])


def test_add_zero_business_days_is_the_same_day():
    assert calendar.add_business_days(MON, 0, []) == MON


def test_saturday_is_not_a_business_day():
    assert not calendar.is_business_day(date(2026, 11, 21), [])


# BR-PMS-035
def test_revision_due_is_sixty_calendar_days_br_pms_035():
    assert calendar.revision_due(date(2026, 1, 1)) == date(2026, 3, 2)


# BR-PMS-093
def test_appeal_due_uses_the_configured_period_br_pms_093():
    assert calendar.appeal_due(date(2026, 1, 1), 30) == date(2026, 1, 31)


@pytest.mark.parametrize(("today", "deadline", "ok"), [
    (date(2026, 1, 1), date(2026, 1, 1), True),
    (date(2026, 1, 2), date(2026, 1, 1), False),
    (date(2026, 1, 2), None, True),
])
def test_on_or_before(today, deadline, ok):
    assert calendar.on_or_before(today, deadline) is ok


# -- validation ----------------------------------------------------------------
FIELDS = {"title": "T", "abstract": "A", "description": "D", "claims": "C",
          "domain_code": "ai"}


# BR-PMS-017
def test_complete_submission_has_nothing_missing_br_pms_017():
    assert validation.missing_fields(FIELDS, inventors=1, documents=1,
                                     domain_codes=frozenset({"ai"})) == []


# BR-PMS-017
def test_missing_fields_are_named_br_pms_017():
    missing = validation.missing_fields({}, inventors=0, documents=0,
                                        domain_codes=frozenset({"ai"}))
    assert missing == ["title", "abstract", "detailed description", "claims",
                       "technical area", "inventor information",
                       "at least one supporting document"]


def test_an_area_no_longer_offered_counts_as_missing():
    missing = validation.missing_fields(FIELDS, inventors=1, documents=1,
                                        domain_codes=frozenset({"bio"}))
    assert missing == ["a technical area that is currently offered"]


def test_whitespace_only_fields_count_as_missing():
    fields = {**FIELDS, "title": "   "}
    assert "title" in validation.missing_fields(fields, inventors=1, documents=1,
                                                domain_codes=frozenset({"ai"}))


def test_overlong_title_refused():
    with pytest.raises(InvalidInput) as exc:
        validation.check_lengths({"title": "x" * 301})
    assert exc.value.code == "field_too_long"


def test_lengths_within_limits_pass():
    validation.check_lengths({"title": "x" * 300})


# BR-PMS-030
def test_justification_of_49_characters_refused_br_pms_030():
    with pytest.raises(InvalidInput) as exc:
        validation.check_justification("x" * 49)
    assert exc.value.code == "justification_too_short"


# BR-PMS-030
def test_justification_of_50_characters_accepted_br_pms_030():
    assert validation.check_justification("  " + "x" * 50 + "  ") == "x" * 50


# BR-PMS-030
def test_justification_padding_does_not_count_br_pms_030():
    with pytest.raises(InvalidInput):
        validation.check_justification(" " * 60 + "short")


def test_overlong_justification_refused():
    with pytest.raises(InvalidInput) as exc:
        validation.check_justification("x" * 10_001)
    assert exc.value.code == "justification_too_long"


# BR-PMS-036
def test_revision_must_answer_every_feedback_br_pms_036():
    with pytest.raises(InvalidInput) as exc:
        validation.check_revision_responses(("review", "appeal"), {"review": "y" * 60},
                                            changed=True)
    assert exc.value.code == "feedback_unanswered"


# BR-PMS-036
def test_revision_response_must_be_fifty_characters_br_pms_036():
    with pytest.raises(InvalidInput):
        validation.check_revision_responses(("review",), {"review": "too short"},
                                            changed=True)


# BR-PMS-036
def test_revision_must_change_something_br_pms_036():
    with pytest.raises(InvalidInput) as exc:
        validation.check_revision_responses(("review",), {"review": "y" * 60}, changed=False)
    assert exc.value.code == "revision_unchanged"


def test_revision_responses_must_be_a_mapping():
    with pytest.raises(InvalidInput):
        validation.check_revision_responses(("review",), ["y" * 60], changed=True)


# BR-PMS-036
def test_valid_revision_responses_pass_br_pms_036():
    out = validation.check_revision_responses(("review",), {"review": " " + "y" * 60},
                                              changed=True)
    assert out == {"review": "y" * 60}


# BR-PMS-069 PMS-AFR-127
def test_withdrawal_needs_reason_br_pms_069():
    with pytest.raises(InvalidInput):
        validation.check_withdrawal_reason("  ")
    assert validation.check_withdrawal_reason(" changed plans ") == "changed plans"


# BR-PMS-094 PMS-AFR-167
def test_appeal_needs_grounds_and_justification_br_pms_094():
    with pytest.raises(InvalidInput) as g:
        validation.check_appeal_grounds("", "because")
    assert g.value.code == "grounds_required"
    with pytest.raises(InvalidInput) as j:
        validation.check_appeal_grounds("ground", " ")
    assert j.value.code == "justification_required"
    assert validation.check_appeal_grounds(" g ", " j ") == ("g", "j")


def test_decline_needs_a_reason():
    with pytest.raises(InvalidInput):
        validation.check_decline_reason(None)
    assert validation.check_decline_reason("busy") == "busy"


def _inv(name="Asha", share="100", user_id=None, email="", affiliation="IIT"):
    return validation.InventorInput(name=name, share_percent=Decimal(share),
                                    user_id=user_id, email=email, affiliation=affiliation)


# BR-PMS-074
def test_inventors_totalling_100_pass_br_pms_074():
    validation.check_inventors([_inv(share="33.33", user_id=1), _inv(share="33.33"),
                                _inv(share="33.34", user_id=2)])


# BR-PMS-074
def test_shares_not_totalling_100_refused_br_pms_074():
    with pytest.raises(InvalidInput) as exc:
        validation.check_inventors([_inv(share="60", user_id=1), _inv(share="30")])
    assert exc.value.code == "shares_not_100"


# BR-PMS-074
@pytest.mark.parametrize("share", ["0", "-5", "100.01"])
def test_share_out_of_range_refused_br_pms_074(share):
    with pytest.raises(InvalidInput) as exc:
        validation.check_inventors([_inv(share=share)])
    assert exc.value.code == "invalid_share"


# BR-PMS-073
def test_no_inventors_refused_br_pms_073():
    with pytest.raises(InvalidInput) as exc:
        validation.check_inventors([])
    assert exc.value.code == "inventors_required"


def test_too_many_inventors_refused():
    with pytest.raises(InvalidInput):
        validation.check_inventors([_inv(share="2") for _ in range(51)])


# BR-PMS-073
def test_inventor_needs_name_br_pms_073():
    with pytest.raises(InvalidInput) as exc:
        validation.check_inventors([_inv(name=" ")])
    assert exc.value.code == "inventor_name_required"


# BR-PMS-073
def test_outside_inventor_needs_affiliation_br_pms_073():
    with pytest.raises(InvalidInput) as exc:
        validation.check_inventors([_inv(affiliation="")])
    assert exc.value.code == "affiliation_required"


def test_institute_inventor_needs_no_affiliation():
    validation.check_inventors([_inv(user_id=5, affiliation="")])


# BR-PMS-073
def test_bad_inventor_email_refused_br_pms_073():
    with pytest.raises(InvalidInput) as exc:
        validation.check_inventors([_inv(email="not-an-email")])
    assert exc.value.code == "invalid_email"


def test_overlong_affiliation_refused():
    with pytest.raises(InvalidInput):
        validation.check_inventors([_inv(affiliation="x" * 201)])


# BR-PMS-073
def test_same_person_twice_refused_br_pms_073():
    with pytest.raises(InvalidInput) as exc:
        validation.check_inventors([_inv(share="50", user_id=3), _inv(share="50", user_id=3)])
    assert exc.value.code == "duplicate_inventor"


@pytest.mark.parametrize("raw", ["abc", "1.234", "NaN"])
def test_unparseable_share_refused(raw):
    with pytest.raises(InvalidInput):
        validation.parse_share(raw)


def test_share_parses():
    assert validation.parse_share("12.5") == Decimal("12.5")


OPINION = {"analysis": "a", "novelty": "n", "non_obviousness": "o", "utility": "u",
           "recommendation": "file_patent"}


# BR-PMS-046
def test_final_opinion_needs_one_recommendation_br_pms_046():
    validation.check_opinion(**OPINION)
    with pytest.raises(InvalidInput) as exc:
        validation.check_opinion(**{**OPINION, "recommendation": "maybe"})
    assert exc.value.code == "recommendation_required"


# PMS-AFR-084
@pytest.mark.parametrize("field", ["analysis", "novelty", "non_obviousness", "utility"])
def test_final_opinion_needs_each_evaluation_pms_afr_084(field):
    with pytest.raises(InvalidInput) as exc:
        validation.check_opinion(**{**OPINION, field: ""})
    assert exc.value.code == "opinion_incomplete"


# BR-PMS-056
def test_international_filing_needs_justification_br_pms_056():
    with pytest.raises(InvalidInput):
        validation.check_international_justification("EP", "")
    assert validation.check_international_justification("EP", " market ") == "market"
    assert validation.check_international_justification("IN", "") == ""


# -- documents: BR-PMS-014, 015, 082, 084, 086, 087 ----------------------------
# BR-PMS-014
def test_pdf_accepted_br_pms_014():
    documents.check_pdf(b"%PDF-1.7 rest", "Spec.PDF")


@pytest.mark.parametrize(("head", "name"), [(b"%PDF-1.4", "spec.docx"),
                                            (b"PK\x03\x04", "spec.pdf")])
# BR-PMS-014
def test_non_pdf_refused_br_pms_014(head, name):
    with pytest.raises(InvalidInput) as exc:
        documents.check_pdf(head, name)
    assert exc.value.code == "not_pdf"


# BR-PMS-015 PMS-AFR-040
def test_exactly_50_mb_refused_br_pms_015():
    with pytest.raises(InvalidInput) as exc:
        documents.check_size(50 * 1024 * 1024)
    assert exc.value.code == "file_too_large"


# BR-PMS-015
def test_just_under_50_mb_accepted_br_pms_015():
    documents.check_size(50 * 1024 * 1024 - 1)


def test_empty_file_refused():
    with pytest.raises(InvalidInput) as exc:
        documents.check_size(0)
    assert exc.value.code == "empty_file"


# PMS-AFR-043
def test_sensitivity_and_kind_checked_pms_afr_043():
    assert documents.check_sensitivity("restricted") == "restricted"
    assert documents.check_kind("claims") == "claims"
    with pytest.raises(InvalidInput):
        documents.check_sensitivity("secret")
    with pytest.raises(InvalidInput):
        documents.check_kind("photo")


# BR-PMS-082
def test_versions_number_from_one_br_pms_082():
    assert documents.next_version(None) == 1
    assert documents.next_version(3) == 4


@pytest.mark.parametrize(("status", "ok"), [
    (sm.DRAFT, True), (sm.NEEDS_REVISION, True), (sm.REJECTED, True),
    (sm.SUBMITTED, False), (sm.UNDER_REVIEW, False), (sm.APPROVED, False),
])
# BR-PMS-087
def test_applicant_uploads_only_in_editable_states_br_pms_087(status, ok):
    assert documents.may_upload({documents.APPLICANT}, status) is ok


@pytest.mark.parametrize(("status", "ok"), [
    (sm.ATTORNEY_ASSIGNED, True), (sm.FILED, True), (sm.GRANTED, True),
    (sm.APPROVED, False),
])
# BR-PMS-086
def test_attorney_uploads_once_assigned_br_pms_086(status, ok):
    assert documents.may_upload({documents.ATTORNEY}, status) is ok


# BR-PMS-086
def test_pcc_admin_uploads_until_terminal_br_pms_086():
    assert documents.may_upload({documents.PCC_ADMIN}, sm.SUBMITTED)
    assert not documents.may_upload({documents.PCC_ADMIN}, sm.WITHDRAWN)


# BR-PMS-086
def test_directors_and_inventors_never_upload_br_pms_086():
    assert not documents.may_upload({documents.REVIEWING_DIRECTOR, documents.INVENTOR},
                                    sm.DRAFT)


@pytest.mark.parametrize(("relation", "public", "confidential", "restricted"), [
    (documents.APPLICANT, True, True, True),
    (documents.INVENTOR, True, True, True),
    (documents.REVIEWING_DIRECTOR, True, True, True),
    (documents.PAST_DIRECTOR, True, True, False),
    (documents.AREA_DIRECTOR, True, False, False),
    (documents.ATTORNEY, True, True, True),
    (documents.PCC_ADMIN, True, True, True),
])
# BR-PMS-084 BR-PMS-130
def test_readers_by_sensitivity_br_pms_084_br_pms_130(relation, public, confidential,
                                                        restricted):
    assert documents.may_read({relation}, documents.PUBLIC_INTERNAL) is public
    assert documents.may_read({relation}, documents.CONFIDENTIAL) is confidential
    assert documents.may_read({relation}, documents.RESTRICTED) is restricted


# BR-PMS-130
def test_no_relation_reads_nothing_br_pms_130():
    assert not documents.may_read(set(), documents.PUBLIC_INTERNAL)
    assert not documents.may_read({documents.APPLICANT}, "unknown")


# -- assignment: BR-PMS-023..027, 041..045 -------------------------------------
def _c(uid, areas=("ai",), load=0):
    return assignment.Candidate(uid, frozenset(areas), load)


# BR-PMS-025
def test_conflicts_cover_applicant_and_inventors_br_pms_025():
    assert assignment.conflicts(1, 1, [])
    assert assignment.conflicts(2, 1, [2])
    assert not assignment.conflicts(3, 1, [2])


# BR-PMS-023 BR-PMS-024 PMS-AFR-051 PMS-AFR-052
def test_eligible_directors_match_area_exclude_conflicts_least_loaded_first_br_pms_023():
    pool = [_c(10, load=3), _c(11, load=1), _c(12, areas=("bio",)), _c(13), _c(99)]
    got = assignment.eligible_directors(pool, "ai", applicant_user_id=99,
                                        inventor_user_ids=[13])
    assert [c.user_id for c in got] == [11, 10]


# BR-PMS-026
def test_check_director_refuses_an_inventor_br_pms_026():
    with pytest.raises(RuleViolation) as exc:
        assignment.check_director(5, [_c(5)], "ai", 1, [5])
    assert exc.value.code == "director_conflicted"


# BR-PMS-025
def test_check_director_refuses_the_applicant_br_pms_025():
    with pytest.raises(RuleViolation):
        assignment.check_director(1, [_c(1)], "ai", 1, [])


def test_check_director_refuses_someone_off_the_roster():
    with pytest.raises(RuleViolation) as exc:
        assignment.check_director(5, [], "ai", 1, [])
    assert exc.value.code == "director_not_on_roster"


# BR-PMS-023
def test_check_director_refuses_an_area_mismatch_br_pms_023():
    with pytest.raises(RuleViolation) as exc:
        assignment.check_director(5, [_c(5, areas=("bio",))], "ai", 1, [])
    assert exc.value.code == "director_area_mismatch"


def test_check_director_accepts_an_eligible_director():
    assignment.check_director(5, [_c(5)], "ai", 1, [])


# BR-PMS-045 BR-PMS-043 PMS-AFR-076 PMS-AFR-077 PMS-AFR-079
def test_rank_attorneys_puts_a_panel_preference_first_br_pms_045():
    pool = [_c(20, load=0), _c(21, load=5), _c(22, areas=("bio",))]
    got = assignment.rank_attorneys(pool, "ai", 1, [], preferred_user_id=21)
    assert [c.user_id for c in got] == [21, 20]


# BR-PMS-045
def test_rank_attorneys_ignores_a_preference_outside_the_panel_br_pms_045():
    pool = [_c(20, load=2), _c(23, load=1)]
    got = assignment.rank_attorneys(pool, "ai", 1, [], preferred_user_id=77)
    assert [c.user_id for c in got] == [23, 20]


# BR-PMS-041
def test_check_attorney_panel_member_is_not_an_exception_br_pms_041():
    assert assignment.check_attorney(20, [_c(20)], "ai", 1, [], "") is False


# BR-PMS-041
def test_check_attorney_off_panel_needs_an_exception_br_pms_041():
    with pytest.raises(RuleViolation) as exc:
        assignment.check_attorney(30, [_c(20)], "ai", 1, [], " ")
    assert exc.value.code == "attorney_not_eligible"
    assert assignment.check_attorney(30, [_c(20)], "ai", 1, [], "Board resolution 4") is True


# BR-PMS-042
def test_check_attorney_area_mismatch_needs_an_exception_br_pms_042():
    with pytest.raises(RuleViolation):
        assignment.check_attorney(20, [_c(20, areas=("bio",))], "ai", 1, [], "")


# BR-PMS-044
def test_check_attorney_conflict_cannot_be_excepted_br_pms_044():
    with pytest.raises(RuleViolation) as exc:
        assignment.check_attorney(20, [_c(20)], "ai", 1, [20], "exception")
    assert exc.value.code == "attorney_conflicted"


# -- budget: BR-PMS-048..053 ----------------------------------------------------
# BR-PMS-048 BR-PMS-049 BR-PMS-050 PMS-AFR-092 PMS-AFR-093 PMS-AFR-094
def test_budget_components_total_br_pms_048_049_050():
    assert budget.check_components("1000", "2000.50", "0") == (
        Decimal("1000"), Decimal("2000.50"), Decimal("0"), Decimal("3000.50"))


# BR-PMS-048
@pytest.mark.parametrize("bad", ["-1", "abc", "1.001", "Infinity", "99999999999"])
def test_bad_amounts_refused_br_pms_048(bad):
    with pytest.raises(InvalidInput):
        budget.check_components(bad, "0", "0")


def test_total_overflow_refused():
    with pytest.raises(InvalidInput):
        budget.check_components("9999999999.99", "1", "0")


@pytest.mark.parametrize(("status", "ok"), [
    (sm.APPROVED, True), (sm.PENDING_REVIEW, True), (sm.ATTORNEY_ASSIGNED, True),
    (sm.UNDER_REVIEW, False), (sm.FILED, False),
])
# BR-PMS-052 PMS-AFR-096
def test_budget_allowed_statuses_br_pms_052(status, ok):
    assert budget.application_allows_budget(status) is ok


# BR-PMS-051
def test_threshold_classification_br_pms_051():
    assert budget.exceeds_threshold(Decimal("101"), Decimal("100"))
    assert not budget.exceeds_threshold(Decimal("100"), Decimal("100"))


# BR-PMS-051
def test_missing_threshold_refuses_a_decision_br_pms_051():
    with pytest.raises(RuleViolation) as exc:
        budget.exceeds_threshold(Decimal("1"), None)
    assert exc.value.code == "budget_threshold_missing"


# -- filing: BR-PMS-020, 075, 078, 128, 142 ------------------------------------
# BR-PMS-128
def test_filing_with_everything_has_no_blockers_br_pms_128():
    facts = filing.FilingFacts(True, True, (filing.InventorState("A", True, True),))
    assert filing.filing_blockers(facts) == []


# BR-PMS-020 BR-PMS-075 BR-PMS-078 PMS-AFR-046 PMS-AFR-136
def test_filing_blockers_name_each_gap_br_pms_020_br_pms_075_br_pms_078():
    facts = filing.FilingFacts(False, False, (filing.InventorState("Asha", False, False),))
    got = filing.filing_blockers(facts)
    assert len(got) == 4
    assert any("budget" in b for b in got)
    assert any("Asha's inventor agreement" in b for b in got)
    assert any("Asha's consent" in b for b in got)


def test_filing_without_inventors_is_blocked():
    assert "The application lists no inventors." in filing.filing_blockers(
        filing.FilingFacts(True, True, ()))


GOOD_FILING = {"jurisdiction": "IN", "external_filing_id": "202611001234",
               "filing_date": date(2026, 11, 1), "confirmation_reference": "CBR 1",
               "today": date(2026, 11, 2)}


# BR-PMS-142
def test_good_filing_record_passes_br_pms_142():
    filing.check_filing(**GOOD_FILING)


@pytest.mark.parametrize(("field", "value", "code"), [
    ("jurisdiction", "india", "invalid_jurisdiction"),
    ("external_filing_id", "x", "invalid_filing_id"),
    ("confirmation_reference", " ", "confirmation_required"),
    ("filing_date", date(2026, 12, 1), "filing_date_in_future"),
])
# BR-PMS-142
def test_bad_filing_records_refused_br_pms_142(field, value, code):
    with pytest.raises(InvalidInput) as exc:
        filing.check_filing(**{**GOOD_FILING, field: value})
    assert exc.value.code == code


# -- post-grant: BR-PMS-059..061 -----------------------------------------------
# BR-PMS-059 PMS-AFR-107
def test_only_granted_is_tracked_br_pms_059():
    assert post_grant.may_track(sm.GRANTED)
    assert not post_grant.may_track(sm.FILED)


# BR-PMS-060 PMS-AFR-108
def test_schedule_from_grant_date_br_pms_060():
    rules = {"IN": (24, 36)}
    assert post_grant.schedule(date(2024, 1, 31), "IN", rules) == (
        date(2026, 1, 31), date(2027, 1, 31))


# BR-PMS-060
def test_no_rule_means_no_schedule_br_pms_060():
    assert post_grant.schedule(date(2024, 1, 1), "US", {"IN": (12,)}) == ()


def test_add_months_clamps_to_month_end():
    assert post_grant.add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)


def test_next_due_after_a_date():
    rules = {"IN": (12, 24)}
    assert post_grant.next_due(date(2024, 1, 1), "IN", rules,
                               after=date(2025, 1, 1)) == date(2026, 1, 1)
    assert post_grant.next_due(date(2024, 1, 1), "IN", rules,
                               after=date(2026, 1, 1)) is None


# BR-PMS-061
def test_renewal_decision_open_until_due_br_pms_061():
    assert post_grant.decision_open(date(2026, 1, 1), date(2026, 1, 1))
    assert not post_grant.decision_open(date(2026, 1, 1), date(2026, 1, 2))


# -- office actions: BR-PMS-065, 066, 099 --------------------------------------
# BR-PMS-065
def test_latest_extension_is_the_deadline_br_pms_065():
    assert office_actions.current_deadline(date(2026, 1, 1),
                                           [date(2026, 3, 1), date(2026, 2, 1)]) \
        == date(2026, 3, 1)
    assert office_actions.current_deadline(date(2026, 1, 1), []) == date(2026, 1, 1)


# BR-PMS-066 BR-PMS-099 PMS-AFR-124
def test_unknown_deadline_not_tracked_br_pms_066():
    assert not office_actions.tracked(None)
    assert office_actions.tracked(date(2026, 1, 1))


# BR-PMS-065
def test_submission_after_deadline_refused_br_pms_065():
    with pytest.raises(RuleViolation) as exc:
        office_actions.check_submission(date(2026, 1, 2), date(2026, 1, 1), date(2026, 1, 3))
    assert exc.value.code == "response_deadline_missed"


# BR-PMS-065
def test_submission_on_deadline_accepted_br_pms_065():
    office_actions.check_submission(date(2026, 1, 1), date(2026, 1, 1), date(2026, 1, 1))
    office_actions.check_submission(date(2026, 1, 1), None, date(2026, 1, 1))


def test_future_submission_date_refused():
    with pytest.raises(InvalidInput):
        office_actions.check_submission(date(2026, 1, 5), None, date(2026, 1, 1))


# PMS-AFR-122
def test_extension_must_be_later_and_explained_pms_afr_122():
    with pytest.raises(InvalidInput):
        office_actions.check_extension(date(2026, 1, 1), date(2026, 1, 1), "r")
    with pytest.raises(InvalidInput):
        office_actions.check_extension(date(2026, 2, 1), date(2026, 1, 1), " ")
    assert office_actions.check_extension(date(2026, 2, 1), None, " r ") == "r"


# -- withdrawal: BR-PMS-067..070 -----------------------------------------------
# BR-PMS-067
def test_withdrawal_after_filing_refused_br_pms_067():
    with pytest.raises(RuleViolation) as exc:
        withdrawal.check_allowed(sm.FILED, sm.WITHDRAWAL_CANDIDATES)
    assert exc.value.code == "withdrawal_after_filing"


# BR-PMS-068
def test_withdrawal_from_unconfigured_status_refused_br_pms_068():
    with pytest.raises(RuleViolation) as exc:
        withdrawal.check_allowed(sm.SUBMITTED, set())
    assert exc.value.code == "withdrawal_not_eligible"


# BR-PMS-068
def test_withdrawal_from_configured_status_allowed_br_pms_068():
    withdrawal.check_allowed(sm.SUBMITTED, {sm.SUBMITTED})


# BR-PMS-070
def test_consent_required_only_when_configured_br_pms_070():
    withdrawal.check_consent(False, [1, 2], [])
    withdrawal.check_consent(True, [1, 2], [2, 1])
    with pytest.raises(RuleViolation):
        withdrawal.check_consent(True, [1, 2], [1])


# -- appeals: BR-PMS-093, 095; ruling C8 ---------------------------------------
# BR-PMS-093
def test_appeal_window_br_pms_093():
    appeals.check_open(date(2026, 1, 10), date(2026, 1, 10), date(2026, 3, 1))
    with pytest.raises(RuleViolation) as late:
        appeals.check_open(date(2026, 1, 11), date(2026, 1, 10), date(2026, 3, 1))
    assert late.value.code == "appeal_period_over"
    with pytest.raises(RuleViolation):
        appeals.check_open(date(2026, 1, 1), None, None)
    with pytest.raises(RuleViolation) as expired:
        appeals.check_open(date(2026, 3, 2), date(2026, 4, 1), date(2026, 3, 1))
    assert expired.value.code == "revision_period_over"


@pytest.mark.parametrize(("outcome", "modified", "event"), [
    ("uphold", None, "appeal_upheld"),
    ("remand", None, "appeal_remanded"),
    ("modify", "approve", "appeal_modified_approve"),
    ("modify", "needs_revision", "appeal_modified_revise"),
])
# BR-PMS-095 PMS-AFR-171
def test_appeal_outcome_drives_the_application_br_pms_095_pms_afr_171(outcome, modified,
                                                                       event):
    assert appeals.application_event(outcome, modified) == event


# BR-PMS-095
def test_modify_needs_a_new_decision_br_pms_095():
    with pytest.raises(InvalidInput) as exc:
        appeals.application_event("modify", None)
    assert exc.value.code == "modified_decision_required"


# BR-PMS-095
def test_unknown_outcome_refused_br_pms_095():
    with pytest.raises(InvalidInput):
        appeals.application_event("overturn", None)


# -- deadlines: BR-PMS-101..104 -------------------------------------------------
@pytest.mark.parametrize(("days_left", "expected"), [
    (31, None), (30, 30), (16, 30), (15, 15), (6, 15), (5, 5), (0, 5), (-1, None),
])
# BR-PMS-101 BR-PMS-102 BR-PMS-103 PMS-AFR-177 PMS-AFR-178
def test_alert_due_br_pms_101_102_103(days_left, expected):
    due = date(2026, 6, 30)
    today = date.fromordinal(due.toordinal() - days_left)
    assert deadlines.alert_due(due, today, (30, 15, 5)) == expected


# BR-PMS-104
def test_missed_br_pms_104():
    assert deadlines.missed(date(2026, 1, 1), date(2026, 1, 2))
    assert not deadlines.missed(date(2026, 1, 1), date(2026, 1, 1))


# -- prior art: PMS-AFR-145, 148, 149; BR-PMS-141 ------------------------------
# PMS-AFR-148
def test_keyword_optimisation_drops_stopwords_and_suggests_terms_pms_afr_148():
    terms, suggestions = prior_art.optimise_keywords(
        "a method for graphene battery", "graphene anode anode electrolyte battery")
    assert terms == ["graphene", "battery"]
    assert suggestions[0] == "anode"
    assert "graphene" not in suggestions


# PMS-AFR-149
def test_classification_codes_validated_pms_afr_149():
    assert prior_art.check_classification(["g06f 16/30", "G06F 16/30", "H01M"]) == [
        "G06F 16/30", "H01M"]
    with pytest.raises(InvalidInput):
        prior_art.check_classification(["Z99"])
    with pytest.raises(InvalidInput):
        prior_art.check_classification(["H01M"] * 21)


# PMS-AFR-145
def test_rank_orders_by_score_pms_afr_145():
    refs = [prior_art.ReferenceText(1, "graphene sheet", "", ""),
            prior_art.ReferenceText(2, "battery graphene anode", "graphene", ""),
            prior_art.ReferenceText(3, "unrelated", "", ""),
            prior_art.ReferenceText(4, "x", "", "us1234")]
    assert prior_art.rank(["graphene", "us1234"], refs) == [(4, 5), (2, 3), (1, 2)]


# BR-PMS-141
def test_outside_sources_are_not_connected_br_pms_141():
    assert {code for code, _ in prior_art.SOURCES} == {"patent_databases",
                                                       "publication_databases"}
    assert prior_art.NOT_CONNECTED == "not connected"


# -- licensing: BR-PMS-088 -------------------------------------------------------
# BR-PMS-088
def test_unconfigured_route_routes_nowhere_br_pms_088():
    assert licensing.route_target(None) is None
    target = licensing.route_target(policy.LicensingRoute("committee", committee_name="TTC"))
    assert target == licensing.Target("committee", None, "TTC")


# PMS-AFR-158 PMS-AFR-159
def test_licensing_request_checked_pms_afr_158_159():
    assert licensing.check_request("licensing", " s ") == "s"
    with pytest.raises(InvalidInput):
        licensing.check_request("sale", "s")
    with pytest.raises(InvalidInput):
        licensing.check_request("technology_transfer", " ")


# -- reports ---------------------------------------------------------------------
# BR-PMS-003
def test_applicant_gets_personal_reports_only_br_pms_003():
    assert reports.check_type("status", applicant_only=True) == "status"
    with pytest.raises(InvalidInput) as exc:
        reports.check_type("financial", applicant_only=True)
    assert exc.value.code == "report_not_available"
    with pytest.raises(InvalidInput):
        reports.check_type("salary", applicant_only=False)


# PMS-AFR-190
def test_report_columns_customisable_pms_afr_190():
    assert reports.check_columns("status", None) == reports.COLUMNS["status"]
    assert reports.check_columns("status", ["title", "title"]) == ("title",)
    with pytest.raises(InvalidInput):
        reports.check_columns("status", ["salary"])


def test_report_filters_validated():
    out = reports.check_filters({"status": "filed", "domain_code": "ai",
                                 "date_from": "2026-01-01", "date_to": "2026-02-01"})
    assert out["date_from"] == date(2026, 1, 1)
    for bad in ({"colour": "x"}, {"status": "nope"}, {"date_from": "yesterday"},
                {"date_from": "2026-02-01", "date_to": "2026-01-01"}):
        with pytest.raises(InvalidInput):
            reports.check_filters(bad)


# PMS-AFR-188
def test_report_schedule_values_pms_afr_188():
    assert reports.check_schedule("weekly") == "weekly"
    with pytest.raises(InvalidInput):
        reports.check_schedule("hourly")


# -- policy ------------------------------------------------------------------------
GOOD_POLICY = {
    "cost_threshold": "500000.00", "appeal_period_days": 30,
    "alert_offsets_days": [5, 30, 15, 15], "withdrawal_statuses": ["submitted"],
    "withdrawal_consent_required": True, "holidays": ["2026-01-26"],
    "domains": [{"code": "ai", "label": "AI", "ipc_classes": ["G06N"]}],
    "maintenance_rules": {"IN": [24, 36]}, "escalation_chain": [7, 7, 8],
    "pcc_contact_user_id": 7, "auto_routing_enabled": True,
    "licensing_route": {"kind": "committee", "committee_name": "TTC"},
}


def test_policy_round_trips():
    spec = policy.parse(GOOD_POLICY, version=3)
    assert spec.alert_offsets_days == (30, 15, 5)
    assert spec.escalation_chain == (7, 8)
    assert policy.parse(policy.to_payload(spec), version=3) == spec


# BR-PMS-101
def test_defaults_are_the_spec_values_br_pms_101_ruling_b7():
    assert policy.DEFAULTS.appeal_period_days == 30
    assert policy.DEFAULTS.alert_offsets_days == (30, 15, 5)
    assert policy.DEFAULTS.withdrawal_statuses == frozenset()
    assert policy.DEFAULTS.cost_threshold is None


# BR-PMS-104
def test_escalation_recipients_fall_back_to_the_contact_br_pms_104():
    assert policy.PolicySpec(escalation_chain=(1, 2)).escalation_recipients == (1, 2)
    assert policy.PolicySpec(pcc_contact_user_id=9).escalation_recipients == (9,)
    assert policy.PolicySpec().escalation_recipients == ()


def test_domain_lookup():
    spec = policy.parse(GOOD_POLICY, version=1)
    assert spec.domain("ai").label == "AI"
    assert spec.domain("bio") is None
    assert spec.domain_codes == frozenset({"ai"})


@pytest.mark.parametrize("patch", [
    {"cost_threshold": "-1"}, {"cost_threshold": "abc"}, {"cost_threshold": "1.234"},
    {"appeal_period_days": 0}, {"appeal_period_days": "x"}, {"appeal_period_days": True},
    {"alert_offsets_days": []}, {"alert_offsets_days": "30"}, {"alert_offsets_days": [400]},
    {"withdrawal_statuses": ["filed"]}, {"withdrawal_statuses": "submitted"},
    {"holidays": ["26-01-2026"]}, {"holidays": "2026-01-26"},
    {"domains": "ai"}, {"domains": ["ai"]}, {"domains": [{"code": "AI", "label": "x"}]},
    {"domains": [{"code": "ai", "label": ""}]},
    {"domains": [{"code": "ai", "label": "a"}, {"code": "ai", "label": "b"}]},
    {"domains": [{"code": "ai", "label": "a", "ipc_classes": ["G6"]}]},
    {"maintenance_rules": []}, {"maintenance_rules": {"india": [12]}},
    {"maintenance_rules": {"IN": []}}, {"maintenance_rules": {"IN": [24, 12]}},
    {"escalation_chain": 7}, {"escalation_chain": [0]},
    {"pcc_contact_user_id": "x"},
    {"licensing_route": {"kind": "board"}}, {"licensing_route": {"kind": "director"}},
    {"licensing_route": {"kind": "committee", "committee_name": " "}},
])
def test_bad_policy_refused(patch):
    with pytest.raises(InvalidInput) as exc:
        policy.parse({**GOOD_POLICY, **patch}, version=1)
    assert exc.value.code == "invalid_policy"


def test_policy_with_director_route_and_no_threshold():
    spec = policy.parse({"cost_threshold": None, "licensing_route":
                         {"kind": "director", "director_user_id": 4}}, version=1)
    assert spec.cost_threshold is None
    assert spec.licensing_route.director_user_id == 4
    assert policy.to_payload(spec)["cost_threshold"] is None


def test_missing_configuration_lists_every_gap_step_2_8():
    gaps = policy.missing_configuration(policy.DEFAULTS, directors=0, panel=0)
    assert len(gaps) == 8
    full = policy.parse(GOOD_POLICY, version=1)
    assert policy.missing_configuration(full, directors=1, panel=1) == []


# -- acting role: PMS-AFR-220 -----------------------------------------------------
def test_acting_permissions_keep_only_the_acting_roles_pms_codes():
    from modules.pms.domain import roles

    grants = {"faculty": ["pms.application.create"], "pms_director": ["pms.review.approve"]}
    held = {"pms.application.create", "pms.review.approve", "placement_cell.job_posting.view"}
    assert roles.acting_permissions(held, "pms_director", "faculty", grants) == {
        "pms.review.approve", "placement_cell.job_posting.view"}
    assert roles.acting_permissions(held, "Professor", "faculty", grants) == {
        "pms.application.create", "placement_cell.job_posting.view"}
    assert roles.acting_permissions(held, None, "staff", grants) == {
        "placement_cell.job_posting.view"}
    assert roles.acting_role("pms_attorney", "staff") == "pms_attorney"
