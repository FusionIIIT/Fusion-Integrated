# Procurement & Stores Management (`psm`) — Blueprint

Module code: `psm` · URL prefix: `/api/v1/psm/` · Client base path: `/psm` · Docs folder: `docs/09-psm/`  
Spec baseline: `PSM_SPECS/` (Problem Statement v1.1, CFR/AFR Registry v1.1, Use Cases v1.2, Business Rules v1.2, Workflows v1.1, Traceability Matrix v1.1).

---

## (a) Traceability Table

Every live specification ID from Phase 0 mapped to its architecture layer and planned enforcement point. Retired/unused IDs (`BR-PSM-002`, `BR-PSM-011`, `BR-PSM-016`, `PSM-UC-004`, `PSM-UC-006`, `PSM-UC-018`) are excluded and are never cited in code.

### Consolidated Requirements (`CFR-PSM-001` – `CFR-PSM-020`)

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| `CFR-PSM-001` | Controlled indent creation, validation, duplicate detection, unique ID, timestamp, audit | `domain/` + `services/` + `models/` | `domain/indent_rules.py`, `services/indents.py::create_and_submit`, `models/indent.py` | Rolls up `AFR-PSM-001`..`007` |
| `CFR-PSM-002` | Permissible-state indent modification, withdrawal/cancel, repeat-as-draft, versioning, history | `domain/` + `services/` + `selectors/` | `domain/state_machine.py`, `services/indents.py::{modify,withdraw,repeat_as_draft}`, `selectors/indents.py` | Rolls up `AFR-PSM-008`..`012` |
| `CFR-PSM-003` | Departmental & central stock check, requestor notification, reservation, anti-overcommit | `domain/` + `services/` + `models/` | `domain/stock_rules.py`, `services/stock.py::check_and_reserve`, `models/stock.py` | Rolls up `AFR-PSM-013`..`016` |
| `CFR-PSM-004` | Internal stock issue pick/dispatch, requestor receipt ack, final posting gated on confirmation & no discrepancy | `domain/` + `services/` | `services/stock.py::schedule_and_dispatch_issue`, `services/receipts.py::{record_grn,confirm_receipt}` | Rolls up `AFR-PSM-017`..`021` |
| `CFR-PSM-005` | Configurable approval hierarchy, priority direct path, criticality, SLA reminders/escalations, rejection justification, audit | `domain/` + `services/` + `tasks.py` | `domain/approval_policy.py`, `services/approvals.py`, `tasks.py::check_approval_slas` | Rolls up `AFR-PSM-022`..`029` |
| `CFR-PSM-006` | External procurement routing when stock insufficient & direct vs. tender selection by threshold | `domain/` + `services/` | `domain/approval_policy.py::select_procurement_method`, `services/procurement.py::review_and_select_method` | Rolls up `AFR-PSM-030`..`031` |
| `CFR-PSM-007` | Tender publication, bid receipt, evaluation against criteria, committee approval, traceable retention | `services/` + `models/` | `services/tenders.py::{publish,record_bid,evaluate_and_award}`, `models/tender.py` | Rolls up `AFR-PSM-032`..`036` |
| `CFR-PSM-008` | PO creation only after required approvals, linked to indent & verified vendor | `domain/` + `services/` + `models/` | `services/procurement.py::create_and_issue_po`, `models/procurement.py::PurchaseOrder` | Rolls up `AFR-PSM-037`..`040` |
| `CFR-PSM-009` | Central tracking of PO status and planned/actual delivery schedules | `services/` + `selectors/` + `models/` | `services/procurement.py::update_po_schedule`, `selectors/procurement.py::purchase_orders_for` | Rolls up `AFR-PSM-041`..`042` |
| `CFR-PSM-010` | Authorized delivery inspection, GRN creation, partial receipt & rejection, accepted-only stock posting | `domain/` + `services/` | `domain/receipt_rules.py`, `services/receipts.py::{record_grn,confirm_receipt}` | Rolls up `AFR-PSM-043`..`047` |
| `CFR-PSM-011` | Discrepancy/damage logging with evidence & case status tracking | `services/` + `models/` + `core/files/` | `services/discrepancies.py::report_discrepancy`, `models/procurement.py::DiscrepancyCase` | Rolls up `AFR-PSM-048`..`049`, `053` |
| `CFR-PSM-012` | Return/replacement/warranty initiation, vendor comms, inventory & accounting adjustments on resolution | `domain/` + `services/` | `services/discrepancies.py::resolve_case`, `services/stock.py::record_adjustment` | Rolls up `AFR-PSM-050`..`052`, `054`..`055` |
| `CFR-PSM-013` | Three-way PO-GRN-Invoice match, payment release gate, mismatch hold, partial payment rules | `domain/` + `services/` + `models/` | `domain/finance_rules.py::three_way_match`, `services/finance.py::{verify_invoice,process_payment}` | Rolls up `AFR-PSM-056`..`059` |
| `CFR-PSM-014` | Vendor onboarding, master maintenance, GST/bank/compliance validation, unverified block, versioning & audit | `domain/` + `services/` + `models/` | `domain/vendor_rules.py`, `services/vendors.py::{onboard,update_vendor,verify_vendor}`, `models/vendor.py` | Rolls up `AFR-PSM-060`..`066` |
| `CFR-PSM-015` | Inter-departmental stock transfer request, reserve, dispatch, receipt confirm, dual-ledger posting, audit | `domain/` + `services/` + `models/` | `services/transfers.py::{request_transfer,dispatch_transfer,confirm_transfer}`, `models/stock.py` | Rolls up `AFR-PSM-067`..`073` |
| `CFR-PSM-016` | Operational, procurement, stock, and financial reports | `selectors/` + `services/` | `services/reports.py::generate_report` | Rolls up `AFR-PSM-074`..`077` |
| `CFR-PSM-017` | Report filtering, export, scheduled generation, and mandatory generation logging | `services/` + `tasks.py` + `models/` | `services/reports.py::{generate_report,create_schedule,run_due_schedules}`, `tasks.py::run_scheduled_reports` | Rolls up `AFR-PSM-078`..`080`, `082` |
| `CFR-PSM-018` | Real-time authorized P&S dashboards | `selectors/` | `selectors/dashboard.py::dashboard_summary` | Rolls up `AFR-PSM-081` |
| `CFR-PSM-019` | Automated lifecycle/SLA notifications and retained communication history | `services/` + `tasks.py` + `models/` | `services/notifications.py::enqueue`, `tasks.py::deliver_notifications`, `models/reporting.py::PsmNotification` | Rolls up `AFR-PSM-083`..`086` |
| `CFR-PSM-020` | Complete audit trail, internal & statutory audit support, RBAC, policy compliance | `services/` + `selectors/` + `api/` | `services/audit.py::record`, `selectors/scoping.py`, `registry.py`, `domain/approval_policy.py` | Rolls up `AFR-PSM-087`..`092` |

### Atomic Requirements (`AFR-PSM-001` – `AFR-PSM-092`)

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| `AFR-PSM-001` | Authenticated employee creates & submits purchase indent | `services/` + `api/` | `services/indents.py::create_and_submit`, `api/views/indents.py` | `PSM-UC-001` |
| `AFR-PSM-002` | Capture item details, quantity, estimated cost, justification | `models/` + `api/` | `models/indent.py::Indent`, `api/serializers/indents.py` | `BR-PSM-001` |
| `AFR-PSM-003` | Validate mandatory indent fields before submission | `domain/` | `domain/indent_rules.py::validate_indent_completeness` | `BR-PSM-001` |
| `AFR-PSM-004` | Detect potential duplicate indents and flag for review | `domain/` + `services/` | `domain/indent_rules.py::is_potential_duplicate`, `services/indents.py::create_and_submit` | `BR-PSM-015` |
| `AFR-PSM-005` | Assign unique indent identifier to every submitted indent | `models/` + `services/` | `models/indent.py::Indent.indent_number` (unique), `services/indents.py::_next_indent_number` | `PSM-UC-001` |
| `AFR-PSM-006` | Record submission timestamp for every submitted indent | `models/` + `services/` | `models/indent.py::Indent.submitted_at`, `services/indents.py::create_and_submit` | `PSM-UC-001` |
| `AFR-PSM-007` | Log indent creation and subsequent indent actions in audit trail | `services/` | `services/audit.py::record`, `models/indent.py::IndentTransition` | `BR-PSM-021` |
| `AFR-PSM-008` | Employee modifies indent only in permissible state | `domain/` + `services/` | `domain/state_machine.py`, `services/indents.py::modify_indent` | `BR-PSM-007`, `PSM-UC-023` |
| `AFR-PSM-009` | Employee withdraws/cancels indent only in permissible state | `domain/` + `services/` | `domain/state_machine.py`, `services/indents.py::withdraw_indent` | `BR-PSM-007`, `PSM-UC-005` |
| `AFR-PSM-010` | Retain each indent modification as a distinct version | `models/` + `services/` | `models/indent.py::IndentVersion`, `services/indents.py::modify_indent` | `BR-PSM-021` |
| `AFR-PSM-011` | Repeat previous indent as new editable draft | `services/` | `services/indents.py::repeat_as_draft` | `PSM-UC-024` |
| `AFR-PSM-012` | Expose logged indent actions to authorized stakeholders | `selectors/` | `selectors/indents.py::indent_history_for` | `PSM-UC-003`, `BR-PSM-020` |
| `AFR-PSM-013` | Check departmental & central stock before external procurement | `services/` | `services/stock.py::check_and_reserve` | `BR-PSM-003`, `PSM-UC-007` |
| `AFR-PSM-014` | Inform requestor when requested items exist in stock records | `services/` | `services/stock.py::check_and_reserve` -> `notifications.enqueue` | `PSM-UC-001`, `PSM-UC-007` |
| `AFR-PSM-015` | Reserve available stock allocated to an indent before internal issue | `services/` + `models/` | `services/stock.py::check_and_reserve`, `models/stock.py::StockReservation` | `BR-PSM-013` |
| `AFR-PSM-016` | Account for reservations in available stock so stock is not over-committed | `domain/` + `services/` | `domain/stock_rules.py::allocable_quantity`, `services/stock.py::check_and_reserve` (`select_for_update`) | `BR-PSM-013` |
| `AFR-PSM-017` | Dept Admin schedules picking for approved internal issue | `services/` | `services/stock.py::schedule_picking` | `PSM-UC-009` |
| `AFR-PSM-018` | Dept Admin schedules/records dispatch for approved internal issue | `services/` | `services/stock.py::dispatch_internal_issue` | `PSM-UC-009` |
| `AFR-PSM-019` | Requestor acknowledges receipt of internally issued goods | `services/` | `services/receipts.py::confirm_receipt` | `PSM-UC-002` |
| `AFR-PSM-020` | Final stock posting only after delivery confirmation | `domain/` + `services/` | `domain/receipt_rules.py::can_post_stock`, `services/receipts.py::confirm_receipt` | `BR-PSM-009`, `BR-PSM-026` |
| `AFR-PSM-021` | Block final stock posting when receipt has unresolved discrepancy | `domain/` + `services/` | `domain/receipt_rules.py::can_post_stock`, `services/receipts.py::confirm_receipt` | `BR-PSM-009`, `BR-PSM-026` |
| `AFR-PSM-022` | Route indents through configured approval hierarchy by cost thresholds | `domain/` + `services/` | `domain/approval_policy.py::next_approval_stage`, `services/approvals.py` | `BR-PSM-004` |
| `AFR-PSM-023` | Support more direct approval path for higher-priority indents per policy | `domain/` + `services/` | `domain/approval_policy.py::next_approval_stage`, `services/approvals.py::dept_admin_review` | `BR-PSM-004`, `BR-PSM-014` |
| `AFR-PSM-024` | Dept Admin records criticality/priority of an indent | `services/` | `services/approvals.py::dept_admin_review` | `PSM-UC-011`, `BR-PSM-014` |
| `AFR-PSM-025` | Use recorded criticality/priority in SLA notifications & queue ordering | `selectors/` + `domain/` | `selectors/indents.py::approval_queue_for`, `domain/approval_policy.py::evaluate_sla` | `BR-PSM-014` |
| `AFR-PSM-026` | Require justification when any approver rejects an indent | `domain/` + `services/` | `domain/state_machine.py` (`has_reason` guard), `services/approvals.py` | `BR-PSM-005` |
| `AFR-PSM-027` | Issue SLA-based reminders for pending approval actions | `tasks.py` + `services/` | `tasks.py::check_approval_slas`, `services/approvals.py::sweep_slas` | `BR-PSM-014` |
| `AFR-PSM-028` | Issue SLA-based escalation notifications when conditions met | `tasks.py` + `services/` | `tasks.py::check_approval_slas`, `services/approvals.py::sweep_slas` | `BR-PSM-014` |
| `AFR-PSM-029` | Record every approval decision in the audit trail | `services/` | `services/approvals.py` -> `IndentTransition` + `audit.record` | `BR-PSM-021` |
| `AFR-PSM-030` | Route indent for external procurement when sufficient stock unavailable | `services/` | `services/stock.py::check_and_reserve` | `BR-PSM-003` |
| `AFR-PSM-031` | Determine direct vs. tender procurement using configured value thresholds | `domain/` + `services/` | `domain/approval_policy.py::select_procurement_method`, `services/procurement.py::review_and_select_method` | `BR-PSM-008` |
| `AFR-PSM-032` | Publish bids/tender invitations for tender procurements | `services/` | `services/tenders.py::publish_tender` | `PSM-UC-022` |
| `AFR-PSM-033` | Receive and record bids for a tender | `services/` | `services/tenders.py::record_bid` | `PSM-UC-022` |
| `AFR-PSM-034` | Evaluate submitted bids against defined tender criteria | `services/` | `services/tenders.py::evaluate_bids` | `BR-PSM-023`, `PSM-UC-022` |
| `AFR-PSM-035` | Record committee approval of tender selection | `services/` | `services/tenders.py::award_tender` | `BR-PSM-023`, `PSM-UC-022` |
| `AFR-PSM-036` | Retain procurement decisions and supporting records traceably | `models/` + `services/` | `models/tender.py`, `services/tenders.py`, `services/audit.py` | `BR-PSM-021`, `BR-PSM-023` |
| `AFR-PSM-037` | Allow PO creation only after required approvals complete | `domain/` + `services/` | `domain/state_machine.py`, `services/procurement.py::create_and_issue_po` | `BR-PSM-004`, `BR-PSM-010`, `PSM-UC-026` |
| `AFR-PSM-038` | Link each PO to its originating indent | `models/` | `models/procurement.py::PurchaseOrder.indent` (FK) | `PSM-UC-026` |
| `AFR-PSM-039` | Link each PO to the selected vendor | `models/` | `models/procurement.py::PurchaseOrder.vendor` (FK) | `PSM-UC-026` |
| `AFR-PSM-040` | Validate vendor master before PO issuance | `domain/` + `services/` | `domain/vendor_rules.py::ensure_vendor_verified`, `services/procurement.py::create_and_issue_po` | `BR-PSM-012` |
| `AFR-PSM-041` | Track current status of each PO centrally | `models/` + `services/` | `models/procurement.py::PurchaseOrder.status`, `services/procurement.py::update_po_schedule` | `PSM-UC-027` |
| `AFR-PSM-042` | Track planned & actual delivery schedule per PO centrally | `models/` + `services/` | `models/procurement.py::PurchaseOrder.{planned_delivery_date,actual_delivery_date}` | `PSM-UC-027` |
| `AFR-PSM-043` | Allow Requestor, Dept Admin, or Dept Head to record delivery inspection | `api/` + `services/` | `services/receipts.py::record_grn`, `registry.py` (`psm.grn.create`) | `PSM-UC-028` |
| `AFR-PSM-044` | Create GRN for recorded deliveries | `models/` + `services/` | `models/procurement.py::GoodsReceiptNote`, `services/receipts.py::record_grn` | `PSM-UC-028` |
| `AFR-PSM-045` | Support partial receipt against a PO | `domain/` + `services/` | `domain/receipt_rules.py::validate_grn_quantities`, `services/receipts.py::record_grn` | `BR-PSM-022` |
| `AFR-PSM-046` | Support rejection of delivered goods during receipt & inspection | `services/` | `services/receipts.py::record_grn` (`rejected_quantity > 0`) | `PSM-UC-028` |
| `AFR-PSM-047` | Update stock for externally procured goods only after accepted & confirmed receipt | `domain/` + `services/` | `domain/receipt_rules.py::can_post_stock`, `services/receipts.py::confirm_receipt` | `BR-PSM-009`, `BR-PSM-026` |
| `AFR-PSM-048` | Log discrepancy or damage against a delivery | `services/` | `services/discrepancies.py::report_discrepancy` | `PSM-UC-020` |
| `AFR-PSM-049` | Retain evidence attached to a logged discrepancy/damage | `core/files/` + `services/` | `services/discrepancies.py::report_discrepancy` (validated via `core/files/validators.py`) | `PSM-UC-020` |
| `AFR-PSM-050` | Support initiation of return when required by policy | `services/` | `services/discrepancies.py::report_discrepancy` (`requested_resolution="return"`) | `BR-PSM-019` |
| `AFR-PSM-051` | Support initiation of replacement when required by policy | `services/` | `services/discrepancies.py::{report_discrepancy,resolve_case}` | `BR-PSM-019`, `BW-PSM-10` |
| `AFR-PSM-052` | Record vendor communication for discrepancy/return/replacement/warranty | `models/` + `services/` | `models/procurement.py::DiscrepancyCommunication`, `services/discrepancies.py::add_communication` | `PSM-UC-032` |
| `AFR-PSM-053` | Track current status & resolution of discrepancy/return/replacement/warranty case | `models/` + `selectors/` | `models/procurement.py::DiscrepancyCase`, `selectors/procurement.py::discrepancies_for` | `PSM-UC-020`, `PSM-UC-032` |
| `AFR-PSM-054` | Apply inventory adjustments required by resolved discrepancy/return/replacement | `services/` | `services/discrepancies.py::resolve_case`, `services/stock.py::record_adjustment` | `BR-PSM-019`, `PSM-UC-008` |
| `AFR-PSM-055` | Apply accounting adjustments required by resolved discrepancy/return/replacement | `services/` | `services/discrepancies.py::resolve_case` (updates invoice eligible amount / hold) | `BR-PSM-019`, `PSM-UC-032` |
| `AFR-PSM-056` | Support three-way matching of PO, GRN, and Invoice | `domain/` + `services/` | `domain/finance_rules.py::three_way_match`, `services/finance.py::verify_invoice` | `BR-PSM-017`, `PSM-UC-013` |
| `AFR-PSM-057` | Permit payment release only after delivery confirmation & invoice verification | `domain/` + `services/` | `domain/finance_rules.py::can_release_payment`, `services/finance.py::process_payment` | `BR-PSM-009`, `BR-PSM-017` |
| `AFR-PSM-058` | Place mismatched invoice on hold | `domain/` + `services/` | `domain/finance_rules.py::three_way_match`, `services/finance.py::verify_invoice` | `BR-PSM-018` |
| `AFR-PSM-059` | Support partial payments according to configured payment rules | `domain/` + `services/` | `domain/finance_rules.py::payable_amount`, `services/finance.py::process_payment` | `BR-PSM-022` |
| `AFR-PSM-060` | Support onboarding of new vendors | `services/` | `services/vendors.py::onboard_vendor` | `PSM-UC-019` |
| `AFR-PSM-061` | Support maintenance of vendor master data | `services/` | `services/vendors.py::update_vendor` | `PSM-UC-019` |
| `AFR-PSM-062` | Validate GST details, bank details, and compliance documents | `domain/` | `domain/vendor_rules.py::validate_vendor_master` | `BR-PSM-012` |
| `AFR-PSM-063` | Prevent PO issuance to an unverified vendor | `domain/` + `services/` | `domain/vendor_rules.py::ensure_vendor_verified`, `services/procurement.py::create_and_issue_po` | `BR-PSM-012` |
| `AFR-PSM-064` | Prevent payment to an unverified vendor | `domain/` + `services/` | `domain/vendor_rules.py::ensure_vendor_verified`, `services/finance.py::process_payment` | `BR-PSM-012`, `BR-PSM-017` |
| `AFR-PSM-065` | Retain version history for vendor master changes | `models/` + `services/` | `models/vendor.py::VendorVersion`, `services/vendors.py::{onboard_vendor,update_vendor}` | `BR-PSM-025` |
| `AFR-PSM-066` | Record vendor master changes in audit trail | `services/` | `services/vendors.py` -> `audit.record` | `BR-PSM-021`, `BR-PSM-025` |
| `AFR-PSM-067` | Create inter-departmental stock transfer request | `services/` | `services/transfers.py::request_transfer` | `PSM-UC-021` |
| `AFR-PSM-068` | Reserve approved stock for inter-departmental transfer | `services/` | `services/transfers.py::dispatch_transfer` (`StockReservation`) | `BR-PSM-013`, `PSM-UC-033` |
| `AFR-PSM-069` | Dispatch approved inter-departmental stock transfer | `services/` | `services/transfers.py::dispatch_transfer` | `PSM-UC-033` |
| `AFR-PSM-070` | Confirm receipt of inter-departmental stock transfer | `services/` | `services/transfers.py::confirm_transfer` | `PSM-UC-034` |
| `AFR-PSM-071` | Update source stock ledger when transfer completed | `services/` | `services/transfers.py::confirm_transfer` (`transfer_out` ledger entry) | `BR-PSM-027` |
| `AFR-PSM-072` | Update destination stock ledger when transfer completed | `services/` | `services/transfers.py::confirm_transfer` (`transfer_in` ledger entry) | `BR-PSM-027` |
| `AFR-PSM-073` | Retain audit trail for inter-departmental stock transfers | `services/` | `services/transfers.py` -> `audit.record` | `BR-PSM-021`, `BR-PSM-027` |
| `AFR-PSM-074` | Provide operational reports for purchase & stores activities | `services/` | `services/reports.py::generate_report(report_type="operational")` | `PSM-UC-010` |
| `AFR-PSM-075` | Provide procurement reports | `services/` | `services/reports.py::generate_report(report_type="procurement")` | `PSM-UC-010` |
| `AFR-PSM-076` | Provide stock reports | `services/` | `services/reports.py::generate_report(report_type="stock")` | `PSM-UC-010` |
| `AFR-PSM-077` | Provide financial reports related to procurement & payments | `services/` | `services/reports.py::generate_report(report_type="financial")` | `PSM-UC-015` |
| `AFR-PSM-078` | Allow report data to be filtered by supported criteria | `services/` + `selectors/` | `services/reports.py::generate_report` (department, status, date range) | `PSM-UC-010`, `PSM-UC-015` |
| `AFR-PSM-079` | Allow generated reports to be exported (CSV with formula-injection escaping) | `services/` + `api/` | `services/reports.py::export_csv` (prefixes `= + - @ \t \r` with `'`) | `PSM-UC-010`, `PSM-UC-015` |
| `AFR-PSM-080` | Support scheduled report generation | `services/` + `tasks.py` | `services/reports.py::{create_schedule,run_due_schedules}`, `tasks.py::run_scheduled_reports` | `PSM-UC-031`, `PSM-UC-035` |
| `AFR-PSM-081` | Provide dashboards showing real-time process status & key metrics | `selectors/` + `api/` | `selectors/dashboard.py::dashboard_summary`, `api/views/reports.py::DashboardView` | `PSM-UC-030` |
| `AFR-PSM-082` | Log every report generation event | `models/` + `services/` | `models/reporting.py::ReportGenerationLog`, `services/reports.py::generate_report` | `BR-PSM-024` |
| `AFR-PSM-083` | Automated notifications for indent submission & approval events | `services/` | `services/indents.py`, `services/approvals.py` -> `notifications.enqueue` | `BR-PSM-006` |
| `AFR-PSM-084` | Alerts for dispatch, receipt, invoice, and payment status events | `services/` | `services/stock.py`, `services/procurement.py`, `services/receipts.py`, `services/finance.py` -> `notifications.enqueue` | `BR-PSM-006` |
| `AFR-PSM-085` | SLA reminder and escalation notifications | `tasks.py` + `services/` | `tasks.py::check_approval_slas`, `services/approvals.py::sweep_slas` | `BR-PSM-014` |
| `AFR-PSM-086` | Retain communication history generated by the module | `models/` + `selectors/` | `models/reporting.py::PsmNotification`, `selectors/notifications.py` | `BR-PSM-006` |
| `AFR-PSM-087` | Maintain complete audit trail of module actions | `models/` + `services/` | `models/reporting.py::PsmAuditLog`, `services/audit.py::record` | `BR-PSM-021` |
| `AFR-PSM-088` | Support internal audit of P&S records | `selectors/` + `api/` | `selectors/audit.py::audit_records_for`, `api/views/audit.py` | `PSM-UC-014` |
| `AFR-PSM-089` | Support statutory audit of P&S records | `selectors/` + `api/` | `selectors/audit.py::audit_records_for` (audit scope + export) | `PSM-UC-014` |
| `AFR-PSM-090` | Enforce role-based access control for module functions & information | `api/` + `selectors/` + `registry.py` | `HasModuleGrant("psm")` + `HasPermission(...)` + `selectors/scoping.py` | `BR-PSM-020` |
| `AFR-PSM-091` | Enforce applicable procurement-policy constraints via configured rules | `domain/` + `services/` | `domain/approval_policy.py`, `models/policy.py::PsmPolicy` | `BR-PSM-028` |
| `AFR-PSM-092` | Enforce applicable financial-policy constraints via configured rules | `domain/` + `services/` | `domain/finance_rules.py`, `models/policy.py::PsmPolicy` | `BR-PSM-028` |

### Business Rules (`BR-PSM-001` – `BR-PSM-028`, 25 Active)

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| `BR-PSM-001` | Indent completeness (item details, quantity, estimated cost, justification) | `domain/` | `domain/indent_rules.py::validate_indent_completeness` | Also enforces `quantity > 0`, `estimated_cost > 0` |
| `BR-PSM-003` | Departmental & central stock checked before external procurement | `domain/` + `services/` | `services/stock.py::check_and_reserve`, `domain/state_machine.py` | Prevents skipping stock check |
| `BR-PSM-004` | Configurable approval hierarchy by cost thresholds | `domain/` + `services/` | `domain/approval_policy.py::next_approval_stage`, `services/approvals.py` | Driven by active `PsmPolicy` |
| `BR-PSM-005` | Mandatory rejection justification + requestor notification + audit | `domain/` + `services/` | `domain/state_machine.py` (`has_reason`), `services/approvals.py::reject_indent` | Rejects blank reason with 422 |
| `BR-PSM-006` | Lifecycle notifications & retained communication history | `services/` + `models/` | `services/notifications.py::enqueue`, `models/reporting.py::PsmNotification` | Idempotent via `dedupe_key` |
| `BR-PSM-007` | Indent modify/withdraw/cancel only in policy-permissible states; modify creates version & re-reviews | `domain/` + `services/` | `domain/indent_rules.py::can_modify_or_withdraw`, `services/indents.py::{modify_indent,withdraw_indent}` | Configurable state lists in `PsmPolicy` |
| `BR-PSM-008` | Procurement method (direct vs. tender) by configured value threshold | `domain/` + `services/` | `domain/approval_policy.py::select_procurement_method`, `services/procurement.py::review_and_select_method` | Driven by `PsmPolicy.direct_limit` |
| `BR-PSM-009` | Delivery confirmation required before final stock posting & payment; unresolved discrepancy blocks both | `domain/` + `services/` | `domain/receipt_rules.py::can_post_stock`, `domain/finance_rules.py::can_release_payment` | Enforced in both `receipts.py` and `finance.py` |
| `BR-PSM-010` | High-value final-approval routing: PS Admin -> Director/Registrar -> back to PS Admin | `domain/` + `services/` | `domain/approval_policy.py::requires_final_approval`, `services/approvals.py::final_approve` | Driven by `PsmPolicy.final_approval_threshold` |
| `BR-PSM-012` | Vendor master verification gate (GST, bank, compliance docs) before PO or payment | `domain/` + `services/` | `domain/vendor_rules.py::ensure_vendor_verified`, `services/procurement.py`, `services/finance.py` | Blocks unverified vendors with 409 |
| `BR-PSM-013` | Reserved stock excluded from allocable stock; retained until consumed/released | `domain/` + `services/` | `domain/stock_rules.py::allocable_quantity`, `services/stock.py`, `services/transfers.py` | Concurrency locked via `select_for_update` |
| `BR-PSM-014` | SLA reminders, escalations & priority queue ordering (no auto-cancel/auto-reassign) | `domain/` + `tasks.py` + `selectors/` | `domain/approval_policy.py::evaluate_sla`, `tasks.py::check_approval_slas`, `selectors/indents.py` | Idempotent via `sla_reminded_at`/`sla_escalated_at` |
| `BR-PSM-015` | Duplicate indent detection flags likely duplicates for Dept Admin review (no silent merge/cancel) | `domain/` + `services/` | `domain/indent_rules.py::is_potential_duplicate`, `services/indents.py` | Flagged on `Indent.is_duplicate_flagged` |
| `BR-PSM-017` | Payment eligibility: PO + accepted GRN + delivery confirmed + verified invoice + verified vendor | `domain/` + `services/` | `domain/finance_rules.py::can_release_payment`, `services/finance.py::process_payment` | All 5 conditions checked atomically |
| `BR-PSM-018` | Invoice mismatch places invoice on hold and blocks payment until resolved | `domain/` + `services/` | `domain/finance_rules.py::three_way_match`, `services/finance.py::verify_invoice` | Sets `status="on_hold"` with reason |
| `BR-PSM-019` | Resolved return/replacement/warranty triggers policy inventory & accounting adjustments | `services/` | `services/discrepancies.py::resolve_case` | Emits stock adjustment + updates invoice hold |
| `BR-PSM-020` | Role-based access control across all module functions & data | `api/` + `selectors/` + `registry.py` | `HasModuleGrant("psm")` + `HasPermission` + `selectors/scoping.py` | Out-of-scope IDs yield 404 |
| `BR-PSM-021` | Audit trail for all material actions + version history for indents & vendors | `services/` + `models/` | `services/audit.py::record`, `IndentVersion`, `VendorVersion`, `PsmAuditLog` | Append-only |
| `BR-PSM-022` | Partial receipt & partial payment up to verified accepted-GRN proportion | `domain/` + `services/` | `domain/receipt_rules.py`, `domain/finance_rules.py::payable_amount`, `services/finance.py` | Tracks remaining open balance |
| `BR-PSM-023` | Tender bid evaluation against defined criteria & committee approval before PO | `domain/` + `services/` | `services/tenders.py::{evaluate_bids,award_tender}` | Records committee members & minutes |
| `BR-PSM-024` | Report/dashboard authorization and mandatory generation logging (interactive & scheduled) | `services/` + `api/` | `services/reports.py::{generate_report,run_due_schedules}`, `ReportGenerationLog` | Logs succeeded, failed, and blocked runs |
| `BR-PSM-025` | Vendor master versioning on create and every update | `models/` + `services/` | `models/vendor.py::VendorVersion`, `services/vendors.py` | Full prior/new snapshot retained |
| `BR-PSM-026` | Accepted-receipt-only stock posting (rejected/discrepant quantities never posted) | `domain/` + `services/` | `domain/receipt_rules.py::can_post_stock`, `services/receipts.py::confirm_receipt` | Append-only `StockLedgerEntry` |
| `BR-PSM-027` | Stock-transfer dual-ledger posting (source out + destination in) on destination receipt confirmation | `services/` | `services/transfers.py::confirm_transfer` | Atomic pair of `StockLedgerEntry` rows |
| `BR-PSM-028` | Enforce configured procurement & financial policy constraints | `domain/` + `services/` | `services/policy.py::active_policy`, `domain/approval_policy.py`, `domain/finance_rules.py` | Fails clearly if no policy seeded |

### Use Cases (`PSM-UC-001` – `PSM-UC-035`, 32 Active)

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| `PSM-UC-001` | Submit Indent | `services/` + `api/` | `services/indents.py::create_and_submit`, `POST /api/v1/psm/indents` | Employee |
| `PSM-UC-002` | Confirm Delivery Receipt | `services/` + `api/` | `services/receipts.py::confirm_receipt`, `POST /api/v1/psm/grns/{id}/confirm` | Employee (Requestor) |
| `PSM-UC-003` | Track Procurement Status | `selectors/` + `api/` | `selectors/indents.py::indent_detail_for`, `GET /api/v1/psm/indents/{id}` | Employee (own scope) |
| `PSM-UC-005` | Withdraw or Cancel Pending Indent | `services/` + `api/` | `services/indents.py::withdraw_indent`, `POST /api/v1/psm/indents/{id}/withdraw` | Employee (own scope) |
| `PSM-UC-007` | Check and Reserve Stock | `services/` + `api/` | `services/stock.py::check_and_reserve`, `POST /api/v1/psm/indents/{id}/stock-check` | Dept Admin |
| `PSM-UC-008` | Record Authorized Stock Adjustment | `services/` + `api/` | `services/stock.py::record_adjustment`, `POST /api/v1/psm/stock/adjustments` | Dept Admin / PS Admin |
| `PSM-UC-009` | Process Internal Stock Issue | `services/` + `api/` | `services/stock.py::{schedule_picking,dispatch_internal_issue}`, `POST /api/v1/psm/internal-issues/{id}/dispatch` | Dept Admin |
| `PSM-UC-010` | Generate Operational, Procurement and Stock Reports | `services/` + `api/` | `services/reports.py::generate_report`, `POST /api/v1/psm/reports/generate` | Authorized P&S / Dept user |
| `PSM-UC-011` | Review Indent | `services/` + `api/` | `services/approvals.py::dept_admin_review`, `POST /api/v1/psm/indents/{id}/review` | Dept Admin |
| `PSM-UC-012` | Final Review and Approval | `services/` + `api/` | `services/approvals.py::final_approve`, `POST /api/v1/psm/indents/{id}/final-decision` | Director / Registrar |
| `PSM-UC-013` | Verify Invoice | `services/` + `api/` | `services/finance.py::verify_invoice`, `POST /api/v1/psm/invoices/{id}/verify` | Accounts Admin |
| `PSM-UC-014` | Audit Procurement and Financial Records | `selectors/` + `api/` | `selectors/audit.py::audit_records_for`, `GET /api/v1/psm/audit` | Accounts Admin / Auditor |
| `PSM-UC-015` | Generate Financial Reports | `services/` + `api/` | `services/reports.py::generate_report(report_type="financial")`, `POST /api/v1/psm/reports/generate` | Accounts Admin |
| `PSM-UC-016` | Review and Recommend Indent | `services/` + `api/` | `services/approvals.py::hod_recommend`, `POST /api/v1/psm/indents/{id}/recommend` | Department Head |
| `PSM-UC-017` | Check Stock During Department Head Review | `selectors/` + `api/` | `selectors/stock.py::stock_availability_for`, `GET /api/v1/psm/stock/availability` | Department Head (read-only) |
| `PSM-UC-019` | Vendor Onboarding and Master Data Management | `services/` + `api/` | `services/vendors.py::{onboard_vendor,update_vendor,verify_vendor}`, `/api/v1/psm/vendors` | PS Admin |
| `PSM-UC-020` | Report Goods Discrepancy and Initiate Return/Replacement | `services/` + `api/` | `services/discrepancies.py::report_discrepancy`, `POST /api/v1/psm/discrepancies` | Requestor / Dept Admin / Dept Head |
| `PSM-UC-021` | Request Inter-Departmental Stock Transfer | `services/` + `api/` | `services/transfers.py::request_transfer`, `POST /api/v1/psm/transfers` | Requesting Dept Admin |
| `PSM-UC-022` | Tender / Competitive Procurement Management | `services/` + `api/` | `services/tenders.py::{create_tender,publish_tender,record_bid,evaluate_bids,award_tender}`, `/api/v1/psm/tenders` | PS Admin (with committee metadata) |
| `PSM-UC-023` | Modify Pending Indent | `services/` + `api/` | `services/indents.py::modify_indent`, `PATCH /api/v1/psm/indents/{id}` | Employee (own scope) |
| `PSM-UC-024` | Repeat Previous Indent | `services/` + `api/` | `services/indents.py::repeat_as_draft`, `POST /api/v1/psm/indents/{id}/repeat` | Employee (own scope) |
| `PSM-UC-025` | Review Procurement and Select Procurement Method | `services/` + `api/` | `services/procurement.py::review_and_select_method`, `POST /api/v1/psm/indents/{id}/procurement-review` | PS Admin |
| `PSM-UC-026` | Create and Issue Purchase Order | `services/` + `api/` | `services/procurement.py::create_and_issue_po`, `POST /api/v1/psm/purchase-orders` | PS Admin |
| `PSM-UC-027` | Manage PO Status and Delivery Schedule | `services/` + `api/` | `services/procurement.py::update_po_schedule`, `PATCH /api/v1/psm/purchase-orders/{id}` | PS Admin |
| `PSM-UC-028` | Inspect Delivery and Record GRN | `services/` + `api/` | `services/receipts.py::record_grn`, `POST /api/v1/psm/grns` | Requestor / Dept Admin / Dept Head |
| `PSM-UC-029` | Process or Hold Vendor Payment | `services/` + `api/` | `services/finance.py::{process_payment,hold_invoice}`, `POST /api/v1/psm/invoices/{id}/pay` | Accounts Admin |
| `PSM-UC-030` | View P&S Dashboard | `selectors/` + `api/` | `selectors/dashboard.py::dashboard_summary`, `GET /api/v1/psm/dashboard` | Authorized user |
| `PSM-UC-031` | Schedule Reports | `services/` + `api/` | `services/reports.py::create_schedule`, `POST /api/v1/psm/reports/schedules` | Authorized user |
| `PSM-UC-032` | Resolve Return, Replacement or Warranty Case | `services/` + `api/` | `services/discrepancies.py::{add_communication,resolve_case}`, `POST /api/v1/psm/discrepancies/{id}/resolve` | PS Admin |
| `PSM-UC-033` | Process and Dispatch Stock Transfer | `services/` + `api/` | `services/transfers.py::dispatch_transfer`, `POST /api/v1/psm/transfers/{id}/dispatch` | Source Dept Admin / PS Admin |
| `PSM-UC-034` | Confirm Stock Transfer Receipt | `services/` + `api/` | `services/transfers.py::confirm_transfer`, `POST /api/v1/psm/transfers/{id}/confirm` | Destination Dept Admin |
| `PSM-UC-035` | Generate Scheduled Report (Event-triggered) | `tasks.py` + `services/` | `tasks.py::run_scheduled_reports`, `services/reports.py::run_due_schedules` | Celery beat (`psm.report.generate_scheduled`) |

### Workflows (`BW-PSM-01` – `BW-PSM-08`, `BW-PSM-10`, `CW-PSM-01`, `CW-PSM-02`)

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| `BW-PSM-01` | Internal Stock Fulfilment (`UC-001 -> 007 -> 011 -> 009 -> 028 -> 002`) | `domain/` + `services/` | `domain/state_machine.py` (`INDENT_TRANSITIONS`), `services/{indents,stock,approvals,receipts}.py` | Literal GRN step (`UC-028`) before `UC-002` |
| `BW-PSM-02` | External Procurement Authorization - Standard Path (`UC-001 -> 007 -> 011 -> 016 -> 025`) | `domain/` + `services/` | `domain/state_machine.py`, `services/{indents,stock,approvals,procurement}.py` | Below final-approval threshold |
| `BW-PSM-03` | External Procurement Authorization - Final Authority Path (`... -> 025 -> 012`) | `domain/` + `services/` | `domain/state_machine.py`, `services/{procurement,approvals}.py` | Above `final_approval_threshold` |
| `BW-PSM-04` | Direct Procurement to Payment (`UC-026 -> 027 -> 028 -> 002 -> 013 -> 029`) | `domain/` + `services/` | `services/{procurement,receipts,finance}.py` | Direct method (`<= direct_limit`) |
| `BW-PSM-05` | Tender Procurement to Payment (`UC-022 -> 026 -> 027 -> 028 -> 002 -> 013 -> 029`) | `domain/` + `services/` | `services/{tenders,procurement,receipts,finance}.py` | Tender method (`> direct_limit`) |
| `BW-PSM-06` | Discrepancy Resolution - Return/Adjustment Path (`UC-028 -> 020 -> 032 -> 013 -> 029`) | `domain/` + `services/` | `domain/state_machine.py` (`DISCREPANCY_TRANSITIONS`), `services/discrepancies.py` | Zero replacement path |
| `BW-PSM-07` | Modify Pending Indent and Re-review (`UC-023 -> 011 -> 016`) | `domain/` + `services/` | `domain/state_machine.py`, `services/indents.py::modify_indent` | Creates `IndentVersion`, returns to `submitted` |
| `BW-PSM-08` | Inter-Departmental Stock Transfer (`UC-021 -> 033 -> 034`) | `domain/` + `services/` | `domain/state_machine.py` (`TRANSFER_TRANSITIONS`), `services/transfers.py` | Dual ledger update on confirm |
| `BW-PSM-10` | Discrepancy Resolution - One Replacement Traversal (`UC-032 -> 028 -> 002 -> 013 -> 029`) | `domain/` + `services/` | `domain/state_machine.py`, `services/discrepancies.py`, `models/procurement.py` (`replacement_count <= 1`) | Enforces max 1 replacement |
| `CW-PSM-01` | Composite: Indent Fulfilment and Procurement | `domain/` + `services/` | Composes `BW-PSM-01..05`; verified end-to-end in `tests/test_journeys.py` | |
| `CW-PSM-02` | Composite: Receipt, Discrepancy and Payment | `domain/` + `services/` | Composes `BW-PSM-04, 05, 06, 10`; verified end-to-end in `tests/test_journeys.py` | |

---

## (b) Domain Model (`modules/psm/models/`)

All models live in `modules/psm/models/` (one file per aggregate, re-exported in `models/__init__.py`). Every person reference is a plain `IntegerField` (`user_id`, never an FK — ADR-0013). Every index and constraint is explicitly named.

### 1. `models/policy.py`
- **`PsmPolicy(TimeStampedModel)`** — effective-dated, append-only (never edited in place; creating a new active policy supersedes the prior one):
  - `version` (`PositiveIntegerField`, unique), `effective_from` (`DateTimeField`), `is_active` (`BooleanField`, default `True`), `created_by_user_id` (`IntegerField`, nullable for seeded policy)
  - `direct_limit` (`DecimalField(14, 2)` — `<=` direct, `>` tender; default `50000.00`)
  - `final_approval_threshold` (`DecimalField(14, 2)` — `>` requires Director/Registrar; default `100000.00`)
  - `high_priority_direct_allowed` (`BooleanField`, default `True`)
  - `modifiable_states` (`JSONField`, default `["draft", "submitted", "changes_requested", "department_reviewed"]`)
  - `withdrawable_states` (`JSONField`, default `["draft", "submitted", "changes_requested", "department_reviewed"]`)
  - `sla_reminder_hours` (`PositiveIntegerField`, default `24`), `sla_escalation_hours` (`PositiveIntegerField`, default `48`)
  - `high_priority_sla_reminder_hours` (`PositiveIntegerField`, default `12`), `high_priority_sla_escalation_hours` (`PositiveIntegerField`, default `24`)
  - `partial_payment_enabled` (`BooleanField`, default `True`)
  - `duplicate_window_days` (`PositiveIntegerField`, default `14`)
  - **DB Constraints:**
    - `UniqueConstraint(fields=["is_active"], condition=Q(is_active=True), name="psm_policy_single_active")`
    - `CheckConstraint(check=Q(direct_limit__gt=0) & Q(final_approval_threshold__gt=0), name="psm_policy_thresholds_positive")`
    - `CheckConstraint(check=Q(sla_escalation_hours__gt=F("sla_reminder_hours")), name="psm_policy_sla_order")`

### 2. `models/vendor.py`
- **`Vendor(TimeStampedModel)`**:
  - `code` (`CharField(32)`, unique), `name` (`CharField(200)`), `gstin` (`CharField(15)`), `bank_account_number` (`CharField(34)`), `bank_ifsc` (`CharField(11)`), `bank_name` (`CharField(120)`), `compliance_documents` (`JSONField`, list of verified doc labels/keys), `contact_email` (`EmailField`, blank=True), `is_verified` (`BooleanField`, default `False`), `verified_by_user_id` (`IntegerField`, null=True), `verified_at` (`DateTimeField`, null=True), `version` (`PositiveIntegerField`, default `1`), `is_active` (`BooleanField`, default `True`).
  - **DB Constraints & Indexes:**
    - `CheckConstraint(check=~Q(is_verified=True) | Q(verified_at__isnull=False), name="psm_vendor_verified_has_timestamp")`
    - `Index(fields=["is_verified", "name"], name="psm_vendor_verified_name_idx")`
- **`VendorVersion(models.Model)`** — append-only:
  - `vendor` (FK `Vendor`, `CASCADE`), `version` (`PositiveIntegerField`), `snapshot` (`JSONField`), `changed_by_user_id` (`IntegerField`), `change_reason` (`CharField(300)`, blank=True), `created_at` (`DateTimeField`, auto_now_add=True).
  - `UniqueConstraint(fields=["vendor", "version"], name="psm_vendor_version_unique")`

### 3. `models/stock.py`
- **`StockItem(TimeStampedModel)`**: `sku` (`CharField(40)`, unique), `name` (`CharField(200)`), `category` (`CharField(80)`), `unit` (`CharField(32)`, default `"unit"`), `description` (`TextField`, blank=True), `is_active` (`BooleanField`, default `True`).
- **`StockLocation(TimeStampedModel)`**: `code` (`CharField(32)`, unique), `name` (`CharField(120)`), `department` (`CharField(64)`, db_index=True — `"CENTRAL"` for central stores or department acronym e.g. `"CSE"`), `is_central` (`BooleanField`, default `False`).
- **`StockLedgerEntry(models.Model)`** — **append-only ledger (§2.7)**, never updated or deleted:
  - `item` (FK `StockItem`, `PROTECT`), `location` (FK `StockLocation`, `PROTECT`), `entry_type` (`CharField(24)`: `opening`, `receipt_post`, `internal_issue_post`, `transfer_out`, `transfer_in`, `adjustment`), `quantity_delta` (`IntegerField` — non-zero), `source_ref_type` (`CharField(32)`), `source_ref_id` (`IntegerField`, null=True), `reason` (`CharField(300)`), `actor_user_id` (`IntegerField`), `created_at` (`DateTimeField`, auto_now_add=True).
  - **DB Constraints & Indexes:**
    - `CheckConstraint(check=~Q(quantity_delta=0), name="psm_ledger_nonzero_delta")`
    - `Index(fields=["item", "location", "-created_at"], name="psm_ledger_item_loc_idx")`
- **`StockReservation(TimeStampedModel)`**:
  - `item` (FK `StockItem`, `PROTECT`), `location` (FK `StockLocation`, `PROTECT`), `quantity` (`PositiveIntegerField`), `purpose` (`CharField(24)`: `internal_issue`, `stock_transfer`), `indent_id` (`IntegerField`, null=True), `transfer_id` (`IntegerField`, null=True), `status` (`CharField(16)`: `active`, `consumed`, `released`), `reserved_by_user_id` (`IntegerField`), `released_at` (`DateTimeField`, null=True).
  - **DB Constraints & Indexes:**
    - `CheckConstraint(check=Q(quantity__gt=0), name="psm_reservation_qty_positive")`
    - `Index(fields=["item", "location", "status"], name="psm_reservation_active_idx")`
- **`StockTransfer(TimeStampedModel)`**:
  - `transfer_number` (`CharField(32)`, unique), `item` (FK `StockItem`, `PROTECT`), `source_location` (FK `StockLocation`, `PROTECT`, related_name=`"outgoing_transfers"`), `destination_location` (FK `StockLocation`, `PROTECT`, related_name=`"incoming_transfers"`), `quantity` (`PositiveIntegerField`), `status` (`CharField(16)`: `requested`, `dispatched`, `completed`, `cancelled`), `reservation` (FK `StockReservation`, `PROTECT`, null=True), `requested_by_user_id` (`IntegerField`), `dispatched_by_user_id` (`IntegerField`, null=True), `confirmed_by_user_id` (`IntegerField`, null=True), `dispatched_at` (`DateTimeField`, null=True), `confirmed_at` (`DateTimeField`, null=True), `notes` (`TextField`, blank=True).
  - **DB Constraints & Indexes:**
    - `CheckConstraint(check=~Q(source_location=F("destination_location")), name="psm_transfer_distinct_locs")`
    - `CheckConstraint(check=Q(quantity__gt=0), name="psm_transfer_qty_positive")`
    - `Index(fields=["status", "-created_at"], name="psm_transfer_status_idx")`

### 4. `models/indent.py`
- **`Indent(TimeStampedModel, UserScopedModel)`** (`user_id` = requestor):
  - `indent_number` (`CharField(32)`, unique, null=True while draft), `department` (`CharField(64)`), `item` (FK `StockItem`, `PROTECT`, null=True), `item_description` (`CharField(300)`), `quantity` (`PositiveIntegerField`), `estimated_cost` (`DecimalField(14, 2)`), `justification` (`TextField`), `priority` (`CharField(16)`: `normal`, `high`, `critical`, default `normal`), `status` (`CharField(32)`), `procurement_method` (`CharField(16)`: `""`, `internal`, `direct`, `tender`), `is_duplicate_flagged` (`BooleanField`, default `False`), `duplicate_of_indent_id` (`IntegerField`, null=True), `duplicate_reviewed` (`BooleanField`, default `False`), `version` (`PositiveIntegerField`, default `1`), `submitted_at` (`DateTimeField`, null=True), `current_stage_since` (`DateTimeField`, null=True), `sla_reminded_at` (`DateTimeField`, null=True), `sla_escalated_at` (`DateTimeField`, null=True), `repeated_from_indent_id` (`IntegerField`, null=True), `rejection_reason` (`TextField`, blank=True), `policy` (FK `PsmPolicy`, `PROTECT`, null=True).
  - **DB Constraints & Indexes:**
    - `CheckConstraint(check=Q(quantity__gt=0) & Q(estimated_cost__gt=0), name="psm_indent_qty_cost_positive")`
    - `Index(fields=["department", "status", "-created_at"], name="psm_indent_dept_status_idx")`
    - `Index(fields=["user_id", "-created_at"], name="psm_indent_user_recent_idx")`
    - `Index(fields=["status", "priority", "current_stage_since"], name="psm_indent_queue_sla_idx")`
- **`IndentVersion(models.Model)`** — append-only:
  - `indent` (FK `Indent`, `CASCADE`), `version` (`PositiveIntegerField`), `snapshot` (`JSONField`), `actor_user_id` (`IntegerField`), `created_at` (`DateTimeField`, auto_now_add=True).
  - `UniqueConstraint(fields=["indent", "version"], name="psm_indent_version_unique")`
- **`IndentTransition(models.Model)`** — append-only:
  - `indent` (FK `Indent`, `CASCADE`), `from_status` (`CharField(32)`), `to_status` (`CharField(32)`), `actor_user_id` (`IntegerField`, null=True), `actor_role` (`CharField(64)`, blank=True), `reason` (`CharField(500)`, blank=True), `created_at` (`DateTimeField`, auto_now_add=True).
  - `Index(fields=["indent", "-created_at"], name="psm_indent_trans_idx")`
- **`InternalIssue(TimeStampedModel)`**:
  - `indent` (`OneToOneField(Indent, on_delete=PROTECT)`), `location` (FK `StockLocation`, `PROTECT`), `reservation` (FK `StockReservation`, `PROTECT`), `picking_scheduled_at` (`DateTimeField`, null=True), `dispatch_scheduled_at` (`DateTimeField`, null=True), `dispatched_at` (`DateTimeField`, null=True), `dispatched_by_user_id` (`IntegerField`, null=True), `status` (`CharField(24)`: `approved`, `picking_scheduled`, `dispatched`, `grn_recorded`, `completed`).

### 5. `models/tender.py`
- **`Tender(TimeStampedModel)`**:
  - `tender_number` (`CharField(32)`, unique), `indent` (FK `Indent`, `PROTECT`), `title` (`CharField(200)`), `scope` (`TextField`), `evaluation_criteria` (`TextField`), `submission_deadline` (`DateTimeField`), `status` (`CharField(20)`: `draft`, `published`, `evaluated`, `awarded`, `cancelled`), `published_at` (`DateTimeField`, null=True), `committee_members` (`JSONField`, default `list`), `committee_minutes` (`TextField`, blank=True), `awarded_vendor` (FK `Vendor`, `PROTECT`, null=True), `awarded_by_user_id` (`IntegerField`, null=True), `awarded_at` (`DateTimeField`, null=True), `created_by_user_id` (`IntegerField`).
  - `Index(fields=["status", "-created_at"], name="psm_tender_status_idx")`
- **`TenderBid(TimeStampedModel)`**:
  - `tender` (FK `Tender`, `CASCADE`), `vendor` (FK `Vendor`, `PROTECT`), `quoted_amount` (`DecimalField(14, 2)`), `technical_score` (`DecimalField(6, 2)`, null=True), `financial_score` (`DecimalField(6, 2)`, null=True), `evaluation_notes` (`TextField`, blank=True), `is_selected` (`BooleanField`, default `False`), `submitted_at` (`DateTimeField`, auto_now_add=True), `recorded_by_user_id` (`IntegerField`).
  - `UniqueConstraint(fields=["tender", "vendor"], name="psm_tender_bid_unique_vendor")`
  - `CheckConstraint(check=Q(quoted_amount__gt=0), name="psm_tender_bid_amount_positive")`

### 6. `models/procurement.py`
- **`PurchaseOrder(TimeStampedModel)`**:
  - `po_number` (`CharField(32)`, unique), `indent` (FK `Indent`, `PROTECT`), `vendor` (FK `Vendor`, `PROTECT`), `tender` (FK `Tender`, `PROTECT`, null=True), `ordered_quantity` (`PositiveIntegerField`), `unit_price` (`DecimalField(14, 2)`), `total_amount` (`DecimalField(14, 2)`), `status` (`CharField(24)`: `issued`, `in_transit`, `partially_delivered`, `delivered`, `closed`, `cancelled`), `planned_delivery_date` (`DateField`), `actual_delivery_date` (`DateField`, null=True), `delivery_notes` (`TextField`, blank=True), `issued_by_user_id` (`IntegerField`), `issued_at` (`DateTimeField`, auto_now_add=True).
  - `CheckConstraint(check=Q(ordered_quantity__gt=0) & Q(unit_price__gt=0) & Q(total_amount__gt=0), name="psm_po_amounts_positive")`
  - `Index(fields=["status", "-created_at"], name="psm_po_status_idx")`
- **`GoodsReceiptNote(TimeStampedModel)`**:
  - `grn_number` (`CharField(32)`, unique), `purchase_order` (FK `PurchaseOrder`, `PROTECT`, null=True), `internal_issue` (FK `InternalIssue`, `PROTECT`, null=True), `replacement_for_case` (FK `DiscrepancyCase`, `PROTECT`, null=True), `inspected_by_user_id` (`IntegerField`), `received_quantity` (`PositiveIntegerField`), `accepted_quantity` (`PositiveIntegerField`), `rejected_quantity` (`PositiveIntegerField`, default `0`), `inspection_notes` (`TextField`, blank=True), `status` (`CharField(20)`: `accepted`, `partial`, `rejected`, `confirmed`), `confirmed_by_user_id` (`IntegerField`, null=True), `confirmed_at` (`DateTimeField`, null=True), `stock_posted` (`BooleanField`, default `False`), `stock_posted_at` (`DateTimeField`, null=True).
  - **DB Constraints:**
    - `CheckConstraint(check=(Q(purchase_order__isnull=False, internal_issue__isnull=True) | Q(purchase_order__isnull=True, internal_issue__isnull=False)), name="psm_grn_single_source")`
    - `CheckConstraint(check=Q(received_quantity__gt=0), name="psm_grn_received_positive")`
    - `CheckConstraint(check=Q(received_quantity=F("accepted_quantity") + F("rejected_quantity")), name="psm_grn_qty_balance")`
- **`DiscrepancyCase(TimeStampedModel)`**:
  - `case_number` (`CharField(32)`, unique), `grn` (FK `GoodsReceiptNote`, `PROTECT`), `reported_by_user_id` (`IntegerField`), `discrepancy_type` (`CharField(24)`: `damage`, `shortage`, `wrong_item`, `quality_defect`), `affected_quantity` (`PositiveIntegerField`), `description` (`TextField`), `evidence_file_key` (`CharField(255)`, blank=True), `evidence_filename` (`CharField(255)`, blank=True), `requested_resolution` (`CharField(24)`: `return`, `replacement`, `warranty`, `adjustment`), `status` (`CharField(24)`: `open`, `replacement_awaited`, `resolved`, `closed`), `replacement_count` (`PositiveSmallIntegerField`, default `0`), `resolution_notes` (`TextField`, blank=True), `inventory_adjusted` (`BooleanField`, default `False`), `accounting_adjusted` (`BooleanField`, default `False`), `resolved_by_user_id` (`IntegerField`, null=True), `resolved_at` (`DateTimeField`, null=True).
  - `CheckConstraint(check=Q(affected_quantity__gt=0) & Q(replacement_count__lte=1), name="psm_discrepancy_bounds")`
  - `Index(fields=["status", "-created_at"], name="psm_discrepancy_status_idx")`
- **`DiscrepancyCommunication(models.Model)`** — append-only:
  - `case` (FK `DiscrepancyCase`, `CASCADE`), `sender_label` (`CharField(120)`), `message` (`TextField`), `recorded_by_user_id` (`IntegerField`), `created_at` (`DateTimeField`, auto_now_add=True).

### 7. `models/finance.py`
- **`Invoice(TimeStampedModel)`**:
  - `invoice_number` (`CharField(64)`), `purchase_order` (FK `PurchaseOrder`, `PROTECT`), `vendor` (FK `Vendor`, `PROTECT`), `billed_quantity` (`PositiveIntegerField`), `billed_amount` (`DecimalField(14, 2)`), `eligible_amount` (`DecimalField(14, 2)`, default `0.00`), `status` (`CharField(20)`: `submitted`, `verified`, `on_hold`, `partially_paid`, `paid`), `hold_reason` (`TextField`, blank=True), `verified_by_user_id` (`IntegerField`, null=True), `verified_at` (`DateTimeField`, null=True), `submitted_by_user_id` (`IntegerField`).
  - `UniqueConstraint(fields=["vendor", "invoice_number"], name="psm_invoice_vendor_number_unique")`
  - `CheckConstraint(check=Q(billed_quantity__gt=0) & Q(billed_amount__gt=0), name="psm_invoice_amounts_positive")`
  - `Index(fields=["status", "-created_at"], name="psm_invoice_status_idx")`
- **`PaymentTransaction(models.Model)`** — **append-only ledger (§2.7)**:
  - `invoice` (FK `Invoice`, `PROTECT`), `vendor` (FK `Vendor`, `PROTECT`), `amount` (`DecimalField(14, 2)`), `payment_reference` (`CharField(64)`, unique), `is_partial` (`BooleanField`, default `False`), `status` (`CharField(16)`: `released`, `reversed`), `processed_by_user_id` (`IntegerField`), `notes` (`TextField`, blank=True), `created_at` (`DateTimeField`, auto_now_add=True).
  - `CheckConstraint(check=Q(amount__gt=0), name="psm_payment_amount_positive")`
  - `Index(fields=["invoice", "-created_at"], name="psm_payment_invoice_idx")`

### 8. `models/reporting.py`
- **`ReportSchedule(TimeStampedModel)`**: `name` (`CharField(160)`), `report_type` (`CharField(20)`: `operational`, `procurement`, `stock`, `financial`), `filters` (`JSONField`, default `dict`), `cadence` (`CharField(16)`: `daily`, `weekly`, `monthly`), `is_active` (`BooleanField`, default `True`), `created_by_user_id` (`IntegerField`), `created_by_role` (`CharField(64)`), `last_run_at` (`DateTimeField`, null=True), `next_run_at` (`DateTimeField`).
- **`ReportGenerationLog(models.Model)`** — append-only: `report_type` (`CharField(20)`), `trigger_type` (`CharField(16)`: `interactive`, `scheduled`), `schedule` (FK `ReportSchedule`, `SET_NULL`, null=True), `filters` (`JSONField`, default `dict`), `export_format` (`CharField(16)`: `json`, `csv`), `row_count` (`PositiveIntegerField`, default `0`), `status` (`CharField(16)`: `succeeded`, `failed`, `blocked`), `actor_user_id` (`IntegerField`, null=True), `error_message` (`TextField`, blank=True), `created_at` (`DateTimeField`, auto_now_add=True).
- **`PsmNotification(models.Model)`** — append-only communication history: `topic` (`CharField(64)`), `dedupe_key` (`CharField(160)`, unique), `recipient_user_id` (`IntegerField`, db_index=True), `subject` (`CharField(200)`), `body` (`TextField`), `payload` (`JSONField`, default `dict`), `status` (`CharField(16)`: `pending`, `sent`, `failed`), `sent_at` (`DateTimeField`, null=True), `created_at` (`DateTimeField`, auto_now_add=True).
- **`PsmAuditLog(models.Model)`** — append-only audit trail: `actor_user_id` (`IntegerField`, null=True), `actor_role` (`CharField(64)`, blank=True), `action` (`CharField(64)`), `target_type` (`CharField(40)`), `target_id` (`IntegerField`), `from_state` (`CharField(32)`, blank=True), `to_state` (`CharField(32)`, blank=True), `details` (`JSONField`, default `dict`), `created_at` (`DateTimeField`, auto_now_add=True).
  - `Index(fields=["target_type", "target_id", "-created_at"], name="psm_audit_target_idx")`
  - `Index(fields=["-created_at"], name="psm_audit_recent_idx")`

---

## (c) State Machines (`modules/psm/domain/state_machine.py`)

Declarative transition tables — pure Python, zero Django imports. Every write service resolves transitions through `resolve(table, from_state, to_state, actor_lane)` inside `transaction.atomic()` + `select_for_update()`.

### 1. Indent Lifecycle (`INDENT_TRANSITIONS`)

| From State | Event / Action | Actor Lane | Permission | Guards | To State |
|---|---|---|---|---|---|
| `draft` | Submit (`PSM-UC-001`) | `employee` | `psm.indent.create` | `indent_complete` | `submitted` |
| `submitted` | Stock sufficient (`PSM-UC-007`) | `dept_admin` | `psm.stock.update` | `stock_available` | `stock_reserved` |
| `submitted` | Stock insufficient (`PSM-UC-007`) | `dept_admin` | `psm.stock.update` | `stock_insufficient` | `external_required` |
| `stock_reserved` | Approve internal issue (`PSM-UC-011`) | `dept_admin` | `psm.indent.review` | `not_self_actor` | `internal_approved` |
| `stock_reserved` | Reject (`PSM-UC-011`) | `dept_admin` | `psm.indent.review` | `has_reason`, `not_self_actor` | `rejected` |
| `internal_approved` | Dispatch internal issue (`PSM-UC-009`) | `dept_admin` | `psm.stock.update` | `reservation_active` | `dispatched` |
| `dispatched` | Record GRN (`PSM-UC-028`) | `receiving_actor` | `psm.grn.create` | `grn_accepted_or_partial` | `grn_recorded` |
| `grn_recorded` | Confirm receipt (`PSM-UC-002`) | `employee` | `psm.grn.approve` | `no_open_discrepancy` | `fulfilled` |
| `external_required` | Approve for review (`PSM-UC-011`) | `dept_admin` | `psm.indent.review` | `not_self_actor` | `department_reviewed` |
| `external_required` | Reject (`PSM-UC-011`) | `dept_admin` | `psm.indent.review` | `has_reason`, `not_self_actor` | `rejected` |
| `department_reviewed` | Recommend onward (`PSM-UC-016`) | `dept_head` | `psm.indent.approve` | `not_self_actor` | `hod_recommended` |
| `department_reviewed` | Recommend changes (`PSM-UC-016`) | `dept_head` | `psm.indent.approve` | `has_reason`, `not_self_actor` | `changes_requested` |
| `department_reviewed` | Reject (`PSM-UC-016`) | `dept_head` | `psm.indent.approve` | `has_reason`, `not_self_actor` | `rejected` |
| `department_reviewed` | Direct high-priority review (`PSM-UC-025`, `BR-PSM-004`/`014`) | `ps_admin` | `psm.procurement.review` | `high_priority_direct_permitted`, `not_self_actor` | `procurement_authorized` |
| `hod_recommended` | Authorize (no final approval needed, `PSM-UC-025`) | `ps_admin` | `psm.procurement.review` | `final_approval_not_required`, `not_self_actor` | `procurement_authorized` |
| `hod_recommended` | Route to Director/Registrar (`PSM-UC-025`, `BR-PSM-010`) | `ps_admin` | `psm.procurement.review` | `final_approval_required`, `not_self_actor` | `awaiting_final_approval` |
| `awaiting_final_approval` | Final approve (`PSM-UC-012`) | `final_authority` | `psm.procurement.approve` | `not_self_actor` | `procurement_authorized` |
| `awaiting_final_approval` | Final reject (`PSM-UC-012`) | `final_authority` | `psm.procurement.approve` | `has_reason`, `not_self_actor` | `rejected` |
| `procurement_authorized` | Tender awarded (`PSM-UC-022`) | `ps_admin` | `psm.tender.approve` | `tender_method` | `tender_awarded` |
| `procurement_authorized` | Issue Direct PO (`PSM-UC-026`) | `ps_admin` | `psm.purchase_order.create` | `direct_method`, `vendor_verified` | `po_issued` |
| `tender_awarded` | Issue Tender PO (`PSM-UC-026`) | `ps_admin` | `psm.purchase_order.create` | `vendor_verified` | `po_issued` |
| `po_issued` | Receipt confirmed & closed (`PSM-UC-002`/`029`) | `employee` / `accounts` | `psm.grn.approve` | `all_qty_confirmed` | `fulfilled` |
| `draft`, `submitted`, `changes_requested`, `department_reviewed` | Modify & resubmit (`PSM-UC-023`, `BW-PSM-07`) | `employee` | `psm.indent.update` | `state_in_policy_modifiable`, `indent_complete` | `submitted` |
| `draft`, `submitted`, `changes_requested`, `department_reviewed` | Withdraw / Cancel (`PSM-UC-005`) | `employee` | `psm.indent.delete` | `state_in_policy_withdrawable` | `withdrawn` |

Terminal states: `fulfilled`, `rejected`, `withdrawn` (zero outgoing transitions).

### 2. Stock Transfer Lifecycle (`TRANSFER_TRANSITIONS`, `BW-PSM-08`)
- `requested` → `dispatched` (`dept_admin`/`ps_admin`, `psm.transfer.update`, guard: `source_stock_available`)
- `dispatched` → `completed` (`dest_dept_admin`, `psm.transfer.approve`, posts `transfer_out` + `transfer_in` ledger entries)
- `requested` → `cancelled` (`dept_admin`, `psm.transfer.delete`, releases any reservation)
- Terminal: `completed`, `cancelled`.

### 3. Discrepancy Case Lifecycle (`DISCREPANCY_TRANSITIONS`, `BW-PSM-06` & `BW-PSM-10`)
- `open` → `resolved` (`ps_admin`, `psm.discrepancy.update`, return/adjustment/warranty path — `BW-PSM-06`)
- `open` → `replacement_awaited` (`ps_admin`, `psm.discrepancy.update`, guard: `replacement_count_zero` — `BW-PSM-10`)
- `replacement_awaited` → `resolved` (`receiving_actor`/`ps_admin`, `psm.grn.create` / `psm.discrepancy.update`, replacement GRN accepted & confirmed)
- `resolved` → `closed` (`ps_admin`/`accounts`, `psm.discrepancy.update`, adjustments posted)
- Terminal: `closed`.

### 4. Invoice Lifecycle (`INVOICE_TRANSITIONS`, `CW-PSM-02`)
- `submitted` → `verified` (`accounts`, `psm.invoice.review`, guard: `three_way_match_passed`)
- `submitted` → `on_hold` (`accounts`, `psm.invoice.review`, guard: `has_reason` — `BR-PSM-018`)
- `on_hold` → `verified` (`accounts`, `psm.invoice.review`, guard: `three_way_match_passed`, `no_open_discrepancy`)
- `verified` → `partially_paid` (`accounts`, `psm.payment.approve`, guard: `vendor_verified`, `partial_payment_allowed`)
- `verified` → `paid` (`accounts`, `psm.payment.approve`, guard: `vendor_verified`, `full_amount_paid`)
- `partially_paid` → `partially_paid` / `paid` (`accounts`, `psm.payment.approve`, guard: `vendor_verified`, `within_eligible_balance`)
- Terminal: `paid`.

---

## (d) Permission List (`modules/psm/registry.py`)

All permission codes follow `psm.<singular_noun>.<verb>` with verbs strictly from the closed vocabulary in `docs/02-iam/rbac-model.md`. Designation names are copied verbatim from `globals_designation`.

```python
MODULE = {
    "code": "psm",
    "label": "Procurement & Stores",
    "icon": "ShoppingCart",
    "base_path": "/psm",
    "nav_section": "Administration",
    "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "psm.dashboard", "label": "Dashboard", "icon": "Gauge",
     "to": "/psm/dashboard", "required_permission": "psm.dashboard.view", "sort_order": 5},
    {"code": "psm.indents", "label": "Indents", "icon": "ClipboardText",
     "to": "/psm/indents", "required_permission": "psm.indent.view", "sort_order": 10},
    {"code": "psm.stock", "label": "Stock & Issues", "icon": "Warehouse",
     "to": "/psm/stock", "required_permission": "psm.stock.view", "sort_order": 20},
    {"code": "psm.transfers", "label": "Stock Transfers", "icon": "ArrowsLeftRight",
     "to": "/psm/transfers", "required_permission": "psm.transfer.view", "sort_order": 25},
    {"code": "psm.vendors", "label": "Vendors", "icon": "Storefront",
     "to": "/psm/vendors", "required_permission": "psm.vendor.view", "sort_order": 30},
    {"code": "psm.tenders", "label": "Tenders", "icon": "Gavel",
     "to": "/psm/tenders", "required_permission": "psm.tender.view", "sort_order": 35},
    {"code": "psm.purchase_orders", "label": "Purchase Orders", "icon": "FileText",
     "to": "/psm/purchase-orders", "required_permission": "psm.purchase_order.view", "sort_order": 40},
    {"code": "psm.grns", "label": "Receipts & Discrepancies", "icon": "Package",
     "to": "/psm/receipts", "required_permission": "psm.grn.view", "sort_order": 45},
    {"code": "psm.invoices", "label": "Invoices & Payments", "icon": "Receipt",
     "to": "/psm/invoices", "required_permission": "psm.invoice.view", "sort_order": 50},
    {"code": "psm.reports", "label": "Reports", "icon": "ChartBar",
     "to": "/psm/reports", "required_permission": "psm.report.view", "sort_order": 60},
    {"code": "psm.audit", "label": "Audit Trail", "icon": "ShieldCheck",
     "to": "/psm/audit", "required_permission": "psm.audit.view", "sort_order": 70},
    {"code": "psm.policy", "label": "Policy", "icon": "Sliders",
     "to": "/psm/policy", "required_permission": "psm.policy.view", "sort_order": 80},
]

PERMISSIONS = [
    ("psm.dashboard.view", "View Procurement & Stores dashboard"),
    ("psm.indent.view", "View indents within authorized scope"),
    ("psm.indent.create", "Create, submit, and repeat purchase indents"),
    ("psm.indent.update", "Modify own pending indents in permissible states"),
    ("psm.indent.delete", "Withdraw or cancel own pending indents"),
    ("psm.indent.review", "Review indents, set priority, and approve internal issue"),
    ("psm.indent.approve", "Recommend, request changes on, or reject departmental indents"),
    ("psm.stock.view", "View departmental and central stock availability"),
    ("psm.stock.update", "Reserve stock, dispatch internal issues, and post adjustments"),
    ("psm.transfer.view", "View inter-departmental stock transfers"),
    ("psm.transfer.create", "Request an inter-departmental stock transfer"),
    ("psm.transfer.update", "Reserve and dispatch an outgoing stock transfer"),
    ("psm.transfer.approve", "Confirm receipt of an incoming stock transfer"),
    ("psm.transfer.delete", "Cancel a pending stock transfer request"),
    ("psm.vendor.view", "View vendor master records and version history"),
    ("psm.vendor.create", "Onboard new vendors"),
    ("psm.vendor.update", "Update vendor master data and verification status"),
    ("psm.procurement.review", "Review external procurements and select procurement method"),
    ("psm.procurement.approve", "Grant final Director/Registrar approval on high-value indents"),
    ("psm.tender.view", "View tenders and recorded bids"),
    ("psm.tender.create", "Create tenders and record vendor bids"),
    ("psm.tender.publish", "Publish tender invitations"),
    ("psm.tender.approve", "Record bid evaluations and committee tender award"),
    ("psm.purchase_order.view", "View purchase orders and delivery schedules"),
    ("psm.purchase_order.create", "Create and issue purchase orders"),
    ("psm.purchase_order.update", "Update purchase order status and delivery schedules"),
    ("psm.grn.view", "View goods receipt notes and delivery discrepancies"),
    ("psm.grn.create", "Inspect deliveries, record GRNs, and report discrepancies"),
    ("psm.grn.approve", "Confirm delivery receipt and trigger final stock posting"),
    ("psm.discrepancy.update", "Record vendor communications and resolve discrepancy cases"),
    ("psm.invoice.view", "View vendor invoices and payment status"),
    ("psm.invoice.create", "Record vendor invoices against purchase orders"),
    ("psm.invoice.review", "Perform three-way invoice matching and place/release holds"),
    ("psm.payment.approve", "Process and release eligible vendor payments"),
    ("psm.report.view", "Generate and view operational, procurement, and stock reports"),
    ("psm.report.export", "Export reports and audit extracts"),
    ("psm.report.create", "Create and manage scheduled report definitions"),
    ("psm.financial_report.view", "Generate and view financial procurement reports"),
    ("psm.audit.view", "Access internal and statutory audit records"),
    ("psm.policy.view", "View active and historical PSM policy versions"),
    ("psm.policy.create", "Publish a new effective-dated PSM policy version"),
    ("psm.sla.review", "System SLA reminder and escalation sweep"),
    ("psm.report.publish", "System scheduled report execution"),
]

SYSTEM_PERMISSIONS = [
    "psm.sla.review",
    "psm.report.publish",
]

SCOPE_PERMISSIONS = []  # Scope is derived from active_role + UserRef.department in selectors/scoping.py

_EMPLOYEE = [
    "psm.dashboard.view",
    "psm.indent.view",
    "psm.indent.create",
    "psm.indent.update",
    "psm.indent.delete",
    "psm.grn.view",
    "psm.grn.create",
    "psm.grn.approve",
]

_DEPT_ADMIN = [
    *_EMPLOYEE,
    "psm.indent.review",
    "psm.stock.view",
    "psm.stock.update",
    "psm.transfer.view",
    "psm.transfer.create",
    "psm.transfer.update",
    "psm.transfer.approve",
    "psm.transfer.delete",
    "psm.report.view",
    "psm.report.export",
    "psm.report.create",
]

_HOD = [
    *_EMPLOYEE,
    "psm.indent.approve",
    "psm.stock.view",
    "psm.report.view",
]

_PS_ADMIN = [
    "psm.dashboard.view",
    "psm.indent.view",
    "psm.stock.view",
    "psm.stock.update",
    "psm.transfer.view",
    "psm.transfer.update",
    "psm.vendor.view",
    "psm.vendor.create",
    "psm.vendor.update",
    "psm.procurement.review",
    "psm.tender.view",
    "psm.tender.create",
    "psm.tender.publish",
    "psm.tender.approve",
    "psm.purchase_order.view",
    "psm.purchase_order.create",
    "psm.purchase_order.update",
    "psm.grn.view",
    "psm.discrepancy.update",
    "psm.invoice.view",
    "psm.invoice.create",
    "psm.report.view",
    "psm.report.export",
    "psm.report.create",
    "psm.policy.view",
    "psm.policy.create",
]

_FINAL_AUTHORITY = [
    "psm.dashboard.view",
    "psm.indent.view",
    "psm.procurement.approve",
    "psm.purchase_order.view",
    "psm.report.view",
    "psm.financial_report.view",
    "psm.policy.view",
]

_ACCOUNTS = [
    "psm.dashboard.view",
    "psm.indent.view",
    "psm.vendor.view",
    "psm.purchase_order.view",
    "psm.grn.view",
    "psm.invoice.view",
    "psm.invoice.create",
    "psm.invoice.review",
    "psm.payment.approve",
    "psm.report.view",
    "psm.report.export",
    "psm.report.create",
    "psm.financial_report.view",
    "psm.audit.view",
]

_AUDITOR = [
    "psm.dashboard.view",
    "psm.indent.view",
    "psm.stock.view",
    "psm.transfer.view",
    "psm.vendor.view",
    "psm.tender.view",
    "psm.purchase_order.view",
    "psm.grn.view",
    "psm.invoice.view",
    "psm.report.view",
    "psm.report.export",
    "psm.financial_report.view",
    "psm.audit.view",
    "psm.policy.view",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "dept_admin": _DEPT_ADMIN,
    "deptadmin_cse": _DEPT_ADMIN,
    "deptadmin_design": _DEPT_ADMIN,
    "deptadmin_ece": _DEPT_ADMIN,
    "deptadmin_liberalarts": _DEPT_ADMIN,
    "deptadmin_me": _DEPT_ADMIN,
    "deptadmin_ns": _DEPT_ADMIN,
    "deptadmin_sm": _DEPT_ADMIN,
    "HOD (CSE)": _HOD,
    "HOD (Design)": _HOD,
    "HOD (ECE)": _HOD,
    "HOD (Liberal Arts)": _HOD,
    "HOD (ME)": _HOD,
    "HOD (NS)": _HOD,
    "ps_admin": _PS_ADMIN,
    "SectionHead_PS": _PS_ADMIN,
    "Director": _FINAL_AUTHORITY,
    "Registrar": _FINAL_AUTHORITY,
    "Accounts Admin": _ACCOUNTS,
    "Auditor": _AUDITOR,
}
```
Note: `student` is deliberately NOT in `ROLE_GRANTS` (students do not raise purchase indents or access PSM). Every role in `ROLE_GRANTS` traces directly to Phase 0's actor inventory and exact `globals_designation` spellings.

---

## (e) Endpoint List, Client Routes & `Fusion-client` Sidebar Entry

All endpoints sit behind `[HasModuleGrant("psm"), HasPermission(...)]` (never `AllowAny`) and all write endpoints carry a `throttle_scope` (`psm_write` or `psm_export`).

### API Endpoints (`/api/v1/psm/`)

| Method & Path | Permission Gate (after `HasModuleGrant("psm")`) | Returns | Enforces |
|---|---|---|---|
| `GET /dashboard` | `psm.dashboard.view` | Real-time scoped KPI counts & status breakdown | `PSM-UC-030`, `AFR-PSM-081`, `BR-PSM-020`, `BR-PSM-024` |
| `GET /indents` | `psm.indent.view` | Cursor-paginated scoped indents (priority-ordered for queues) | `PSM-UC-003`, `BR-PSM-014`, `BR-PSM-020` |
| `POST /indents` | `psm.indent.create` | Created & submitted (or draft) indent + duplicate flag | `PSM-UC-001`, `BR-PSM-001`, `BR-PSM-015`, `BR-PSM-021` |
| `GET /indents/{id}` | `psm.indent.view` | Scoped indent detail + versions + transitions + notifications | `PSM-UC-003`, `AFR-PSM-012`, `BR-PSM-020` |
| `PATCH /indents/{id}` | `psm.indent.update` | Updated indent + new `IndentVersion` | `PSM-UC-023`, `BR-PSM-001`, `BR-PSM-007`, `BR-PSM-015` |
| `POST /indents/{id}/withdraw` | `psm.indent.delete` | Withdrawn indent | `PSM-UC-005`, `BR-PSM-007`, `BR-PSM-021` |
| `POST /indents/{id}/repeat` | `psm.indent.create` | New editable draft copied from prior indent | `PSM-UC-024`, `AFR-PSM-011` |
| `POST /indents/{id}/stock-check` | `psm.stock.update` | Stock availability result; reserves if sufficient else marks external | `PSM-UC-007`, `BR-PSM-003`, `BR-PSM-013` |
| `POST /indents/{id}/review` | `psm.indent.review` | Dept Admin decision (approve/reject + priority) | `PSM-UC-011`, `BR-PSM-004`, `BR-PSM-005`, `BR-PSM-014` |
| `POST /indents/{id}/recommend` | `psm.indent.approve` | Dept Head decision (recommend/request_changes/reject) | `PSM-UC-016`, `BR-PSM-004`, `BR-PSM-005` |
| `POST /indents/{id}/procurement-review` | `psm.procurement.review` | PS Admin method selection & routing (authorize or route to final approval) | `PSM-UC-025`, `BR-PSM-008`, `BR-PSM-010` |
| `POST /indents/{id}/final-decision` | `psm.procurement.approve` | Director/Registrar final approve or reject | `PSM-UC-012`, `BR-PSM-005`, `BR-PSM-010` |
| `GET /stock/items` | `psm.stock.view` | Stock catalog items | `PSM-UC-007`, `PSM-UC-017` |
| `POST /stock/items` | `psm.stock.update` | Create stock catalog item / opening balance | `PSM-UC-008` |
| `GET /stock/locations` | `psm.stock.view` | Departmental & central stock locations | `PSM-UC-007`, `PSM-UC-017` |
| `GET /stock/availability` | `psm.stock.view` | Live on-hand, reserved, and allocable stock per item/location | `PSM-UC-007`, `PSM-UC-017`, `BR-PSM-013` |
| `POST /stock/adjustments` | `psm.stock.update` | Append-only authorized stock ledger adjustment | `PSM-UC-008`, `BR-PSM-009`, `BR-PSM-019`, `BR-PSM-026` |
| `GET /internal-issues` | `psm.stock.view` | Scoped internal stock issues | `PSM-UC-009` |
| `POST /internal-issues/{id}/schedule-picking` | `psm.stock.update` | Scheduled picking timestamp | `PSM-UC-009`, `AFR-PSM-017` |
| `POST /internal-issues/{id}/dispatch` | `psm.stock.update` | Dispatched internal issue + requestor notification | `PSM-UC-009`, `AFR-PSM-018`, `BR-PSM-006` |
| `GET /transfers` | `psm.transfer.view` | Scoped inter-departmental stock transfers | `PSM-UC-021`, `BR-PSM-020` |
| `POST /transfers` | `psm.transfer.create` | Created stock transfer request | `PSM-UC-021`, `BR-PSM-013` |
| `POST /transfers/{id}/dispatch` | `psm.transfer.update` | Reserved & dispatched stock transfer | `PSM-UC-033`, `BR-PSM-013`, `BR-PSM-027` |
| `POST /transfers/{id}/confirm` | `psm.transfer.approve` | Completed transfer + source/dest ledger entries | `PSM-UC-034`, `BR-PSM-027` |
| `POST /transfers/{id}/cancel` | `psm.transfer.delete` | Cancelled transfer | `BW-PSM-08` |
| `GET /vendors` | `psm.vendor.view` | Vendor master list | `PSM-UC-019` |
| `POST /vendors` | `psm.vendor.create` | Onboarded vendor + `VendorVersion` v1 | `PSM-UC-019`, `BR-PSM-012`, `BR-PSM-025` |
| `GET /vendors/{id}` | `psm.vendor.view` | Vendor detail + version history | `PSM-UC-019`, `BR-PSM-025` |
| `PATCH /vendors/{id}` | `psm.vendor.update` | Updated vendor + new `VendorVersion` | `PSM-UC-019`, `BR-PSM-012`, `BR-PSM-025` |
| `POST /vendors/{id}/verify` | `psm.vendor.update` | Verified vendor (validates GST, bank, compliance docs) | `PSM-UC-019`, `BR-PSM-012` |
| `GET /tenders` | `psm.tender.view` | Tenders with bids | `PSM-UC-022` |
| `POST /tenders` | `psm.tender.create` | Created draft tender | `PSM-UC-022`, `BR-PSM-008` |
| `POST /tenders/{id}/publish` | `psm.tender.publish` | Published tender | `PSM-UC-022`, `AFR-PSM-032` |
| `POST /tenders/{id}/bids` | `psm.tender.create` | Recorded vendor bid | `PSM-UC-022`, `AFR-PSM-033` |
| `POST /tenders/{id}/evaluate` | `psm.tender.approve` | Recorded bid evaluation scores & notes | `PSM-UC-022`, `BR-PSM-023` |
| `POST /tenders/{id}/award` | `psm.tender.approve` | Committee-approved tender selection | `PSM-UC-022`, `BR-PSM-023` |
| `GET /purchase-orders` | `psm.purchase_order.view` | Scoped purchase orders | `PSM-UC-027` |
| `POST /purchase-orders` | `psm.purchase_order.create` | Issued PO (gates: approved indent + verified vendor) | `PSM-UC-026`, `BR-PSM-012`, `AFR-PSM-037`..`040` |
| `PATCH /purchase-orders/{id}` | `psm.purchase_order.update` | Updated PO status / delivery schedule | `PSM-UC-027`, `BR-PSM-006` |
| `GET /grns` | `psm.grn.view` | Scoped GRNs | `PSM-UC-028` |
| `POST /grns` | `psm.grn.create` | Created GRN (full, partial, or rejected) | `PSM-UC-028`, `BR-PSM-009`, `BR-PSM-022`, `BR-PSM-026` |
| `POST /grns/{id}/confirm` | `psm.grn.approve` | Confirmed delivery receipt + final stock ledger posting | `PSM-UC-002`, `BR-PSM-009`, `BR-PSM-026` |
| `GET /discrepancies` | `psm.grn.view` | Scoped discrepancy cases | `PSM-UC-020`, `AFR-PSM-053` |
| `POST /discrepancies` | `psm.grn.create` | Logged discrepancy case (+ optional validated evidence upload) | `PSM-UC-020`, `BR-PSM-009`, `BR-PSM-019` |
| `POST /discrepancies/{id}/communications` | `psm.discrepancy.update` | Appended vendor communication | `PSM-UC-032`, `AFR-PSM-052` |
| `POST /discrepancies/{id}/resolve` | `psm.discrepancy.update` | Resolved case (return/adjustment or replacement awaited) | `PSM-UC-032`, `BR-PSM-019`, `BW-PSM-06`, `BW-PSM-10` |
| `GET /discrepancies/{id}/evidence` | `psm.grn.view` | Authorized evidence file download (`Content-Disposition: attachment`) | `AFR-PSM-049`, Step 7.7 |
| `GET /invoices` | `psm.invoice.view` | Scoped invoices + payments | `PSM-UC-013`, `PSM-UC-029` |
| `POST /invoices` | `psm.invoice.create` | Recorded vendor invoice against PO | `PSM-UC-013` |
| `POST /invoices/{id}/verify` | `psm.invoice.review` | Three-way match result (`verified` or `on_hold`) | `PSM-UC-013`, `BR-PSM-017`, `BR-PSM-018`, `BR-PSM-022` |
| `POST /invoices/{id}/pay` | `psm.payment.approve` | Released full or partial `PaymentTransaction` | `PSM-UC-029`, `BR-PSM-012`, `BR-PSM-017`, `BR-PSM-022` |
| `POST /invoices/{id}/hold` | `psm.invoice.review` | Placed invoice on hold with reason | `PSM-UC-029`, `BR-PSM-018` |
| `POST /reports/generate` | `psm.report.view` (or `psm.financial_report.view` for financial) | Generated report rows + logged `ReportGenerationLog` | `PSM-UC-010`, `PSM-UC-015`, `BR-PSM-024` |
| `POST /reports/export` | `psm.report.export` | CSV download (formula-escaped) + logged `ReportGenerationLog` | `PSM-UC-010`, `PSM-UC-015`, `AFR-PSM-079`, `BR-PSM-024` |
| `GET /reports/schedules` | `psm.report.view` | Report schedules + generation logs | `PSM-UC-031`, `BR-PSM-024` |
| `POST /reports/schedules` | `psm.report.create` | Created active report schedule | `PSM-UC-031`, `BR-PSM-024` |
| `PATCH /reports/schedules/{id}` | `psm.report.create` | Enable/disable or update schedule | `PSM-UC-031`, `PSM-UC-035` |
| `GET /audit` | `psm.audit.view` | Cursor-paginated `PsmAuditLog` + audit export | `PSM-UC-014`, `AFR-PSM-087`..`089`, `BR-PSM-021` |
| `GET /notifications` | `psm.dashboard.view` | Caller's own retained communication history | `BR-PSM-006`, `AFR-PSM-086` |
| `GET /policy` | `psm.policy.view` | Active policy + historical versions | `BR-PSM-028`, Step 2.8 |
| `POST /policy` | `psm.policy.create` | New effective-dated `PsmPolicy` version | `BR-PSM-028`, Step 2.8 |

### Client Routes (`client/src/modules/psm/routes.tsx`) & Guards

Every route matches `NAV_ITEMS` 1:1 (`nav_matches_routes.py`). Record details and creation forms open in modals/drawers on their list page.

| Path | Component | Route Guard (`RequirePermission`) | Shared / Restricted |
|---|---|---|---|
| `dashboard` | `DashboardPage` | Open to all granted roles (checks `psm.dashboard.view`) | Shared across all PSM roles |
| `indents` | `IndentsPage` | Open to all granted roles (checks `psm.indent.view`, controls gated via `can()`) | Shared; controls gated per permission |
| `stock` | `StockPage` | `RequirePermission("psm.stock.view")` | Dept Admin, HOD, PS Admin, Auditor |
| `transfers` | `TransfersPage` | `RequirePermission("psm.transfer.view")` | Dept Admin, PS Admin, Auditor |
| `vendors` | `VendorsPage` | `RequirePermission("psm.vendor.view")` | PS Admin, Accounts, Auditor |
| `tenders` | `TendersPage` | `RequirePermission("psm.tender.view")` | PS Admin, Auditor |
| `purchase-orders` | `PurchaseOrdersPage` | `RequirePermission("psm.purchase_order.view")` | PS Admin, Director/Registrar, Accounts, Auditor |
| `receipts` | `ReceiptsPage` | Open to all roles with `psm.grn.view` (controls gated via `can()`) | Shared; controls gated per permission |
| `invoices` | `InvoicesPage` | `RequirePermission("psm.invoice.view")` | Accounts, PS Admin, Auditor |
| `reports` | `ReportsPage` | `RequirePermission("psm.report.view")` | Dept Admin, HOD, PS Admin, Director/Registrar, Accounts, Auditor |
| `audit` | `AuditPage` | `RequirePermission("psm.audit.view")` | Accounts, Auditor |
| `policy` | `PolicyPage` | `RequirePermission("psm.policy.view")` | PS Admin, Director/Registrar, Auditor |

### `Fusion-client` Sidebar Entry (for `module-only` Handover)

Add this entry to `INTEGRATED_MODULES` in `Fusion-client/src/ui/nav/navigation.js`:

```js
{
  id: "psm",
  label: "Procurement & Stores",
  icon: "ShoppingCart",
  to: "/psm/dashboard",
  section: "Administration",
}
```

---

## (f) Contracts (`modules/psm/contracts.py`)

### Exposed by `modules/psm/contracts.py` (All Plural)
- `get_indent_summaries(user_ids: Sequence[int]) -> dict[int, IndentSummaryDTO]` — counts of open, fulfilled, and rejected indents per requestor `user_id`.
- `get_pending_receipt_obligations(user_ids: Sequence[int]) -> dict[int, PendingReceiptDTO]` — unconfirmed internal issues / GRNs per `user_id` (useful for clearance/no-dues checks).

### Consumed from Other Modules
- `modules.directory.contracts.get_users(user_ids: Sequence[int])` — batched display names, usernames, and department affiliations for indents, approvals, and audit trails.
- `modules.directory.contracts.search(q, kind, limit)` — employee lookup where needed.
- No new IAM endpoints or `IamClient` methods are required.

---

## (g) Scheduled Work (`modules/psm/schedule.py`)

Registered in `config/celery.py` (`BEAT_SCHEDULE` + `TASK_ROUTES`). Every task is idempotent, `acks_late=True`, and has an `expires` shorter than its cadence.

| Beat Key | Task Name | Queue | Cadence | What breaks if it does not run |
|---|---|---|---|---|
| `psm.check-approval-slas` | `psm.check_approval_slas` | `default` | Every 15 min (`crontab(minute="*/15")`, `expires=800`) | Pending indents past SLA never emit reminder or escalation notifications (`BR-PSM-014`, `AFR-PSM-085`). |
| `psm.run-scheduled-reports` | `psm.run_scheduled_reports` | `reports` | Every 15 min (`crontab(minute="*/15")`, `expires=800`) | Due `ReportSchedule` definitions never execute or write `ReportGenerationLog` (`PSM-UC-035`, `AFR-PSM-080`). |
| `psm.deliver-notifications` | `psm.deliver_notifications` | `notifications` | Every 60 s (`60.0`, `expires=55`) | Queued `PsmNotification` rows stay `pending` instead of being marked delivered (`BR-PSM-006`, `AFR-PSM-083`..`086`). |

---

## (h) Open Questions & Known Operational Prerequisites

1. **`Fusion-client` sidebar entry (`module-only` environment):** Because this workspace is `module-only`, `Fusion-client` is not checked out here. The exact `INTEGRATED_MODULES` entry is documented in Section (e) for handover, and Step 6.6 (framing inside the real portal) is deferred to `full-platform`.
2. **Initial Policy Seeding:** Per §2.8, no policy is hardcoded in business logic. Running `manage.py seed_psm_policy` creates version 1 with the approved defaults. Before policy seeding, `registry.readiness()` reports `"No active PSM policy is configured — run 'manage.py seed_psm_policy'"` and write endpoints refuse cleanly with `409 policy_missing` rather than 500.
3. **Notification Delivery Transport:** As in `modules/placement`, external email/SMS gateways are not configured in dev; `deliver_notifications` marks queued `PsmNotification` rows as `sent` and retains the full communication history (`BR-PSM-006`, `AFR-PSM-086`).
4. **External Accounting System Integration:** `AFR-PSM-055` ("accounting adjustments") is satisfied within PSM by adjusting the linked invoice's `eligible_amount` / hold state and recording an auditable adjustment entry on `DiscrepancyCase` and `PsmAuditLog`, as no separate institute general-ledger module exists in `Fusion-Integrated`.
5. **Pre-approved Shared-File Registrations (Step 4.0):** `config/settings/base.py`, `config/urls.py`, `config/celery.py`, `.importlinter`, `client/src/app/registry.ts`, `client/e2e/accounts.ts`, `ops/docs/psm_reference.py`, and regenerated `openapi/fusion-integrated.v1.yaml` / `registry/permissions.json` / `docs/02-iam/permission-catalog.generated.md`. No other shared files will be touched without explicit approval.
