from modules.employee_leave_management.models import LeaveRequest, LeaveType, Approval
from directory.models import User # Assuming User model exists in directory/models
from datetime import date, timedelta
from django.core.exceptions import PermissionDenied

class ELMService:
    """
    Service layer for handling Employee Leave Management business logic,
    integrating functional rules from ELM specifications.
    """

    def get_leave_types(self):
        """Retrieves all defined leave types."""
        # Uses the existing model structure to fetch types.
        return LeaveType.objects.all()

    def request_leave(self, user: User, leave_type_id: int, start_date: date, end_date: date, reason: str) -> LeaveRequest:
        """
        Submits a new leave request. Validates basic constraints against the leave type.
        """
        try:
            leave_type = LeaveType.objects.get(pk=leave_type_id)
        except LeaveType.DoesNotExist:
            raise ValueError("Leave type not found.")

        duration = (end_date - start_date).days + 1
        if duration <= 0:
            raise ValueError("End date must be after start date.")
        
        # TODO: Implement complex vacation entitlement/balance check here using leave_type.max_carry_over
        
        new_request = LeaveRequest.objects.create(
            user=user,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            status='PENDING',
            reason=reason
        )
        return new_request

    def process_approval(self, request_id: int, approver: User, is_approved: bool, comment: str = "") -> LeaveRequest:
        """
        Handles the approval/rejection workflow, creating and linking an Approval record.
        """
        try:
            request = LeaveRequest.objects.get(pk=request_id)
            # Rule: Only managers/HR authorized by role management (reused from fusion_auth) can approve.
            # Check user.has_permission('elm:approve_leave') goes here.
            
            # Check if approver has the necessary authority (Simplified for implementation)
            if not request.user.is_staff and not approver.is_staff: # Placeholder check
                 raise PermissionDenied("Approver role insufficient to process leave request.")


            approval = Approval.objects.create(
                request=request,
                approver=approver,
                approved=is_approved,
                comment=comment
            )

            if is_approved:
                request.status = 'APPROVED'
            else:
                request.status = 'REJECTED'
            
            request.save()
            return request

        except LeaveRequest.DoesNotExist:
            raise ValueError("Leave request not found.")

# Instantiate service for use by views/routes
elm_service = ELMService()
