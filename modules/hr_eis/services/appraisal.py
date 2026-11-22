import datetime
from django.db import transaction
from modules.hr_eis.models.appraisal import AppraisalCycle, AppraisalRecord
from modules.hr_eis.contracts import AppraisalStatus
from modules.hr_eis.domain.rules import validate_appraisal_window
from modules.hr_eis.domain.state_machine import AppraisalStateMachine
from modules.hr_eis.services.audit import AuditService

class AppraisalService:
    @classmethod
    def submit_appraisal(cls, employee, cycle, self_assessment):
        # BR-HR-012
        validate_appraisal_window(cycle.is_open, datetime.date.today(), cycle.submission_deadline)
        record, _ = AppraisalRecord.objects.get_or_create(employee=employee, cycle=cycle)
        AppraisalStateMachine.transition(record.status, AppraisalStatus.SUBMITTED, "Employee")
        record.self_assessment = self_assessment
        record.status = AppraisalStatus.SUBMITTED
        record.submitted_at = datetime.datetime.now()
        record.save()
        AuditService.log("AppraisalRecord", record.id, employee.employee_id, "SUBMIT_APPRAISAL", to_state=AppraisalStatus.SUBMITTED)
        return record

    @classmethod
    def assign_reviewer(cls, record, reviewer, actor):
        # BR-HR-013: HR Admin assigns reviewer
        record.assigned_reviewer = reviewer
        record.status = AppraisalStatus.UNDER_REVIEW
        record.save()
        AuditService.log("AppraisalRecord", record.id, actor, "ASSIGN_REVIEWER", details=f"Reviewer: {reviewer.employee_id}")
        return record

    @classmethod
    def finalize_appraisal(cls, record, rating, remarks, actor_role, actor_id):
        # BR-HR-014, BR-HR-015
        AppraisalStateMachine.transition(record.status, AppraisalStatus.FINALIZED, actor_role)
        record.overall_rating = rating
        record.director_remarks = remarks
        record.status = AppraisalStatus.FINALIZED
        record.finalized_at = datetime.datetime.now()
        record.is_immutable = True  # Permanently archived and immutable
        record.save()
        AuditService.log("AppraisalRecord", record.id, actor_id, "FINALIZE_APPRAISAL", to_state=AppraisalStatus.FINALIZED)
        return record
