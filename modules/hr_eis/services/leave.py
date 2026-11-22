import datetime
from django.db import transaction
from modules.hr_eis.models.leave import LeaveBalance, LeaveRequest
from modules.hr_eis.contracts import LeaveStatus, AuthorityRoles
from modules.hr_eis.domain.rules import validate_leave_request, DomainValidationError
from modules.hr_eis.domain.state_machine import LeaveStateMachine
from modules.hr_eis.services.audit import AuditService

class LeaveService:
    @classmethod
    @transaction.atomic
    def apply_leave(cls, employee, leave_type, start_date, end_date, days_requested, reason):
        # BR-HR-007, BR-HR-008
        current_year = start_date.year if hasattr(start_date, 'year') else 2026
        balance_obj, _ = LeaveBalance.objects.get_or_create(
            employee=employee, leave_type=leave_type, year=current_year,
            defaults={"entitled_days": 15.0, "used_days": 0.0}
        )
        years_of_service = 1
        if hasattr(employee, 'date_of_joining'):
            years_of_service = max(1, (datetime.date.today() - employee.date_of_joining).days // 365)

        validate_leave_request(
            balance_obj.available_days, float(days_requested),
            leave_type, employee.employment_type, years_of_service
        )

        req = LeaveRequest.objects.create(
            employee=employee,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            days_requested=days_requested,
            reason=reason,
            status=LeaveStatus.SUBMITTED,
            current_authority="HOD"
        )
        AuditService.log("LeaveRequest", req.id, employee.employee_id, "SUBMIT_LEAVE", to_state=LeaveStatus.SUBMITTED)
        AuditService.notify(employee.email, "Leave Submitted", f"Your {leave_type} leave request #{req.id} is submitted.")
        return req

    @classmethod
    @transaction.atomic
    def decide_leave(cls, leave_request, action, actor_role, actor_id, remarks=""):
        # BR-HR-009, BR-HR-010, BR-HR-023
        from_state = leave_request.status
        if action == "RECOMMEND":
            new_state = LeaveStateMachine.transition(from_state, LeaveStatus.RECOMMENDED, actor_role)
            leave_request.current_authority = "Director" if leave_request.employee.employment_type == "Faculty" else "Registrar"
        elif action == "APPROVE":
            new_state = LeaveStateMachine.transition(from_state, LeaveStatus.APPROVED, actor_role)
            # BR-HR-010: Automatically deduct balance on approval
            current_year = leave_request.start_date.year
            bal = LeaveBalance.objects.get(employee=leave_request.employee, leave_type=leave_request.leave_type, year=current_year)
            bal.used_days = float(bal.used_days) + float(leave_request.days_requested)
            bal.save()
            leave_request.current_authority = "None"
        elif action == "REJECT":
            new_state = LeaveStateMachine.transition(from_state, LeaveStatus.REJECTED, actor_role)
            leave_request.current_authority = "None"
        else:
            raise DomainValidationError(f"Unknown action: {action}")

        leave_request.status = new_state
        leave_request.remarks = remarks
        leave_request.decided_at = datetime.datetime.now()
        leave_request.save()

        AuditService.log("LeaveRequest", leave_request.id, actor_id, f"LEAVE_{action}", from_state, new_state, remarks)
        AuditService.notify(leave_request.employee.email, f"Leave {new_state}", f"Leave request #{leave_request.id} decided: {new_state}")
        return leave_request
