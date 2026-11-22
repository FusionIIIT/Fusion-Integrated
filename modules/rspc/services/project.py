"""Project business services for RSPC."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError
from modules.rspc.domain.state_machine import DomainTransitionError, ProjectLifecycleStateMachine
from modules.rspc.models import Project, ProjectCoPI


@transaction.atomic
def sanction_and_register_project(
    *,
    user_id: int,
    project_code: str,
    project_type: str,
    title: str,
    department: str,
    funding_agency: str,
    sanction_order_no: str,
    sanction_date: datetime.date,
    start_date: datetime.date,
    end_date: datetime.date,
    sanctioned_amount: Decimal,
    co_pi_user_ids: Sequence[int] = (),
) -> Project:
    if sanctioned_amount <= Decimal("0.00"):
        raise BadRequestError("Sanctioned amount must be strictly positive.")
    if end_date < start_date:
        raise BadRequestError("End date must be greater than or equal to start date.")
    if Project.objects.filter(project_code=project_code).exists():
        raise ConflictError(f"Project with code '{project_code}' already exists.")

    project = Project.objects.create(
        user_id=user_id,
        project_code=project_code,
        project_type=project_type,
        title=title,
        department=department,
        funding_agency=funding_agency,
        sanction_order_no=sanction_order_no,
        sanction_date=sanction_date,
        start_date=start_date,
        end_date=end_date,
        sanctioned_amount=sanctioned_amount,
        status="sanctioned",
    )

    for copi_id in co_pi_user_ids:
        ProjectCoPI.objects.create(project=project, user_id=copi_id)

    return project


@transaction.atomic
def activate_project(*, project: Project, actor_role: str) -> Project:
    try:
        new_status = ProjectLifecycleStateMachine.transition(
            current_status=project.status,
            event="activate",
            actor_role=actor_role,
        )
    except DomainTransitionError as e:
        raise ConflictError(str(e)) from e

    project.status = new_status
    project.save(update_fields=["status", "updated_at"])
    return project
