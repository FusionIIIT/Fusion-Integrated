# Task: rewrite modules/leave/models.py so it represents the ELM leave workflow (Workflow Spec v1.6, Business Rules v1.4)

Output the COMPLETE file modules/leave/models.py. Keep `from core.db.mixins import TimeStampedModel, UserScopedModel`.
People are plain `user_id` integers (UserScopedModel already provides `user_id`; do NOT redeclare it). No ForeignKey to any user table.
Follow the style of the pattern file (modules/placement/models/students.py): module docstring, comments, Meta with db_table, named constraints/indexes.
Problems in the CURRENT file that you must fix:
- STATUS_CHOICES were copied from another module (shortlisted, interview_scheduled, offer_*). Replace them with the leave states below.
- `UniqueConstraint(category, user_id)` forbids a person ever applying for the same category twice. REMOVE it.
- Remove placement leftovers: cpi_at_apply, semester_at_apply, standing_declared_seq_at_apply, eligibility_snapshot, `actor_recruiter_id`.
- COL is "Commuted Leave" (not "Casual Leave"). `LeaveCategory.code` must use `choices=CODE_CHOICES`; remove the redundant `unique_together` on code (unique=True is enough).
- `LeaveBalance` must not redeclare `user_id`.

## LeaveCategory
code (CharField max 3, unique, choices CODE_CHOICES = CL Casual Leave, RH Restricted Holiday, SCL Special Casual Leave, EL Earned Leave, COL Commuted Leave, VL Vacation Leave),
name (max 50), description (TextField blank), is_carry_forwardable (Boolean default False). db_table "leave_category".

## LeaveApplication(TimeStampedModel, UserScopedModel)  db_table "leave_application"
STATUS_CHOICES (value, label) - use EXACTLY these values (max_length 40):
 awaiting_substitute "Awaiting substitute response"; applicant_action_required "Applicant action required";
 awaiting_unit_head "Awaiting Unit Head review"; awaiting_establishment "Awaiting Establishment routing";
 awaiting_final_sanction "Awaiting final sanction decision"; awaiting_director_self_sanction "Awaiting Director self-sanction";
 approved "Approved"; rejected "Rejected"; withdrawn "Withdrawn";
 cancellation_pending_unit_head "Cancellation pending - Unit Head"; cancellation_pending_establishment "Cancellation pending - Establishment";
 cancellation_pending_final "Cancellation pending - final decision"; cancelled "Cancelled".
KIND_CHOICES: new "New leave", extension "Extension of ongoing leave".
HALF_CHOICES: first "First half", second "Second half".
RECOMMENDATION_CHOICES: recommended "Recommended", not_recommended "Not recommended".
SUBSTITUTE_RESPONSE_CHOICES: pending "Pending", accepted "Accepted", declined "Declined".
RESUMPTION_CHOICES: none "Not submitted", pending "Review pending", reviewed_no_adjustment "Reviewed - no adjustment",
 reviewed_early "Reviewed - early return synchronized", reviewed_late "Reviewed - late return synchronized".
Fields:
 category FK(LeaveCategory, PROTECT, related_name="applications"); kind (choices, default "new");
 parent FK("self", null, blank, PROTECT, related_name="extensions")  # the approved leave an extension extends
 status (choices, default "awaiting_unit_head", db_index) ; start_date, end_date (DateField); half_day (CharField max 6, choices HALF_CHOICES, blank, default "");
 days_charged DecimalField(5,2, default 0)  # chargeable days computed by rules.calculate_leave_days
 balance_deducted DecimalField(5,2, default 0)  # what approval actually deducted, so cancellation can restore exactly that
 reason TextField; is_station_leave Boolean default False; station_details JSONField default dict blank (BR-EL-013, same application);
 medical_evidence_ref CharField(max 300, blank) (COL, BR-EL-009);
 substitute_user_id IntegerField null blank; substitute_response (choices, default "pending", only meaningful when a substitute is nominated);
 recommendation (choices, blank, default "")  # Unit Head record for SCL/EL/COL/VL (BR-EL-017)
 applicant_is_director Boolean default False  # BR-EL-020 routing flag captured at submission
 withdrawn_reason CharField(300, blank);
 actual_resumption_date DateField null blank; resumption_status (choices, default "none").
Meta: constraints = CheckConstraint named "leave_end_not_before_start" (end_date >= start_date, use `condition=` like the pattern file),
 CheckConstraint named "leave_half_day_single_day" (half_day == "" OR start_date == end_date; use F("end_date")),
 indexes = [Index(["user_id","status"], name="leave_app_user_status_idx"), Index(["category","start_date"], name="leave_app_cat_start_idx")].
`__str__` returns f"app#{pk} u{user_id} {category.code} {start_date}..{end_date} [{status}]".

## LeaveApplicationTransition (append-only audit)  db_table "leave_application_transition"
application FK(CASCADE, related_name="transitions"); from_status, to_status (CharField max 40); actor_user_id IntegerField null blank;
actor_label CharField(80, blank) (e.g. "employee", "unit_head", "system"); reason CharField(300, blank); at DateTimeField(auto_now_add).
Index on ["application","at"] named "leave_trans_app_idx".

## LeaveBalance(TimeStampedModel, UserScopedModel)  db_table "leave_balance"
category FK(PROTECT, related_name="balances"); year IntegerField; balance_days DecimalField(6,2); is_converted Boolean default False.
Constraints: UniqueConstraint(["category","user_id","year"], name="leave_balance_unique_per_year"),
 CheckConstraint(balance_days >= 0, name="leave_balance_not_negative").

## Output rules
Complete file only. No explanations, no placeholders, no TODOs. Max line length 100. No trailing whitespace on blank lines.
