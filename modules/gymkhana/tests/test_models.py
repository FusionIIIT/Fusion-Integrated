"""Model structural & constraint tests for the 11 Gymkhana domain entities."""
from django.apps import apps
from django.db import models

from modules.gymkhana.models import (
    Booking,
    Club,
    ClubBudgetRequest,
    ClubEventReport,
    ClubLeadershipHistory,
    ClubMembership,
    Poll,
    PollChoice,
    PollTarget,
    PollVote,
    VenueDayLock,
)

EXPECTED_MODELS = [
    Club,
    ClubLeadershipHistory,
    ClubMembership,
    VenueDayLock,
    Booking,
    Poll,
    PollChoice,
    PollTarget,
    PollVote,
    ClubBudgetRequest,
    ClubEventReport,
]


def test_exactly_11_models_exported():
    assert len(EXPECTED_MODELS) == 11
    # Verify no unexpected models in gymkhana app
    gymkhana_app = apps.get_app_config("gymkhana")
    registered_models = list(gymkhana_app.get_models())
    assert len(registered_models) == 11
    assert set(registered_models) == set(EXPECTED_MODELS)


def test_club_constraints_and_indexes():
    constraint_names = {c.name for c in Club._meta.constraints}
    assert "gymkhana_club_name_uniq" in constraint_names
    assert "gymkhana_club_distinct_coordinators" in constraint_names
    assert "gymkhana_club_category_valid" in constraint_names
    assert "gymkhana_club_status_valid" in constraint_names

    index_names = {i.name for i in Club._meta.indexes}
    assert "gymkhana_club_status_idx" in index_names


def test_club_leadership_history_indexes():
    index_names = {i.name for i in ClubLeadershipHistory._meta.indexes}
    assert "gymkhana_lead_hist_idx" in index_names


def test_membership_constraints_and_indexes():
    # Verify exact fields: description and remarks are NOT present
    fields = {f.name for f in ClubMembership._meta.get_fields() if getattr(f, "concrete", True)}
    assert fields == {"id", "club", "student_id", "status", "created_at", "updated_at"}

    constraint_names = {c.name for c in ClubMembership._meta.constraints}
    assert "gymkhana_membership_club_student_uniq" in constraint_names
    assert "gymkhana_membership_status_valid" in constraint_names

    index_names = {i.name for i in ClubMembership._meta.indexes}
    assert "gymkhana_member_club_stat_idx" in index_names
    assert "gymkhana_member_stu_stat_idx" in index_names


def test_poll_target_discipline_default_and_blank():
    disc_field = PollTarget._meta.get_field("discipline")
    assert disc_field.blank is True
    assert disc_field.default == "all"
    assert disc_field.max_length == 50


def test_poll_vote_choice_protection_and_related_names():
    choice_field = PollVote._meta.get_field("choice")
    assert choice_field.remote_field.on_delete == models.PROTECT
    assert choice_field.remote_field.related_name == "votes"

    poll_field = PollVote._meta.get_field("poll")
    assert poll_field.remote_field.on_delete == models.CASCADE
    assert poll_field.remote_field.related_name == "votes"


def test_all_11_models_exact_fields():
    expected_fields_by_model = {
        Club: {
            "id", "name", "category", "description", "coordinator_id",
            "co_coordinator_id", "faculty_councillor_id", "status",
            "created_at", "updated_at",
        },
        ClubLeadershipHistory: {
            "id", "club", "coordinator_id", "co_coordinator_id",
            "effective_from", "effective_to", "changed_by_user_id",
        },
        ClubMembership: {
            "id", "club", "student_id", "status", "created_at", "updated_at",
        },
        VenueDayLock: {
            "id", "venue", "date",
        },
        Booking: {
            "id", "booking_type", "club", "venue", "date", "start_time",
            "end_time", "name", "description", "poster_url",
            "poster_file_id", "faculty_councillor_id", "created_at",
        },
        Poll: {
            "id", "club", "title", "description", "expires_at", "status",
            "created_by_user_id", "created_at",
        },
        PollChoice: {
            "id", "poll", "text",
        },
        PollTarget: {
            "id", "poll", "batch_year", "discipline",
        },
        PollVote: {
            "id", "poll", "choice", "student_id", "created_at",
        },
        ClubBudgetRequest: {
            "id", "club", "amount", "purpose", "description",
            "supporting_file_url", "supporting_file_id", "status",
            "submitted_by_user_id", "created_at",
        },
        ClubEventReport: {
            "id", "club", "student_incharge_id", "event_name", "event_date",
            "event_time", "description", "report_file_url", "report_file_id",
            "submitted_by_user_id", "created_at",
        },
    }
    for model_cls, expected_fields in expected_fields_by_model.items():
        actual_fields = {
            f.name for f in model_cls._meta.get_fields() if getattr(f, "concrete", True)
        }
        assert actual_fields == expected_fields, (
            f"Field mismatch in {model_cls.__name__}: expected {expected_fields}, got {actual_fields}"
        )



def test_venue_day_lock_constraints_and_indexes():
    constraint_names = {c.name for c in VenueDayLock._meta.constraints}
    assert "gymkhana_venueday_uniq" in constraint_names

    index_names = {i.name for i in VenueDayLock._meta.indexes}
    assert "gymkhana_venueday_idx" in index_names


def test_booking_constraints_and_indexes():
    constraint_names = {c.name for c in Booking._meta.constraints}
    assert "gymkhana_booking_time_valid" in constraint_names
    assert "gymkhana_booking_type_valid" in constraint_names

    index_names = {i.name for i in Booking._meta.indexes}
    assert "gymkhana_booking_venue_slot_idx" in index_names
    assert "gymkhana_booking_club_date_idx" in index_names


def test_poll_and_poll_choice_constraints():
    poll_constraints = {c.name for c in Poll._meta.constraints}
    assert "gymkhana_poll_status_valid" in poll_constraints

    choice_constraints = {c.name for c in PollChoice._meta.constraints}
    assert "gymkhana_poll_choice_text_uniq" in choice_constraints

    target_constraints = {c.name for c in PollTarget._meta.constraints}
    assert "gymkhana_polltarget_uniq" in target_constraints

    vote_constraints = {c.name for c in PollVote._meta.constraints}
    assert "gymkhana_pollvote_uniq" in vote_constraints


def test_budget_request_constraints():
    constraint_names = {c.name for c in ClubBudgetRequest._meta.constraints}
    assert "gymkhana_budget_amount_gte_zero" in constraint_names
    assert "gymkhana_budget_status_open" in constraint_names


def test_event_report_indexes():
    index_names = {i.name for i in ClubEventReport._meta.indexes}
    assert "gymkhana_report_club_date_idx" in index_names


def test_no_cross_module_foreign_keys_in_gymkhana():
    """Verify ADR-0013: All user references are plain integer IDs, not FKs."""
    gymkhana_app = apps.get_app_config("gymkhana")
    for model in gymkhana_app.get_models():
        for field in model._meta.get_fields():
            if (
                getattr(field, "is_relation", False)
                and field.related_model
                and getattr(field, "concrete", False)
            ):
                # Destination model must belong to gymkhana
                assert field.related_model._meta.app_label == "gymkhana", (
                    f"Cross-module FK detected: {model.__name__}.{field.name} -> "
                    f"{field.related_model._meta.app_label}.{field.related_model.__name__}"
                )
