# Institute Work Department (IWD) Module Blueprint

**Module Code:** iwd  
**Module Name:** Institute Work Department  
**Specification Path:** IWD/  
**Docs Folder:** docs/09-iwd/  
**Specification ID Prefix:** IWD- (BR-IWD-, UC-IWD-, BW-IWD-, CW-IWD-, CFR-IWD-, AFR-IWD-)  
**Environment:** module-only  

---

## Step 3.1 (a) — Traceability Table

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| BR-IWD-001 - Active-role authorization | A user may perform an IWD action only under an active authorized role; Department Head and Dean are distinct approval roles. | api + registry | api/permissions.py / registry.py | Type: Authorization |
| BR-IWD-002 - Automatic engineer assignment | A valid submitted complaint is automatically assigned to an Engineer using workload distribution and relevant expertise. | domain + services | domain/assignment.py | Type: Routing |
| BR-IWD-003 - Cost-band routing | Estimate routing uses three bands: total < Rs.25,000; Rs.25,000 <= total <= Rs.2.5 lakh; total > Rs.2.5 lakh. | domain | domain/routing.py | Type: Routing |
| BR-IWD-004 - Low-cost internal quotation | For an estimate below Rs.25,000, internal quotation/procurement is used only after IWD Admin approval when procurement is required. | domain | domain/state_machine.py / services/approvals.py | Type: Constraint |
| BR-IWD-005 - Mid-range committee review | A mid-range estimate requires committee necessity/feasibility review before the Department Head makes the first supervisory decision. | domain | domain/state_machine.py / services/approvals.py | Type: Constraint |
| BR-IWD-006 - Department Head mid-range decision | The Department Head may approve, reject, or forward a committee-reviewed mid-range estimate to the Director. | api + domain | domain/state_machine.py / services/approvals.py | Type: Authorization / Routing |
| BR-IWD-007 - High-cost bidding authorization | An estimate above Rs.2.5 lakh requires Director approval before external competitive bidding is initiated. | api + domain | domain/state_machine.py / services/approvals.py | Type: Authorization |
| BR-IWD-008 - Vendor-selection compliance | Vendor selection must use an approved vendor list or competitive bidding as applicable and comply with institutional policy. | domain | domain/state_machine.py / services/approvals.py | Type: Constraint |
| BR-IWD-009 - Rejection reason and resubmission | A rejected approval-stage request must retain the rejection reason and may be modified and resubmitted to the appropriate route. | api + domain | domain/state_machine.py / services/approvals.py | Type: Lifecycle |
| BR-IWD-010 - Inventory-before-procurement | Stock availability is checked before procurement is initiated for required maintenance materials. | domain | domain/state_machine.py / services/approvals.py | Type: Constraint |
| BR-IWD-011 - Inventory audit trail | Material usage and inventory movements associated with maintenance work must be recorded in an audit trail. | models + services | models/audit.py / services/audit.py | Type: Constraint |
| BR-IWD-012 - Urgent fast-track routing | An Engineer may flag an urgent repair for fast-track review by the Department Head or Director; fast-track status does not waive normal cost-based approval controls. | domain | domain/state_machine.py / services/approvals.py | Type: Routing |
| BR-IWD-013 - Audit logging of decisions | Approvals, modifications, and rejections in the IWD approval process must be logged. | models + services | models/audit.py / services/audit.py | Type: Constraint |
| BR-IWD-014 - Verify before resolution | A complaint may be marked resolved only after completed work passes physical verification. | domain | domain/state_machine.py | Type: Constraint |
| BR-IWD-015 - Financial audit basis | The Auditor validates invoices against the approved estimate and cross-checks completed-work reports/supporting evidence before forwarding the bill. | domain + services | domain/state_machine.py / services/billing.py | Type: Validation |
| BR-IWD-016 - Settlement authorization sequence | Payment settlement proceeds only after Auditor validation and Director final approval, after which Accounts performs settlement. | domain + services | domain/state_machine.py / services/billing.py | Type: Authorization |
| BR-IWD-017 - Feedback after resolution | Feedback/rating is available after physical verification resolves the complaint; a post-repair issue may be reported through the same channel. | api + domain | domain/state_machine.py / services/approvals.py | Type: Lifecycle |
| BR-IWD-018 - Department Head / Dean role separation | Department Head and Dean are distinct IWD/Fusion approval roles and must not be treated as aliases or interchangeable identities. | api + registry | api/permissions.py / registry.py | Type: Authorization |
| UC-IWD-001 - Submit Maintenance Complaint | Create a valid maintenance complaint and place it into the IWD work queue with automatic engineer assignment. (Actor: Institute Employee) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-002 |
| UC-IWD-005 - Track Complaint Status | View the current status of a complaint submitted by the Employee. (Actor: Institute Employee) | api + services | api/views.py + selectors/ | Related BRs: BR-IWD-001 |
| UC-IWD-015 - Assess Assigned Complaint | Review an assigned complaint and record the repair assessment needed to prepare an estimate. (Actor: Engineer) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001 |
| UC-IWD-021 - Prepare and Submit Estimate | Prepare and submit a time/material/cost estimate for an assessed complaint. (Actor: Engineer) | api + services | api/views.py + services/ | Related BRs: BR-IWD-003, BR-IWD-001 |
| UC-IWD-025 - Flag Urgent Repair | Mark an assigned/assessed repair as urgent so it receives fast-track attention. (Actor: Engineer) | api + services | api/views.py + services/ | Related BRs: BR-IWD-012, BR-IWD-001 |
| UC-IWD-031 - Review Low-Cost Estimate | Approve or reject an estimate below Rs.25,000. (Actor: IWD Admin) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-003, BR-IWD-004, BR-IWD-009, BR-IWD-013 |
| UC-IWD-041 - Conduct Mid-Range Review | Obtain committee feasibility input and make the Department Head supervisory decision for a mid-range estimate. (Actor: Department Head) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-003, BR-IWD-005, BR-IWD-006, BR-IWD-009, BR-IWD-013 |
| UC-IWD-051 - Director Review and Approval | Review a Director-routed estimate and record the Director decision; for high-cost work, approval authorizes external bidding. (Actor: Director) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-003, BR-IWD-006, BR-IWD-007, BR-IWD-009, BR-IWD-013 |
| UC-IWD-055 - Review Urgent Escalation | Acknowledge and prioritize an Engineer-flagged urgent repair for fast-track handling. (Actor: Department Head or Director) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-012, BR-IWD-013 |
| UC-IWD-061 - Check Stock and Issue Material | Check required stock and issue available material for approved work. (Actor: IWD Admin) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-010, BR-IWD-011 |
| UC-IWD-071 - Coordinate Procurement for Stock Shortage | Coordinate procurement when approved work requires material not available in stock. (Actor: IWD Admin) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-004, BR-IWD-008, BR-IWD-010 |
| UC-IWD-081 - Conduct External Bidding and Vendor Selection | Carry out the policy-compliant external competitive-bidding/vendor-selection activity authorized for high-cost work. (Actor: IWD Admin) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-007, BR-IWD-008, BR-IWD-013 |
| UC-IWD-091 - Execute Repair Work | Perform/coordinate approved repair work and record work progress, material usage, and completion. (Actor: Engineer) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-011, BR-IWD-014 |
| UC-IWD-101 - Verify Completed Work | Verify completed work quality and decide whether it may be resolved or requires rework. (Actor: Department Head) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-014, BR-IWD-013 |
| UC-IWD-111 - Submit Final Bill | Submit the final bill and supporting records after required physical verification. (Actor: Engineer) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-014 |
| UC-IWD-121 - Audit Final Bill | Validate the final bill against the approved estimate and completed-work evidence before settlement. (Actor: Auditor) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-015, BR-IWD-016 |
| UC-IWD-131 - Approve and Record Payment Settlement | Grant final payment approval after audit and record the Accounts settlement outcome. (Actor: Director) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-016, BR-IWD-013 |
| UC-IWD-141 - Submit Feedback or Report Post-Repair Issue | Provide feedback/rating for a resolved complaint or report a post-repair issue. (Actor: Institute Employee) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-017 |
| UC-IWD-145 - View Feedback | Review recorded feedback for quality monitoring. (Actor: Authorized IWD stakeholder) | api + services | api/views.py + selectors/ | Related BRs: BR-IWD-001, BR-IWD-017 |
| UC-IWD-151 - Modify and Resubmit Rejected Request | Correct a request rejected during approval and return it to the appropriate approval path. (Actor: Institute Employee or Engineer) | api + services | api/views.py + services/ | Related BRs: BR-IWD-001, BR-IWD-003, BR-IWD-009, BR-IWD-013 |
| UC-IWD-175 - Issue IWD Notifications | Issue timely IWD notifications to relevant recipients when a configured IWD notification event occurs. (Actor: N.A. - Event-triggered) | services | services/notifications.py | Related BRs: BR-IWD-002, BR-IWD-012 |
| UC-IWD-181 - Switch Active IWD Role | Select one of the user's assigned IWD roles as the active role for subsequent IWD actions. (Actor: Authorized IWD user) | IAM / platform | fusion_auth / shell role switcher | Related BRs: BR-IWD-001 |
| UC-IWD-191 - Synchronize Shared Fusion Data | Keep shared administrative/reference data used by IWD consistent with authoritative Fusion ERP sources. (Actor: Fusion ERP integration service) | contracts | contracts.py | Related BRs: N/A |
| BW-IWD-01 | State transitions for Complaint Intake and Assessment | domain + services | domain/state_machine.py | Spec workflow |
| BW-IWD-02 | State transitions for Low-Cost Estimate Approval | domain + services | domain/state_machine.py | Spec workflow |
| BW-IWD-03 | State transitions for Mid-Range Approval by Department Head | domain + services | domain/state_machine.py | Spec workflow |
| BW-IWD-04 | State transitions for Mid-Range Forward to Director | domain + services | domain/state_machine.py | Spec workflow |
| BW-IWD-05 | State transitions for High-Cost Approval and External Bidding | domain + services | domain/state_machine.py | Spec workflow |
| BW-IWD-06 | State transitions for Stock Available | domain + services | domain/state_machine.py | Spec workflow |
| BW-IWD-07 | State transitions for Low-Cost Stock Shortage Procurement | domain + services | domain/state_machine.py | Spec workflow |
| BW-IWD-08 | State transitions for Mid-Range Stock Shortage Procurement | domain + services | domain/state_machine.py | Spec workflow |
| BW-IWD-09 | State transitions for Work Execution and Verification | domain + services | domain/state_machine.py | Spec workflow |
| BW-IWD-10 | State transitions for Work Rework | domain + services | domain/state_machine.py | Spec workflow |
| BW-IWD-11 | State transitions for Billing, Audit and Settlement | domain + services | domain/state_machine.py | Spec workflow |
| BW-IWD-12 | State transitions for Rejected Low-Cost Estimate Resubmission | domain + services | domain/state_machine.py | Spec workflow |
| BW-IWD-13 | State transitions for Rejected Mid-Range Estimate Resubmission | domain + services | domain/state_machine.py | Spec workflow |
| BW-IWD-14 | State transitions for Rejected Director-Routed Estimate Resubmission | domain + services | domain/state_machine.py | Spec workflow |
| BW-IWD-15 | State transitions for Urgent Fast-Track Review | domain + services | domain/state_machine.py | Spec workflow |
| CW-IWD-01 | State transitions for Estimate Approval Routing | domain + services | domain/state_machine.py | Spec workflow |
| CW-IWD-02 | State transitions for Inventory and Procurement | domain + services | domain/state_machine.py | Spec workflow |
| CW-IWD-03 | State transitions for Work Completion and Verification | domain + services | domain/state_machine.py | Spec workflow |
| CW-IWD-04 | State transitions for Rejection and Resubmission | domain + services | domain/state_machine.py | Spec workflow |
| AFR-IWD-001 | The system shall allow an authenticated Institute Employee to submit a maintenance complaint. | api + services | services/complaints.py::create_complaint | Complaint intake validation and persistence |
| AFR-IWD-002 | The system shall capture the complaint issue category/nature, including civil or electrical maintenance. | api + services | services/complaints.py::create_complaint | Complaint intake validation and persistence |
| AFR-IWD-003 | The system shall capture the complaint location. | api + services | services/complaints.py::create_complaint | Complaint intake validation and persistence |
| AFR-IWD-004 | The system shall capture the complaint urgency level. | api + services | services/complaints.py::create_complaint | Complaint intake validation and persistence |
| AFR-IWD-005 | The system shall capture complaint remarks. | services | services/general.py | General implementation |
| AFR-IWD-006 | The system shall create and persist a complaint record after successful validation and submission. | api + services | services/complaints.py::create_complaint | Complaint intake validation and persistence |
| AFR-IWD-007 | The system shall automatically assign a submitted complaint to an Engineer using workload distribution and relevant expertise. | domain + services | services/assignment.py::assign_engineer_auto | Automatic engineer assignment based on domain rules |
| AFR-IWD-008 | The system shall allow an Institute Employee to track the current status of each submitted complaint. | selectors + api | selectors/complaints.py::list_complaints_for_actor | Scoped complaint status reading |
| AFR-IWD-009 | The system shall allow an Engineer to view complaints assigned to that Engineer. | services | services/general.py | General implementation |
| AFR-IWD-010 | The system shall allow an Engineer to record the assessment of an assigned complaint and the repairs required. | services + domain | services/complaints.py::record_assessment | Technical repair assessment recording |
| AFR-IWD-011 | The system shall allow an Engineer to record estimated repair time. | services | services/general.py | General implementation |
| AFR-IWD-012 | The system shall allow an Engineer to record required materials and quantities for an estimate. | services + models | services/inventory.py::issue_material | Inventory checking and material ledger logging |
| AFR-IWD-013 | The system shall allow an Engineer to record estimated cost and submit the estimate for approval. | domain + services | services/estimates.py::create_estimate | Estimate preparation and total validation |
| AFR-IWD-014 | The system shall classify and route a submitted estimate according to the applicable cost band. | domain + services | services/estimates.py::create_estimate | Estimate preparation and total validation |
| AFR-IWD-015 | The system shall route an estimate below Rs. 25,000 to IWD Admin for approval. | domain | domain/routing.py::determine_cost_band_route | Pure domain cost band routing |
| AFR-IWD-016 | The system shall allow IWD Admin to approve or reject an estimate below Rs. 25,000. | domain + services | services/estimates.py::resubmit_estimate | Rejection reason persistence and resubmission |
| AFR-IWD-017 | After IWD Admin approval of an estimate below Rs. 25,000, the system shall support the internal quotation/procurement route when procurement is required. | domain | domain/routing.py::determine_cost_band_route | Pure domain cost band routing |
| AFR-IWD-018 | The system shall route an estimate from Rs. 25,000 through Rs. 2.5 lakh for committee necessity/feasibility review. | domain | domain/routing.py::determine_cost_band_route | Pure domain cost band routing |
| AFR-IWD-019 | The system shall capture the committee necessity/feasibility outcome for a mid-range estimate. | domain + services | services/approvals.py::record_committee_review | Committee review recording |
| AFR-IWD-020 | The system shall allow the Department Head to approve, reject, or forward a mid-range estimate to the Director. | domain + services | services/approvals.py::review_mid_range | Department Head supervisory decision |
| AFR-IWD-021 | The system shall route an estimate above Rs. 2.5 lakh to the Director for approval. | domain | domain/routing.py::determine_cost_band_route | Pure domain cost band routing |
| AFR-IWD-022 | After Director approval of an estimate above Rs. 2.5 lakh, the system shall support initiation of external competitive bidding. | domain + services | services/approvals.py::review_high_cost | Director bidding authorization |
| AFR-IWD-023 | The system shall support vendor selection from an approved list or through competitive bidding, as applicable under institutional procurement policy. | services | services/procurement.py::select_vendor | Vendor selection compliance |
| AFR-IWD-024 | When an approval-stage request is rejected, the system shall record the rejection reason. | domain + services | services/estimates.py::resubmit_estimate | Rejection reason persistence and resubmission |
| AFR-IWD-025 | The system shall allow the responsible actor to modify a rejected complaint/estimate request when resubmission is permitted by the stated process. | domain + services | services/estimates.py::resubmit_estimate | Rejection reason persistence and resubmission |
| AFR-IWD-026 | The system shall allow a modified rejected request to be resubmitted to the appropriate approval route. | domain | domain/routing.py::determine_cost_band_route | Pure domain cost band routing |
| AFR-IWD-027 | The system shall allow IWD Admin to view and monitor inventory stock levels relevant to maintenance work. | services + models | services/inventory.py::issue_material | Inventory checking and material ledger logging |
| AFR-IWD-028 | The system shall check stock availability before initiating procurement for required materials. | services + models | services/inventory.py::issue_material | Inventory checking and material ledger logging |
| AFR-IWD-029 | The system shall record material usage against the relevant maintenance work. | services + models | services/inventory.py::issue_material | Inventory checking and material ledger logging |
| AFR-IWD-030 | The system shall maintain an audit trail of inventory movements associated with maintenance work. | services + models | services/inventory.py::issue_material | Inventory checking and material ledger logging |
| AFR-IWD-031 | When required stock is unavailable, the system shall allow IWD Admin to initiate or coordinate the applicable procurement action with the Procurement Team. | services + models | services/inventory.py::issue_material | Inventory checking and material ledger logging |
| AFR-IWD-032 | The system shall allow an Engineer to record work execution progress and mark the repair work complete. | services | services/general.py | General implementation |
| AFR-IWD-033 | The system shall allow an Engineer to flag a repair as urgent for fast-track attention. | domain + services | services/complaints.py::flag_urgent | Urgent priority escalation handling |
| AFR-IWD-034 | The system shall route an urgent flag to the Department Head or Director for fast-track review without removing applicable cost-based approval controls. | domain | domain/routing.py::determine_cost_band_route | Pure domain cost band routing |
| AFR-IWD-035 | The system shall log approval actions performed in the IWD process. | services | services/general.py | General implementation |
| AFR-IWD-036 | The system shall log modifications to approval-stage IWD requests. | services | services/general.py | General implementation |
| AFR-IWD-037 | The system shall log rejection actions and their recorded reasons. | domain + services | services/estimates.py::resubmit_estimate | Rejection reason persistence and resubmission |
| AFR-IWD-038 | The system shall prevent a complaint from being marked resolved until completed work has passed physical verification. | domain + services | services/execution.py::verify_work | Physical verification before resolution gate |
| AFR-IWD-039 | The system shall allow the Department Head to record the quality verification outcome for completed work. | domain + services | services/execution.py::verify_work | Physical verification before resolution gate |
| AFR-IWD-040 | After required physical verification, the system shall allow the Engineer to submit the final bill with supporting records. | domain + services | services/execution.py::verify_work | Physical verification before resolution gate |
| AFR-IWD-041 | The system shall allow the Auditor to validate invoices against the approved estimate. | services | services/general.py | General implementation |
| AFR-IWD-042 | The system shall allow the Auditor to cross-check completed-work reports and supporting evidence during bill validation. | services | services/billing.py::audit_bill | Auditor invoice and work cross-check |
| AFR-IWD-043 | The system shall allow the Auditor to forward a validated bill to the Director for final approval. | services | services/billing.py::audit_bill | Auditor invoice and work cross-check |
| AFR-IWD-044 | The system shall allow the Director to grant or withhold final approval for payment settlement after Auditor validation. | domain + services | services/billing.py::settle_payment | Director final approval and Accounts settlement |
| AFR-IWD-045 | After final approval, the system shall route the payment for Accounts settlement and record the resulting settlement status. | domain | domain/routing.py::determine_cost_band_route | Pure domain cost band routing |
| AFR-IWD-046 | After physical verification resolves a complaint, the system shall allow the Institute Employee to submit feedback and a rating. | domain + services | services/execution.py::verify_work | Physical verification before resolution gate |
| AFR-IWD-047 | The system shall allow the Institute Employee to report a post-repair issue through the feedback channel. | services + models | services/feedback.py::record_feedback | Feedback and post-repair issue recording |
| AFR-IWD-048 | The system shall allow authorized IWD stakeholders to view recorded feedback for quality monitoring. | services + models | services/feedback.py::record_feedback | Feedback and post-repair issue recording |
| AFR-IWD-049 | The system shall notify relevant stakeholders when a complaint is successfully submitted and assigned. | services | services/general.py | General implementation |
| AFR-IWD-050 | The system shall notify relevant stakeholders when the complaint/work status changes. | services | services/general.py | General implementation |
| AFR-IWD-051 | The system shall notify relevant stakeholders of estimate/budget approval decisions. | services | services/general.py | General implementation |
| AFR-IWD-052 | The system shall issue alerts when an urgent repair is escalated for fast-track review. | domain + services | services/complaints.py::flag_urgent | Urgent priority escalation handling |
| AFR-IWD-053 | The system shall issue configured notifications for submission deadlines and policy updates applicable to IWD users. | services | services/notifications.py::send_iwd_notification | IWD notification dispatch |
| AFR-IWD-054 | The system shall enforce role-based access to IWD functions according to the user's active authorized role. | api + registry | api/permissions.py / registry.py | RBAC role checks and distinct Dean/HOD authorization |
| AFR-IWD-055 | The system shall restrict access to sensitive financial information according to the active authorized role. | api + registry | api/permissions.py / registry.py | RBAC role checks and distinct Dean/HOD authorization |
| AFR-IWD-056 | The system shall restrict approval actions to users authorized for the corresponding IWD approval role. | api + registry | api/permissions.py / registry.py | RBAC role checks and distinct Dean/HOD authorization |
| AFR-IWD-057 | The system shall allow an authenticated user with multiple assigned IWD roles to switch to an authorized active IWD role. | api + registry | api/permissions.py / registry.py | RBAC role checks and distinct Dean/HOD authorization |
| AFR-IWD-058 | The system shall use shared Fusion ERP data/services where required to maintain consistency with other administrative modules. | contracts | contracts.py | ERP/IAM client integration contracts |
| AFR-IWD-060 | The system shall represent Department Head and Dean as distinct IWD approval roles and shall not treat either role as an alias of the other. | api + registry | api/permissions.py / registry.py | RBAC role checks and distinct Dean/HOD authorization |


---

## Step 3.2 (b) — Domain Model

### Entities, Invariants, and Database Constraints

1. **Complaint (models/complaint.py)**
   - **Fields:**
     - id: AutoField / BigAutoField
     - complaint_id: CharField(max_length=32, unique=True) (e.g. CMP-2026-0001)
     - complainant_user_id: IntegerField(db_index=True) (plain user_id, ADR-0002)
     - category: CharField(max_length=30, choices=['civil', 'electrical'])
     - location: CharField(max_length=255)
     - urgency: CharField(max_length=20, choices=['low', 'medium', 'high', 'emergency'])
     - 
emarks: TextField(blank=True)
     - status: CharField(max_length=40, default='submitted', db_index=True)
     - ssigned_engineer_id: IntegerField(null=True, blank=True, db_index=True)
     - is_urgent_escalated: BooleanField(default=False)
     - urgent_escalated_at: DateTimeField(null=True, blank=True)
     - urgent_escalated_to: CharField(max_length=30, null=True, blank=True)
     - created_at: DateTimeField(auto_now_add=True)
     - updated_at: DateTimeField(auto_now=True)
   - **Constraints & Invariants:**
     - CheckConstraint(check=Q(category__in=['civil', 'electrical']), name='valid_complaint_category')
     - CheckConstraint(check=Q(urgency__in=['low', 'medium', 'high', 'emergency']), name='valid_complaint_urgency')
     - State machine validation on all transitions.

2. **RepairAssessment (models/complaint.py)**
   - **Fields:**
     - complaint: OneToOneField(Complaint, on_delete=CASCADE, related_name='assessment')
     - engineer_id: IntegerField()
     - ssessment_details: TextField()
     - is_site_visit_complete: BooleanField(default=True)
     - created_at: DateTimeField(auto_now_add=True)
     - updated_at: DateTimeField(auto_now=True)

3. **RepairEstimate (models/estimate.py)**
   - **Fields:**
     - id: BigAutoField
     - complaint: ForeignKey(Complaint, on_delete=CASCADE, related_name='estimates')
     - ersion: IntegerField(default=1)
     - engineer_id: IntegerField()
     - 	ime_estimate_days: IntegerField()
     - materials_cost: DecimalField(max_digits=12, decimal_places=2)
     - labor_cost: DecimalField(max_digits=12, decimal_places=2)
     - other_cost: DecimalField(max_digits=12, decimal_places=2, default=0.00)
     - 	otal_cost: DecimalField(max_digits=12, decimal_places=2, db_index=True)
     - cost_band: CharField(max_length=20, choices=['low', 'mid', 'high'])
     - status: CharField(max_length=40, default='pending_review')
     - 
ejection_reason: TextField(blank=True, default='')
     - created_at: DateTimeField(auto_now_add=True)
     - updated_at: DateTimeField(auto_now=True)
   - **Constraints & Invariants:**
     - UniqueConstraint(fields=['complaint', 'version'], name='unique_complaint_estimate_version')
     - CheckConstraint(check=Q(total_cost__gte=0), name='non_negative_estimate_total')
     - CheckConstraint(check=Q(time_estimate_days__gt=0), name='positive_estimate_days')
     - Invariant: 	otal_cost == materials_cost + labor_cost + other_cost.
     - Invariant: cost_band strictly matches BR-IWD-003:
       - Low: 	otal_cost < 25000
       - Mid: 25000 <= total_cost <= 250000
       - High: 	otal_cost > 250000

4. **ReviewCommitteeOutcome (models/approvals.py)**
   - **Fields:**
     - estimate: OneToOneField(RepairEstimate, on_delete=CASCADE, related_name='committee_review')
     - 
eviewer_user_id: IntegerField()
     - is_feasible: BooleanField()
     - is_necessary: BooleanField()
     - 
emarks: TextField()
     - 
eviewed_at: DateTimeField(auto_now_add=True)

5. **DecisionAuditTrail (models/audit.py)**
   - **Fields:**
     - id: BigAutoField
     - complaint: ForeignKey(Complaint, on_delete=CASCADE, related_name='audit_trails')
     - estimate: ForeignKey(RepairEstimate, null=True, blank=True, on_delete=SET_NULL)
     - ctor_user_id: IntegerField()
     - cting_role: CharField(max_length=50)
     - ction: CharField(max_length=50)
     - rom_state: CharField(max_length=40)
     - 	o_state: CharField(max_length=40)
     - decision_reason: TextField(blank=True)
     - 	imestamp: DateTimeField(auto_now_add=True, db_index=True)
   - **Invariant:** Immutable ledger; rows are appended only, never updated or deleted.

6. **InventoryItem & MaterialIssueLedger (models/inventory.py)**
   - **InventoryItem:**
     - item_code: CharField(max_length=50, unique=True)
     - 
ame: CharField(max_length=255)
     - category: CharField(max_length=50)
     - unit: CharField(max_length=30)
     - current_stock: IntegerField(default=0)
   - **MaterialIssueLedger (Append-Only):**
     - id: BigAutoField
     - complaint: ForeignKey(Complaint, on_delete=CASCADE, related_name='material_issues')
     - item: ForeignKey(InventoryItem, on_delete=PROTECT)
     - quantity: IntegerField()
     - issued_by_user_id: IntegerField()
     - issued_at: DateTimeField(auto_now_add=True)
   - **Invariant:**
     - CheckConstraint(check=Q(current_stock__gte=0), name='non_negative_inventory_stock')
     - Stock changes are tracked with ledger entries (Step 2.7).

7. **ProcurementOrder & VendorSelection (models/procurement.py)**
   - **Fields:**
     - id: BigAutoField
     - complaint: ForeignKey(Complaint, on_delete=CASCADE)
     - estimate: ForeignKey(RepairEstimate, on_delete=CASCADE)
     - procurement_type: CharField(max_length=30, choices=['internal_quotation', 'external_bidding'])
     - endor_name: CharField(max_length=255)
     - endor_details: TextField()
     - quoted_amount: DecimalField(max_digits=12, decimal_places=2)
     - compliance_confirmed: BooleanField(default=False)
     - status: CharField(max_length=30, default='in_progress')
     - created_at: DateTimeField(auto_now_add=True)

8. **PhysicalVerification (models/execution.py)**
   - **Fields:**
     - complaint: OneToOneField(Complaint, on_delete=CASCADE, related_name='physical_verification')
     - erified_by_user_id: IntegerField()
     - is_approved: BooleanField()
     - erification_remarks: TextField()
     - 
ework_notes: TextField(blank=True)
     - erified_at: DateTimeField(auto_now_add=True)

9. **FinalBill & PaymentSettlement (models/billing.py)**
   - **FinalBill:**
     - complaint: OneToOneField(Complaint, on_delete=CASCADE, related_name='final_bill')
     - engineer_id: IntegerField()
     - invoice_number: CharField(max_length=100)
     - claimed_amount: DecimalField(max_digits=12, decimal_places=2)
     - is_audited: BooleanField(default=False)
     - uditor_user_id: IntegerField(null=True, blank=True)
     - udit_remarks: TextField(blank=True)
     - udit_timestamp: DateTimeField(null=True, blank=True)
     - director_approved: BooleanField(default=False)
     - director_user_id: IntegerField(null=True, blank=True)
     - director_approved_at: DateTimeField(null=True, blank=True)
     - settlement_status: CharField(max_length=30, default='pending')
     - ccounts_reference: CharField(max_length=100, blank=True)
     - settled_at: DateTimeField(null=True, blank=True)

10. **ComplaintFeedback (models/feedback.py)**
    - **Fields:**
      - complaint: OneToOneField(Complaint, on_delete=CASCADE, related_name='feedback')
      - user_id: IntegerField()
      - 
ating: IntegerField()
      - eedback_text: TextField(blank=True)
      - post_repair_issue: TextField(blank=True)
      - created_at: DateTimeField(auto_now_add=True)
    - **Constraints:**
      - CheckConstraint(check=Q(rating__gte=1) & Q(rating__lte=5), name='valid_rating_1_to_5')

---

## Step 3.3 (c) — State Machine

A declarative transition table in domain/state_machine.py:

`python
TRANSITIONS = {
    # 1. Intake and Assessment
    ('submitted', 'assign_engineer', 'system'): 'assigned',
    ('assigned', 'record_assessment', 'engineer'): 'assessed',

    # 2. Estimate Routing
    ('assessed', 'submit_estimate_low', 'engineer'): 'low_cost_review_pending',
    ('assessed', 'submit_estimate_mid', 'engineer'): 'mid_range_committee_pending',
    ('assessed', 'submit_estimate_high', 'engineer'): 'director_review_high_pending',

    # 3. Low-Cost Approval
    ('low_cost_review_pending', 'approve_low_cost', 'iwd_admin'): 'estimate_approved',
    ('low_cost_review_pending', 'reject_low_cost', 'iwd_admin'): 'rejected_low_cost',

    # 4. Mid-Range Approval
    ('mid_range_committee_pending', 'record_committee_review', 'review_committee'): 'dept_head_review_pending',
    ('dept_head_review_pending', 'approve_dept_head', 'department_head'): 'estimate_approved',
    ('dept_head_review_pending', 'forward_to_director', 'department_head'): 'director_review_mid_pending',
    ('dept_head_review_pending', 'reject_dept_head', 'department_head'): 'rejected_mid_range',
    ('director_review_mid_pending', 'approve_director_mid', 'director'): 'estimate_approved',
    ('director_review_mid_pending', 'reject_director_mid', 'director'): 'rejected_director_route',

    # 5. High-Cost Approval and Bidding
    ('director_review_high_pending', 'authorize_bidding', 'director'): 'bidding_authorized',
    ('director_review_high_pending', 'reject_director_high', 'director'): 'rejected_director_route',
    ('bidding_authorized', 'select_vendor', 'iwd_admin'): 'vendor_selected',
    ('vendor_selected', 'confirm_procurement', 'iwd_admin'): 'estimate_approved',

    # 6. Inventory & Procurement
    ('estimate_approved', 'issue_materials_direct', 'iwd_admin'): 'ready_for_execution',
    ('estimate_approved', 'flag_procurement_low', 'iwd_admin'): 'procurement_needed_low',
    ('estimate_approved', 'flag_procurement_mid', 'iwd_admin'): 'procurement_needed_mid',
    ('procurement_needed_low', 'complete_procurement', 'iwd_admin'): 'materials_available',
    ('procurement_needed_mid', 'complete_procurement', 'iwd_admin'): 'materials_available',
    ('materials_available', 'issue_materials', 'iwd_admin'): 'ready_for_execution',

    # 7. Work Execution, Verification & Rework
    ('ready_for_execution', 'complete_work', 'engineer'): 'verification_pending',
    ('verification_pending', 'verify_approved', 'department_head'): 'resolved',
    ('verification_pending', 'verify_rework', 'department_head'): 'rework_required',
    ('rework_required', 'complete_work', 'engineer'): 'verification_pending',

    # 8. Billing, Audit, Settlement
    ('resolved', 'submit_final_bill', 'engineer'): 'audit_pending',
    ('audit_pending', 'audit_validated', 'auditor'): 'director_payment_approval_pending',
    ('director_payment_approval_pending', 'approve_payment', 'director'): 'accounts_settlement_pending',
    ('accounts_settlement_pending', 'record_settlement', 'accounts'): 'settled',

    # 9. Rejections and Resubmissions
    ('rejected_low_cost', 'resubmit_estimate', 'engineer'): 'low_cost_review_pending',
    ('rejected_mid_range', 'resubmit_estimate', 'engineer'): 'mid_range_committee_pending',
    ('rejected_director_route', 'resubmit_estimate', 'engineer'): 'director_review_high_pending',
}
`

---

## Step 3.4 (d) — Permission List

Prefix: iwd.  
Verbs strictly drawn from docs/02-iam/rbac-model.md closed list (iew, create, update, delete, manage):

1. iwd.complaint.create — Submit a maintenance complaint (Institute Employee)
2. iwd.complaint.view — View complaints (Employee views own via scoping; Engineer/Admin views all)
3. iwd.complaint.update — Update complaint status / assign / flag urgent
4. iwd.estimate.create — Prepare repair estimate (Engineer)
5. iwd.estimate.view — View repair estimates
6. iwd.estimate.update — Modify and resubmit rejected estimate (Engineer)
7. iwd.estimate.manage — Approve or reject estimates across cost bands (IWD Admin, Dept Head, Director)
8. iwd.committee_review.create — Record committee feasibility review (Review Committee / Dept Head)
9. iwd.inventory.view — View inventory items and stock levels
10. iwd.inventory.update — Issue materials and update stock ledger (IWD Admin)
11. iwd.procurement.manage — Coordinate quotations, vendor selection, bidding (IWD Admin)
12. iwd.verification.manage — Record physical verification of completed work (Department Head)
13. iwd.bill.create — Submit final bill after verification (Engineer)
14. iwd.bill.view — View final bills and invoices
15. iwd.bill.manage — Audit final bill (Auditor)
16. iwd.settlement.manage — Approve payment settlement (Director) and record settlement (Accounts)
17. iwd.feedback.create — Submit feedback and post-repair issues (Employee)
18. iwd.feedback.view — View recorded complaint feedback

### Role Grants Mapping (
egistry.py)
- aculty / staff / student (as Institute Employee): iwd.complaint.create, iwd.complaint.view, iwd.feedback.create
- engineer: iwd.complaint.view, iwd.complaint.update, iwd.estimate.create, iwd.estimate.view, iwd.estimate.update, iwd.bill.create, iwd.bill.view, iwd.feedback.view
- iwd_admin: iwd.complaint.view, iwd.estimate.view, iwd.estimate.manage, iwd.inventory.view, iwd.inventory.update, iwd.procurement.manage, iwd.feedback.view
- department_head: iwd.complaint.view, iwd.estimate.view, iwd.estimate.manage, iwd.committee_review.create, iwd.verification.manage, iwd.feedback.view
- director: iwd.complaint.view, iwd.estimate.view, iwd.estimate.manage, iwd.settlement.manage, iwd.feedback.view
- uditor: iwd.complaint.view, iwd.estimate.view, iwd.bill.view, iwd.bill.manage
- ccounts: iwd.bill.view, iwd.settlement.manage
- Dean: Distinct role (BR-IWD-018), view permissions only (iwd.complaint.view, iwd.estimate.view, iwd.feedback.view) pending specific policy workflow.

---

## Step 3.5 (e) — Endpoint List

All endpoints prefixed with /api/v1/iwd/:

| Method | Path | Required Permission | Gate / Scoping | Description | Rule IDs |
|---|---|---|---|---|---|
| POST | /complaints/ | iwd.complaint.create | Role check | Submit maintenance complaint | AFR-IWD-001-006, BR-IWD-001, BR-IWD-002 |
| GET | /complaints/ | iwd.complaint.view | Scoped to user or active role | List complaints (Employee sees own, Engineer sees assigned, Admin sees all) | AFR-IWD-008, AFR-IWD-009, UC-IWD-005 |
| GET | /complaints/{id}/ | iwd.complaint.view | Scoped (404 on unowned) | Complaint details + audit log | AFR-IWD-008, BR-IWD-013 |
| POST | /complaints/{id}/assess/ | iwd.complaint.update | Assigned Engineer | Record assessment | AFR-IWD-010-011, UC-IWD-015 |
| POST | /complaints/{id}/urgent/ | iwd.complaint.update | Assigned Engineer | Flag urgent repair | AFR-IWD-033, BR-IWD-012, UC-IWD-025 |
| POST | /complaints/{id}/urgent-review/ | iwd.complaint.update | Dept Head or Director | Acknowledge urgent priority | AFR-IWD-034, BR-IWD-012, UC-IWD-055 |
| POST | /complaints/{id}/estimates/ | iwd.estimate.create | Assigned Engineer | Submit repair estimate | AFR-IWD-012-015, BR-IWD-003, UC-IWD-021 |
| GET | /complaints/{id}/estimates/ | iwd.estimate.view | Scoped to complaint | List estimates for complaint | AFR-IWD-013 |
| POST | /estimates/{id}/review-low/ | iwd.estimate.manage | IWD Admin | Low-cost approval/rejection | AFR-IWD-016-017, BR-IWD-004, UC-IWD-031 |
| POST | /estimates/{id}/committee-review/| iwd.committee_review.create| Committee / Dept Head | Record committee input | AFR-IWD-019, BR-IWD-005, UC-IWD-041 |
| POST | /estimates/{id}/review-mid/ | iwd.estimate.manage | Dept Head | Mid-range approve/reject/forward | AFR-IWD-020, BR-IWD-006, UC-IWD-041 |
| POST | /estimates/{id}/review-director/| iwd.estimate.manage| Director | High-cost or forwarded approval | AFR-IWD-022, BR-IWD-007, UC-IWD-051 |
| POST | /estimates/{id}/resubmit/ | iwd.estimate.update | Assigned Engineer | Resubmit rejected estimate | AFR-IWD-025-026, BR-IWD-009, UC-IWD-151 |
| GET | /inventory/ | iwd.inventory.view | Staff / Admin | List inventory items | AFR-IWD-027, UC-IWD-061 |
| POST | /complaints/{id}/issue-materials/| iwd.inventory.update| IWD Admin | Issue materials / stock check | AFR-IWD-028-030, BR-IWD-010, BR-IWD-011 |
| POST | /complaints/{id}/procure/ | iwd.procurement.manage | IWD Admin | Coordinate procurement / quotation | AFR-IWD-017, AFR-IWD-031, BR-IWD-004 |
| POST | /complaints/{id}/vendor-bidding/| iwd.procurement.manage| IWD Admin | External bidding / vendor selection | AFR-IWD-023, BR-IWD-008, UC-IWD-081 |
| POST | /complaints/{id}/complete-work/ | iwd.complaint.update | Assigned Engineer | Mark repair work complete | AFR-IWD-032, UC-IWD-091 |
| POST | /complaints/{id}/verify/ | iwd.verification.manage | Dept Head | Physical verification / rework | AFR-IWD-038-039, BR-IWD-014, UC-IWD-101 |
| POST | /complaints/{id}/final-bill/ | iwd.bill.create | Assigned Engineer | Submit final bill | AFR-IWD-040, UC-IWD-111 |
| POST | /complaints/{id}/audit-bill/ | iwd.bill.manage | Auditor | Validate/query final bill | AFR-IWD-041-042, BR-IWD-015, UC-IWD-121 |
| POST | /complaints/{id}/settle-payment/| iwd.settlement.manage | Director / Accounts | Approve & record settlement | AFR-IWD-043-045, BR-IWD-016, UC-IWD-131 |
| POST | /complaints/{id}/feedback/ | iwd.feedback.create | Original Complainant | Submit feedback / post-repair | AFR-IWD-046-048, BR-IWD-017, UC-IWD-141 |
| GET | /complaints/{id}/feedback/ | iwd.feedback.view | Authorized roles | View complaint feedback | AFR-IWD-047, UC-IWD-145 |

### Client Routes & Navigation (client/src/modules/iwd/routes.tsx)
- /iwd/complaints — My Complaints & New Complaint (Guarded: RequireAuth)
- /iwd/assigned — Engineer Work Queue (Guarded: RequirePermission(iwd.complaint.update))
- /iwd/approvals — Approval Dashboard (Guarded: RequirePermission(iwd.estimate.manage))
- /iwd/inventory — Material & Procurement Hub (Guarded: RequirePermission(iwd.inventory.view))
- /iwd/verification — Completed Work Verification (Guarded: RequirePermission(iwd.verification.manage))
- /iwd/billing — Audit & Payment Settlement (Guarded: RequirePermission(iwd.bill.manage))

---

## Step 3.6 (f) — Contracts

modules/iwd/contracts.py:
- get_complaints_by_user(user_ids: Sequence[int]) -> Sequence[ComplaintSummaryDTO]
- get_active_work_orders(department_ids: Sequence[int]) -> Sequence[WorkOrderDTO]
- Plural queries only (ops/checks/contracts_are_plural.py).

External dependencies:
- Reaches IAM via HTTP client (usion_auth/client.py) for user identities, roles, and designations.
- Plain integer user_id used for all actor linkages (no cross-database foreign keys, ADR-0002, ADR-0013).

---

## Step 3.7 (g) — Scheduled Work

modules/iwd/schedule.py:
- check_urgent_escalation_reminders: Runs hourly (Celery beat). Checks complaints in urgent review pending > 24h and issues reminder notification.
- In module-only, Celery beat runs in background if tasks exist.

---

## Step 3.8 (h) — Open Questions

1. **Dean-Specific Routing:** As clarified in the DIRECT_FINAL_v2 problem statement, Department Head and Dean are distinct approval roles. However, the exact Dean-specific cost-band or workflow stage was not defined in the source problem statement. Dean is modeled as an active role with review/view capabilities, but no artificial workflow transitions are invented.
2. **Review Committee Composition:** The review committee input for mid-range estimates is recorded as a necessity/feasibility review by authorized users; specific committee voting rules are kept configurable.
