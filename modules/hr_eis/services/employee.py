from modules.hr_eis.models.employee import EmployeeProfile
from modules.hr_eis.services.audit import AuditService
from modules.hr_eis.domain.rules import DomainValidationError

class EmployeeService:
    @staticmethod
    def get_profile_by_user(user_id):
        return EmployeeProfile.objects.filter(user_id=user_id).first()

    @staticmethod
    def update_service_record(employee_id, actor, **fields):
        # Enforces BR-HR-005, BR-HR-006: Only HR Administrator
        profile = EmployeeProfile.objects.filter(employee_id=employee_id).first()
        if not profile:
            raise DomainValidationError(f"Employee {employee_id} not found.")
        for k, v in fields.items():
            if hasattr(profile, k):
                setattr(profile, k, v)
        profile.save()
        AuditService.log("EmployeeProfile", profile.employee_id, actor, "UPDATE_SERVICE_RECORD", details=str(fields))
        return profile
