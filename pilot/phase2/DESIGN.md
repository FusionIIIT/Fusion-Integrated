# ELM Phase 2 target design (review decisions; code is written by the local model)

Rules: no user table (people are integer user ids from request.principal.user_id); never import another module's models; domain/ is pure Python; all writes in services/ inside transaction.atomic; every state change appends a LeaveAction row.

## models.py
- LeaveCategory(TextChoices): CL, RH, SCL, EL, COL, VL. CharField max_length=3.
- HalfDay(TextChoices): NONE="none", FIRST="first", SECOND="second".
- Stage(TextChoices): SUBSTITUTE="substitute", UNIT_HEAD="unit_head", ESTABLISHMENT="establishment", SANCTION="sanction", DONE="done".
- Status(TextChoices): PENDING="pending", APPROVED="approved", REJECTED="rejected", WITHDRAWN="withdrawn", CANCELLED="cancelled".
- SubstituteStatus(TextChoices): NOT_REQUIRED="not_required", PENDING="pending", ACCEPTED="accepted", DECLINED="declined".
- RequestKind(TextChoices): LEAVE="leave", CANCELLATION="cancellation".
- ReportingLine(TimeStampedModel): user_id IntegerField(unique=True), unit_head_id IntegerField, establishment_id IntegerField(null=True, blank=True), sanctioning_authority_id IntegerField(null=True, blank=True).
- LeaveApplication(UserScopedModel, TimeStampedModel): kind, parent ForeignKey("self", null=True, blank=True, on_delete=PROTECT, related_name="cancellations"), category, start_date, end_date, half_day (default NONE), days DecimalField(max_digits=5, decimal_places=1), purpose TextField, station_leave BooleanField(default=False), station_address TextField(blank=True), substitute_id IntegerField(null=True, blank=True), substitute_status (default NOT_REQUIRED), unit_head_id IntegerField, establishment_id IntegerField(null=True, blank=True), sanctioning_authority_id IntegerField(null=True, blank=True), unit_head_recommendation CharField(max_length=20, blank=True), stage, status (default PENDING), assignee_id IntegerField(null=True, blank=True, db_index=True), decided_at DateTimeField(null=True, blank=True). Meta ordering ["-created_at"].
- LeaveBalance(UserScopedModel, TimeStampedModel): category, year IntegerField, entitled DecimalField(5,1), used DecimalField(5,1, default=0). UniqueConstraint(user_id, year, category). property available = entitled - used.
- LeaveAction(models.Model): application ForeignKey(LeaveApplication, CASCADE, related_name="actions"), actor_id IntegerField, action CharField(40), remark TextField(blank=True), created_at DateTimeField(auto_now_add=True). Meta ordering ["created_at"].

## domain/policy.py (pure Python, Decimal arithmetic)
- ENTITLEMENT = {category: (days_per_year, faculty_allowed, staff_allowed, carries_forward)}: CL (8, yes, yes, no) BR-EL-002; RH (2, yes, yes, no) BR-EL-003; SCL (15, yes, yes, no) BR-EL-004; EL (30, no, yes, yes) BR-EL-005; COL (20, yes, yes, yes) BR-EL-009; VL (60, yes, no, no) BR-EL-006.
- entitlement(category, kind) -> Decimal | None. kind "faculty" means faculty, anything else is staff. None means not eligible (BR-EL-001).
- count_days(category, start, end, half_day) -> Decimal. Raise PolicyError if end < start. half_day other than "none" only for CL and only when start == end, giving 0.5 (BR-EL-010). EL, COL, VL count every calendar day inclusive (BR-EL-011). CL, RH, SCL count Monday to Friday only (no holiday calendar yet).
- overlaps(a_start, a_end, a_half, b_start, b_end, b_half) -> bool. True when the date ranges intersect, except a single shared date where both halves are set and different (BR-EL-012).
- unit_head_is_final(category) -> bool: True for CL and RH (BR-EL-016); others only get a recommendation (BR-EL-017).
- class PolicyError(Exception).

## Workflow (services)
apply -> stage SUBSTITUTE (assignee = substitute) if a substitute is nominated, else UNIT_HEAD (assignee = unit head).
Substitute accepts -> UNIT_HEAD. Declines -> substitute_status DECLINED, assignee None; applicant nominates a replacement (back to SUBSTITUTE) or withdraws (BR-EL-015).
UNIT_HEAD: CL/RH approve or reject is final. Other categories: "recommended" or "not_recommended" (not a rejection), then ESTABLISHMENT if establishment_id else SANCTION.
ESTABLISHMENT: verify -> SANCTION (assignee = sanctioning authority).
SANCTION: approve or reject is final.
If the applicant is their own unit head (unit_head_id == user_id, e.g. Director), skip UNIT_HEAD and go to SANCTION; if there is no sanctioning authority either, the applicant self-sanctions (BR-EL-020).
Approval of a LEAVE request adds days to LeaveBalance.used for the start year. Rejection or withdrawal changes no balance.
Withdraw: owner only, only while PENDING (BR-EL-022). Pending requests are never edited (BR-EL-034).
Cancellation: owner asks before start_date for an APPROVED leave; creates a CANCELLATION request (parent = the leave) routed like the original (BR-EL-023). Approving it marks the parent CANCELLED and subtracts its days from used.
Only the current assignee may act; anyone else gets NotFound (shown as 404, so ids are not leaked).

## Permissions (registry.py, code "leave")
leave.application.apply, leave.application.view_own, leave.substitute.respond, leave.application.review, leave.application.verify, leave.application.sanction, leave.admin.manage.
Roles: Employee = apply, view_own, substitute.respond. Unit Head = review. Deputy Registrar (Estt.) = review, verify. Dean, Registrar, Director = review, sanction. Leave Administrator = admin.manage.
Nav: /leave/apply (apply), /leave/mine (view_own), /leave/substitute (substitute.respond), /leave/approvals (review).

## API (base /api/v1/leave/)
GET/POST applications/ ; GET applications/<id>/ ; POST applications/<id>/withdraw/ ; POST applications/<id>/cancel/ ;
POST applications/<id>/substitute-response/ {"accept": bool} ; POST applications/<id>/replace-substitute/ {"substitute_id": int} ;
GET inbox/ ; POST applications/<id>/decide/ {"decision": str} ; GET balances/?year= ; GET/PUT reporting-lines/<user_id>/ (admin).
Errors reuse Fusion's core.api.exceptions: services raise LeaveError (class LeaveError(BadRequestError), HTTP 400) and NotFound (class NotFound(NotFoundError), HTTP 404); selectors raise core.api.exceptions.NotFoundError directly. The platform exception handler (core.api.exceptions.exception_handler) renders the standard {"error": {"code", "message", "details", "request_id"}} envelope, so views never catch these or build error responses themselves.
