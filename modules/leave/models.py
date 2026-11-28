from django.db import models
from django.utils.translation import gettext_lazy as _


class LeaveCategory(models.TextChoices):
    CL = "CL", _("Casual Leave")
    RH = "RH", _("Restricted Holiday")
    SCL = "SCL", _("Special Casual Leave")
    EL = "EL", _("Earned Leave")
    COL = "COL", _("Commuted Leave")
    VL = "VL", _("Vacation Leave")


class HalfDayType(models.TextChoices):
    NONE = "NONE", _("Full Day")
    FIRST_HALF = "FIRST_HALF", _("First Half")
    SECOND_HALF = "SECOND_HALF", _("Second Half")


class SubstituteStatus(models.TextChoices):
    NOT_REQUIRED = "NOT_REQUIRED", _("Not Required")
    AWAITING_RESPONSE = "AWAITING_RESPONSE", _("Awaiting Response")
    ACCEPTED = "ACCEPTED", _("Accepted")
    DECLINED = "DECLINED", _("Declined")


class ApplicationStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    AWAITING_SUBSTITUTE = "AWAITING_SUBSTITUTE", _("Awaiting Substitute Response")
    APPLICANT_ACTION_REQUIRED = "APPLICANT_ACTION_REQUIRED", _("Applicant Action Required (Substitute Declined)")
    AWAITING_UNIT_HEAD = "AWAITING_UNIT_HEAD", _("Awaiting Unit Head Review")
    AWAITING_ESTABLISHMENT = "AWAITING_ESTABLISHMENT", _("Awaiting Establishment Routing")
    AWAITING_FINAL_SANCTION = "AWAITING_FINAL_SANCTION", _("Awaiting Final Sanction Decision")
    AWAITING_DIRECTOR_SELF_SANCTION = "AWAITING_DIRECTOR_SELF_SANCTION", _("Awaiting Director Self-Sanction")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")
    WITHDRAWN = "WITHDRAWN", _("Withdrawn")
    CANCELLED = "CANCELLED", _("Cancelled")
    CANCELLATION_PENDING_UNIT_HEAD = "CANCELLATION_PENDING_UNIT_HEAD", _("Cancellation Pending Unit Head Review")
    CANCELLATION_PENDING_ESTABLISHMENT = "CANCELLATION_PENDING_ESTABLISHMENT", _("Cancellation Pending Establishment")
    CANCELLATION_PENDING_FINAL = "CANCELLATION_PENDING_FINAL", _("Cancellation Pending Final Decision")
    EXTENSION_PENDING_SUBSTITUTE = "EXTENSION_PENDING_SUBSTITUTE", _("Extension Pending Substitute Response")
    EXTENSION_PENDING_UNIT_HEAD = "EXTENSION_PENDING_UNIT_HEAD", _("Extension Pending Unit Head Review")
    EXTENSION_PENDING_ESTABLISHMENT = "EXTENSION_PENDING_ESTABLISHMENT", _("Extension Pending Establishment")
    EXTENSION_PENDING_FINAL = "EXTENSION_PENDING_FINAL", _("Extension Pending Final Decision")
    RESUMPTION_PENDING_REVIEW = "RESUMPTION_PENDING_REVIEW", _("Resumption Review Pending")


class ResumptionType(models.TextChoices):
    NORMAL = "NORMAL", _("Normal Return (On Approved Date)")
    EARLY = "EARLY", _("Early Return (Before Approved Date)")
    LATE = "LATE", _("Late Return (After Approved Date)")


class UserRole(models.TextChoices):
    FACULTY = "FACULTY", _("Faculty")
    STAFF = "STAFF", _("Staff")
    UNIT_HEAD = "UNIT_HEAD", _("Unit Head")
    DEPUTY_REGISTRAR = "DEPUTY_REGISTRAR", _("Deputy Registrar (Estt.)")
    DEAN = "DEAN", _("Dean")
    REGISTRAR = "REGISTRAR", _("Registrar")
    DIRECTOR = "DIRECTOR", _("Director")
    LEAVE_ADMIN = "LEAVE_ADMIN", _("Leave Administrator")


class LeavePolicy(models.Model):
    category = models.CharField(max_length=10, choices=LeaveCategory.choices, unique=True)
    annual_entitlement = models.DecimalField(max_digits=5, decimal_places=1)
    allows_half_day = models.BooleanField(default=False)
    is_continuous_counting = models.BooleanField(default=False, help_text="Intervening weekends/holidays count as leave")
    allows_carry_forward = models.BooleanField(default=False)
    max_balance = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    faculty_only = models.BooleanField(default=False)
    staff_only = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Policy - {self.category} ({self.annual_entitlement} days/yr)"


class HolidayCalendar(models.Model):
    class Type(models.TextChoices):
        CLOSED_HOLIDAY = "CLOSED_HOLIDAY", _("Closed Holiday")
        RESTRICTED_HOLIDAY = "RESTRICTED_HOLIDAY", _("Restricted Holiday (RH)")

    date = models.DateField(unique=True)
    name = models.CharField(max_length=150)
    holiday_type = models.CharField(max_length=30, choices=Type.choices, default=Type.CLOSED_HOLIDAY)
    year = models.IntegerField()
    is_published = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.date}: {self.name} [{self.holiday_type}]"


class AcademicCalendarVacation(models.Model):
    academic_year = models.CharField(max_length=20)
    name = models.CharField(max_length=150)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"


class LeaveBalance(models.Model):
    user_id = models.CharField(max_length=100)
    username = models.CharField(max_length=150)
    user_category = models.CharField(max_length=20, choices=[("FACULTY", "Faculty"), ("STAFF", "Staff")], default="STAFF")
    category = models.CharField(max_length=10, choices=LeaveCategory.choices)
    allocated = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    availed = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    pending = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    balance = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    year = models.IntegerField()

    class Meta:
        unique_together = ("user_id", "category", "year")

    def __str__(self):
        return f"{self.username} - {self.category}: {self.balance} remaining ({self.year})"


class LeaveApplication(models.Model):
    applicant_id = models.CharField(max_length=100)
    applicant_name = models.CharField(max_length=150)
    applicant_category = models.CharField(max_length=20, choices=[("FACULTY", "Faculty"), ("STAFF", "Staff")], default="STAFF")
    applicant_role = models.CharField(max_length=50, default="EMPLOYEE")
    department = models.CharField(max_length=100, default="General")

    category = models.CharField(max_length=10, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day_type = models.CharField(max_length=20, choices=HalfDayType.choices, default=HalfDayType.NONE)
    requested_days = models.DecimalField(max_digits=5, decimal_places=1)
    purpose = models.TextField()

    # Station Leave
    is_station_leave = models.BooleanField(default=False)
    station_address = models.TextField(blank=True, null=True)
    out_of_station_start = models.DateField(null=True, blank=True)
    out_of_station_end = models.DateField(null=True, blank=True)
    emergency_contact = models.CharField(max_length=30, blank=True, null=True)

    # Substitute
    substitute_id = models.CharField(max_length=100, blank=True, null=True)
    substitute_name = models.CharField(max_length=150, blank=True, null=True)
    substitute_status = models.CharField(max_length=30, choices=SubstituteStatus.choices, default=SubstituteStatus.NOT_REQUIRED)

    # Status & Routing
    status = models.CharField(max_length=50, choices=ApplicationStatus.choices, default=ApplicationStatus.DRAFT)
    current_authority_role = models.CharField(max_length=50, blank=True, null=True)
    unit_head_recommendation = models.CharField(max_length=30, default="NONE")
    unit_head_remarks = models.TextField(blank=True, null=True)
    final_decision_by = models.CharField(max_length=150, blank=True, null=True)
    final_decision_remarks = models.TextField(blank=True, null=True)

    # Base application reference if this is an extension
    parent_application = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="extensions")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"App #{self.pk} - {self.applicant_name} ({self.category}: {self.start_date} to {self.end_date}) [{self.status}]"


class SubstituteRequest(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="substitute_requests")
    substitute_id = models.CharField(max_length=100)
    substitute_name = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=[("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("DECLINED", "Declined")], default="PENDING")
    remarks = models.TextField(blank=True, null=True)
    replacement_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"SubReq #{self.pk} for App #{self.application_id} -> {self.substitute_name} ({self.status})"


class LeaveActionHistory(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="action_history")
    actor_id = models.CharField(max_length=100)
    actor_name = models.CharField(max_length=150)
    actor_role = models.CharField(max_length=50)
    action = models.CharField(max_length=50)
    from_state = models.CharField(max_length=50)
    to_state = models.CharField(max_length=50)
    remarks = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"History #{self.pk} App #{self.application_id}: {self.action} by {self.actor_name}"


class ResumptionRequest(models.Model):
    application = models.OneToOneField(LeaveApplication, on_delete=models.CASCADE, related_name="resumption")
    applicant_id = models.CharField(max_length=100)
    approved_end_date = models.DateField()
    actual_resumption_date = models.DateField()
    resumption_type = models.CharField(max_length=20, choices=ResumptionType.choices)
    delta_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    status = models.CharField(max_length=30, choices=[("PENDING_REVIEW", "Pending Review"), ("REVIEWED", "Reviewed")], default="PENDING_REVIEW")
    reviewed_by = models.CharField(max_length=150, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Resumption App #{self.application_id} ({self.resumption_type}: Actual {self.actual_resumption_date})"


class OfflineLeaveRecord(models.Model):
    employee_id = models.CharField(max_length=100)
    employee_name = models.CharField(max_length=150)
    category = models.CharField(max_length=10, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=5, decimal_places=1)
    purpose = models.TextField()
    offline_sanction_reference = models.CharField(max_length=100)
    sanctioned_by = models.CharField(max_length=150)
    sanction_date = models.DateField()
    recorded_by = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OfflineLeave #{self.pk} - {self.employee_name} ({self.offline_sanction_reference})"


class SLAConfig(models.Model):
    task_class = models.CharField(max_length=100, unique=True)
    reminder_hours = models.IntegerField(default=48)
    escalation_hours = models.IntegerField(default=96)
    escalation_target_role = models.CharField(max_length=50, default="DEPUTY_REGISTRAR")

    def __str__(self):
        return f"SLAConfig: {self.task_class} (Reminder: {self.reminder_hours}h, Escalation: {self.escalation_hours}h)"
