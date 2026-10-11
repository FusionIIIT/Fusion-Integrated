from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

# -- Leave --------------------------------------------------------------
class Leave(TimeStampedModel, UserScopedModel):
    STATUS = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("cancelled", "Cancelled"),
        ("withdrawn", "Withdrawn"),
        ("resumed", "Resumed"),
        ("extended", "Extended"),
    ]

    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="leaves")
    leave_type = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    approved_by = models.ForeignKey("core.User", null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="approved_leaves")
    cancelled_by = models.ForeignKey("core.User", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="cancelled_leaves")
    resumed_by = models.ForeignKey("core.User", null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="resumed_leaves")
    extended_by = models.ForeignKey("core.User", null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="extended_leaves")

    class Meta:
        db_table = "elm_leave"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "start_date"],
                                    name="leave_unique_per_user"),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_user_idx"),
            models.Index(fields=["start_date", "end_date"], name="leave_dates_idx"),
        ]

    def __str__(self) -> str:
        return f"leave#{self.pk} u{self.user_id} {self.status}"

# BR-EL-001: Supported leave-category eligibility
class LeaveCategory(models.Model):
    name = models.CharField(max_length=20)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_category"
        constraints = [
            models.UniqueConstraint(fields=["name"], name="leave_category_unique_name"),
        ]

# BR-EL-002: Casual Leave entitlement and lapse
class CasualLeave(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="casual_leaves")
    days = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        db_table = "elm_casual_leave"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="casual_leave_unique_per_user"),
        ]

# BR-EL-003: Restricted Holiday entitlement and applicability
class RestrictedHoliday(models.Model):
    date = models.DateField()
    description = models.TextField(blank=True)

    class Meta:
        db_table = "elm_restricted_holiday"
        constraints = [
            models.UniqueConstraint(fields=["date"], name="restricted_holiday_unique_date"),
        ]

# BR-EL-004: Special Casual Leave entitlement and admissibility
class SpecialCasualLeave(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="special_casual_leaves")
    days = models.DecimalField(max_digits=4, decimal_places=2)
    purpose = models.TextField(blank=True)

    class Meta:
        db_table = "elm_special_casual_leave"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="special_casual_leave_unique_per_user"),
        ]

# BR-EL-005: Non-faculty Earned Leave credit and carry-forward
class NonFacultyEarnedLeave(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="non_faculty_earned_leaves")
    days = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        db_table = "elm_non_faculty_earned_leave"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="non_faculty_earned_leave_unique_per_user"),
        ]

# BR-EL-006: Faculty Vacation Leave entitlement and vacation-period applicability
class FacultyVacationLeave(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="faculty_vacation_leaves")
    days = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        db_table = "elm_faculty_vacation_leave"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="faculty_vacation_leave_unique_per_user"),
        ]

# BR-EL-007: VL-to-EL year-end conversion
class VLToELConversion(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="vl_to_el_conversions")
    days = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        db_table = "elm_vl_to_el_conversion"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="vl_to_el_conversion_unique_per_user"),
        ]

# BR-EL-009: Commuted Leave entitlement and treatment
class CommutedLeave(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="commuted_leaves")
    days = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        db_table = "elm_commuted_leave"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="commuted_leave_unique_per_user"),
        ]

# BR-EL-010: Half-day CL treatment
class HalfDayCL(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="half_day_cls")
    days = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        db_table = "elm_half_day_cl"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="half_day_cl_unique_per_user"),
        ]

# BR-EL-013: Station Leave coupling
class StationLeave(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="station_leaves")
    details = models.TextField(blank=True)

    class Meta:
        db_table = "elm_station_leave"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="station_leave_unique_per_user"),
        ]

# BR-EL-014: Substitute eligibility
class Substitute(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="substitutes")
    is_eligible = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_substitute"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="substitute_unique_per_user"),
        ]

# BR-EL-015: Substitute consent gate and decline recovery
class SubstituteConsent(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="substitute_consent")
    is_accepted = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_substitute_consent"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="substitute_consent_unique_per_user"),
        ]

# BR-EL-016: Unit Head final scope for CL/RH
class UnitHeadScope(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="unit_head_scopes")
    is_final_scope = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_unit_head_scope"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="unit_head_scope_unique_per_user"),
        ]

# BR-EL-017: Unit Head recommendation for higher-sanction leave
class UnitHeadRecommendation(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="unit_head_recommendations")
    is_recommended = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_unit_head_recommendation"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="unit_head_recommendation_unique_per_user"),
        ]

# BR-EL-018: Higher-sanction routing
class HigherSanctionRouting(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="higher_sanction_routings")
    is_routing = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_higher_sanction_routing"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="higher_sanction_routing_unique_per_user"),
        ]

# BR-EL-019: Authority resolution and optional Establishment step
class AuthorityResolution(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="authority_resolutions")
    is_resolution = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_authority_resolution"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="authority_resolution_unique_per_user"),
        ]

# BR-EL-021: Immediate withdrawal of pending request
class PendingRequestWithdrawal(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="pending_request_withdrawals")
    is_withdrawal = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_pending_request_withdrawal"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="pending_request_withdrawal_unique_per_user"),
        ]

# BR-EL-023: Cancellation of approved leave before start
class ApprovedLeaveCancellation(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="approved_leave_cancellations")
    is_cancellation = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_approved_leave_cancellation"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="approved_leave_cancellation_unique_per_user"),
        ]

# BR-EL-025: Extension of ongoing EL/COL/VL
class LeaveExtension(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE,
                             related_name="leave_extensions")
    is_extension = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_leave_extension"
        constraints = [
            models.UniqueConstraint(fields=["user_id"], name="leave_extension_unique_per_user"),
        ]
