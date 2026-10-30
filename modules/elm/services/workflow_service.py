from django.utils import timezone

from modules.elm.domain import (
    APPROVED,
    REJECTED,
    transition,
)
from modules.elm.models.leave_application import LeaveApplication


class WorkflowService:
    @staticmethod
    def process_decision(
        application: LeaveApplication,
        action: str,
        actor_id: int,
        *,
        applicant_is_director: bool = False,
        establishment_configured: bool = False,
    ) -> LeaveApplication:
        """
        Records a decision and updates the application status based on the state machine.
        """
        new_state = transition(
            application.status,
            action,
            category=application.leave_type.code,
            applicant_is_director=applicant_is_director,
            establishment_configured=establishment_configured,
        )

        if action in ("recommend", "not_recommend"):
            application.unit_head_recommendation = (
                "RECOMMENDED" if action == "recommend" else "NOT_RECOMMENDED"
            )

        application.status = new_state

        if new_state in (APPROVED, REJECTED):
            application.decision_maker_id = actor_id
            application.decision_date = timezone.now()

        application.save()
        return application

    @staticmethod
    def check_sla_and_notify(application: LeaveApplication) -> None:
        """
        Checks if an application has exceeded any SLA thresholds and
        triggers notifications/escalations.
        """
        # Placeholder for SLA logic
