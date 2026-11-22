"""Proposal business services for RSPC."""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError
from modules.rspc.domain.state_machine import DomainTransitionError, ProposalStateMachine
from modules.rspc.models import Proposal, ProposalReview


def create_proposal(
    *,
    user_id: int,
    title: str,
    proposal_type: str,
    department: str,
    funding_agency: str,
    proposed_budget: Decimal,
    overhead_amount: Decimal = Decimal("0.00"),
    submission_deadline: datetime.date | None = None,
    summary: str = "",
) -> Proposal:
    if proposed_budget <= Decimal("0.00"):
        raise BadRequestError("Proposed budget must be strictly positive.")

    return Proposal.objects.create(
        user_id=user_id,
        title=title,
        proposal_type=proposal_type,
        department=department,
        funding_agency=funding_agency,
        proposed_budget=proposed_budget,
        overhead_amount=overhead_amount,
        submission_deadline=submission_deadline,
        status="draft",
        summary=summary,
    )


@transaction.atomic
def submit_proposal(*, proposal: Proposal, actor_user_id: int) -> Proposal:
    if proposal.user_id != actor_user_id:
        raise BadRequestError("Only the Principal Investigator can submit their proposal.")

    try:
        new_status = ProposalStateMachine.transition(
            current_status=proposal.status,
            event="submit",
            actor_role="faculty",
            pi_user_id=proposal.user_id,
            actor_user_id=actor_user_id,
        )
    except DomainTransitionError as e:
        raise ConflictError(str(e)) from e

    proposal.status = new_status
    proposal.save(update_fields=["status", "updated_at"])
    return proposal


@transaction.atomic
def endorse_proposal(*, proposal: Proposal, actor_user_id: int, comments: str = "") -> Proposal:
    try:
        new_status = ProposalStateMachine.transition(
            current_status=proposal.status,
            event="endorse",
            actor_role="hod",
            pi_user_id=proposal.user_id,
            actor_user_id=actor_user_id,
        )
    except DomainTransitionError as e:
        raise ConflictError(str(e)) from e

    proposal.status = new_status
    proposal.save(update_fields=["status", "updated_at"])

    ProposalReview.objects.create(
        proposal=proposal,
        reviewer_user_id=actor_user_id,
        reviewer_role="Head of Department",
        action="endorse",
        comments=comments,
    )
    return proposal


@transaction.atomic
def approve_proposal(*, proposal: Proposal, actor_user_id: int, comments: str = "") -> Proposal:
    try:
        new_status = ProposalStateMachine.transition(
            current_status=proposal.status,
            event="approve",
            actor_role="dean",
            pi_user_id=proposal.user_id,
            actor_user_id=actor_user_id,
        )
    except DomainTransitionError as e:
        raise ConflictError(str(e)) from e

    proposal.status = new_status
    proposal.save(update_fields=["status", "updated_at"])

    ProposalReview.objects.create(
        proposal=proposal,
        reviewer_user_id=actor_user_id,
        reviewer_role="Dean (RSPC)",
        action="approve",
        comments=comments,
    )
    return proposal


@transaction.atomic
def reject_proposal(
    *, proposal: Proposal, actor_user_id: int, actor_role: str, comments: str = ""
) -> Proposal:
    try:
        new_status = ProposalStateMachine.transition(
            current_status=proposal.status,
            event="reject",
            actor_role=actor_role,
            pi_user_id=proposal.user_id,
            actor_user_id=actor_user_id,
        )
    except DomainTransitionError as e:
        raise ConflictError(str(e)) from e

    proposal.status = new_status
    proposal.save(update_fields=["status", "updated_at"])

    ProposalReview.objects.create(
        proposal=proposal,
        reviewer_user_id=actor_user_id,
        reviewer_role=actor_role,
        action="reject",
        comments=comments,
    )
    return proposal
