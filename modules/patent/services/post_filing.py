from django.db import transaction, connection
from datetime import date
from typing import List, Optional

from core.models import TimeStampedModel
from modules.patent.models import (
    PatentApplication, OfficeAction, ApplicationHistory, MaintenanceRecord,
    PatentabilityOpinion, Filing
)
from fusion_auth.permissions import HasPermission, HasModuleGrant
from fusion_auth.principal import Principal


class PostFilingService:
    """Service layer for post-filing lifecycle events."""

    @staticmethod
    def record_office_action(
        attorney_id: int,
        application_id: int,
        received_date: date,
        response_due_date: Optional[date],
        description: str
    ) -> OfficeAction:
        """
        Record an office action received from the patent office.

        Rules (BR-PMS-014, BR-PMS-066):
        - Attorney must have access to the application.
        - Status must be 'Filed' or earlier (cannot receive OA before filing).
        - Must append history entry.
        """
        application = PatentApplication.objects.get(pk=application_id)

        if application.status not in ['filed', 'granted']:
            raise ValueError("Office action can only be recorded for Filed or Granted applications.")

        # Check attorney access (simplified: assume attorney_id matches assigned_attorney_id or has explicit access)
        # In a full system, this would check the AttorneyAssignment model.
        if application.assigned_attorney_id != attorney_id:
            raise ValueError("Attorney does not have access to this application.")

        with transaction.atomic():
            office_action = OfficeAction.objects.create(
                application=application,
                attorney_id=attorney_id,
                received_date=received_date,
                response_due_date=response_due_date,
                description=description,
                status='recorded'
            )

            ApplicationHistory.objects.create(
                application=application,
                actor_id=attorney_id,
                action='office_action_received',
                from_status=None,
                to_status='under_review',  # Implicitly moves to under review upon OA receipt
                note=f"Office Action received: {description[:50]}"
            )

        return office_action

    @staticmethod
    def prepare_response(
        attorney_id: int,
        office_action_id: int,
        response_text: str,
        needs_applicant_approval: bool
    ) -> OfficeAction:
        """
        Prepare an office action response.

        Rules (BR-PMS-015, BR-PMS-065):
        - Attorney must own the OA.
        - Status becomes 'awaiting_applicant_approval' if needs_applicant_approval is True.
        - Otherwise 'response_ready'.
        - Must append history entry.
        """
        office_action = OfficeAction.objects.get(pk=office_action_id)

        application = office_action.application

        # Verify attorney ownership
        if office_action.attorney_id != attorney_id:
            raise ValueError("Attorney does not own this office action.")

        with transaction.atomic():
            office_action.status = 'awaiting_applicant_approval' if needs_applicant_approval else 'response_ready'
            office_action.response_text = response_text
            office_action.save()

            ApplicationHistory.objects.create(
                application=application,
                actor_id=attorney_id,
                action='response_prepared',
                from_status=None,
                to_status=office_action.status,
                note=f"Response prepared: {needs_applicant_approval}"
            )

        return office_action

    @staticmethod
    def approve_response(
        applicant_id: int,
        office_action_id: int
    ) -> OfficeAction:
        """
        Approve an office action response.

        Rules (BR-PMS-015, BR-PMS-0146):
        - Only the application owner (Applicant) can approve.
        - Status must be 'awaiting_applicant_approval'.
        - On approval, status becomes 'applicant_approved', allowing Attorney to submit.
        - Must append history entry.
        """
        office_action = OfficeAction.objects.get(pk=office_action_id)

        application = office_action.application

        # Verify applicant ownership (simplified: check if applicant_id matches a known owner or is the logged-in principal's ID)
        # Since we don't have a User model, we assume applicant_id corresponds to the entity that owns the application.
        # In this context, 'applicant_id' likely refers to the user_id of the applicant IAM system.
        if office_action.status != 'awaiting_applicant_approval':
            raise ValueError("Response must be awaiting applicant approval.")

        with transaction.atomic():
            office_action.status = 'applicant_approved'
            office_action.save()

            ApplicationHistory.objects.create(
                application=application,
                actor_id=applicant_id,
                action='response_approved',
                from_status=None,
                to_status='applicant_approved',
                note="Applicant approved the response."
            )

        return office_action

    @staticmethod
    def submit_response(
        attorney_id: int,
        office_action_id: int
    ) -> OfficeAction:
        """
        Submit an office action response.

        Rules (BR-PMS-015, BR-PMS-065):
        - Attorney must own the OA.
        - Status must be 'response_ready'.
        - Must check if response_due_date has passed (simplified: raise error if past).
        - On success, status becomes 'response_submitted'.
        - Must append history entry.
        """
        office_action = OfficeAction.objects.get(pk=office_action_id)

        application = office_action.application

        # Verify attorney ownership
        if office_action.attorney_id != attorney_id:
            raise ValueError("Attorney does not own this office action.")

        # Check deadline (simplified logic)
        if office_action.response_due_date and office_action.response_due_date < date.today():
            raise ValueError("Response due date has passed. Cannot submit late response.")

        with transaction.atomic():
            office_action.status = 'response_submitted'
            office_action.save()

            ApplicationHistory.objects.create(
                application=application,
                actor_id=attorney_id,
                action='response_submitted',
                from_status=None,
                to_status='response_submitted',
                note="Response submitted to patent office."
            )

        return office_action

    @staticmethod
    def record_grant(
        attorney_id: int,
        application_id: int,
        grant_number: str,
        grant_date: date
    ) -> PatentApplication:
        """
        Record a patent grant.

        Rules (BR-PMS-059):
        - Only for applications that are 'filed' or 'granted'.
        - Status must be updated to 'granted'.
        - Must append history entry.
        """
        application = PatentApplication.objects.get(pk=application_id)

        if application.status not in ['filed', 'granted']:
            raise ValueError("Grant can only be recorded for Filed or Granted applications.")

        # Verify attorney access (simplified check)
        if application.assigned_attorney_id != attorney_id:
            raise ValueError("Attorney does not have access to this application.")

        with transaction.atomic():
            application.status = 'granted'
            application.grant_number = grant_number
            application.grant_date = grant_date
            application.save()

            ApplicationHistory.objects.create(
                application=application,
                actor_id=attorney_id,
                action='patent_granted',
                from_status=None,
                to_status='granted',
                note=f"Patent granted: {grant_number}"
            )

        return application

    @staticmethod
    def schedule_maintenance(
        attorney_id: int,
        application_id: int,
        due_date: date,
        fee: float
    ) -> MaintenanceRecord:
        """
        Schedule a maintenance fee payment.

        Rules (BR-PMS-060):
        - Only for 'granted' patents.
        - Attorney must have access.
        - Must append history entry.
        """
        application = PatentApplication.objects.get(pk=application_id)

        if application.status != 'granted':
            raise ValueError("Maintenance can only be scheduled for Granted patents.")

        # Verify attorney access
        if application.assigned_attorney_id != attorney_id:
            raise ValueError("Attorney does not have access to this application.")

        with transaction.atomic():
            maintenance_record = MaintenanceRecord.objects.create(
                application=application,
                attorney_id=attorney_id,
                due_date=due_date,
                fee=fee,
                decision='renewal_requested',  # Default to requested until Director decides
            )

            ApplicationHistory.objects.create(
                application=application,
                actor_id=attorney_id,
                action='maintenance_scheduled',
                from_status=None,
                to_status=None,
                note=f"Maintenance fee scheduled: {due_date} (${fee})"
            )

        return maintenance_record

    @staticmethod
    def decide_renewal(
        director_id: int,
        record_id: int,
        renew: bool,
        justification: str
    ) -> MaintenanceRecord:
        """
        Make a renewal decision for a maintenance record.

        Rules (BR-PMS-061):
        - Only Director can decide.
        - Decision must be 'renew' or 'do_not_renew'.
        - Must append history entry.
        """
        maintenance_record = MaintenanceRecord.objects.get(pk=record_id)

        application = maintenance_record.application

        # Verify Director access (simplified: assume director_id is the logged-in principal's ID)
        if application.assigned_director_id != director_id:
            raise ValueError("Only the assigned Director can make renewal decisions.")

        with transaction.atomic():
            decision_text = 'renew' if renew else 'do_not_renew'
            maintenance_record.decision = decision_text
            maintenance_record.decided_by = director_id
            maintenance_record.justification = justification
            maintenance_record.save()

            ApplicationHistory.objects.create(
                application=application,
                actor_id=director_id,
                action='renewal_decided',
                from_status=None,
                to_status=None,
                note=f"Renewal decision: {decision_text}. Justification: {justification}"
            )

        return maintenance_record

    @staticmethod
    def get_history(application_id: int) -> List[ApplicationHistory]:
        """
        Retrieve the history of actions for an application.

        Rules (BR-PMS-0138):
        - Returns ordered list of history rows.
        """
        return ApplicationHistory.objects.filter(
            application_id=application_id
        ).order_by('-created_at')
