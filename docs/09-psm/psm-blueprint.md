# Purchase and Stores Management (PSM) — Module Blueprint

- **Module Name:** Purchase and Stores Management
- **Module Code / URL Segment:** `psm` (`/api/v1/psm/`, `/psm`)
- **Docs Folder:** `docs/09-psm/`
- **Spec Prefix:** `PSM-` (`BR-PSM-`, `PSM-UC-`, `BW-PSM-`, `CW-PSM-`, `CFR-PSM-`, `AFR-PSM-`)
- **Environment:** `module-only`
- **Status:** Awaiting Student 2 written approval before Phase 3 implementation

---

## (a) Traceability Table

> **Retired / Excluded IDs (never implemented or cited as live):** `BR-PSM-002` (positive qty/cost), `BR-PSM-011` (withdraw approver acknowledgement — eligibility retained in `BR-PSM-007`), `BR-PSM-016` (asset capitalization/tagging), `PSM-UC-004` (employee invoice download), `PSM-UC-006` (unused index alias for `PSM-UC-007`), `PSM-UC-018` (Department Head cancel indent).
> **Traceability Matrix Note (Step 1.4.5):** `06_PSM_Traceability_Matrix_v1.1_FINAL.xlsx` leaves mapping columns blank on `AFR_Traceability`, `CFR_Rollup`, `UC_AFR`, `BR_AFR`, and `WF_AFR` (except `UC(s)` on `AFR-PSM-091`–`092`). All rows below are derived directly from the six specification documents.

### Active Business Rules (25)

| Id | What it requires | Layer | Planned Enforcement Point | Notes |
|---|---|---|---|---|
| `BR-PSM-001` | Block indent submission/resubmission if item details, quantity, estimated cost, or justification (plus policy-required fields) are missing | `domain/` + `services/` | `domain/rules.py::validate_indent_completeness`, `services/indents.py` | Returns missing field names |
| `BR-PSM-003` | Check departmental and central stock before external procurement; route to internal issue if sufficient allocable stock exists | `domain/` + `services/` | `domain/rules.py::evaluate_stock_routing`, `services/stock.py::check_and_reserve` | Includes both dept & central stock |
| `BR-PSM-004` | Route indent approvals via configured effective-dated approval hierarchy and cost thresholds | `domain/` + `services/` | `domain/policy.py::resolve_approval_route`, `services/approvals.py` | Thresholds from `PsmPolicy` |
| `BR-PSM-005` | Require mandatory justification on any indent rejection; notify requestor and audit | `domain/` + `services/` | `domain/state_machine.py` (`has_reason` guard), `services/approvals.py` | Non-empty justification enforced |
| `BR-PSM-006` | Emit lifecycle notifications (submission, approval, dispatch, receipt, invoice, payment, SLA) and retain communication history | `services/` + `tasks.py` | `services/notifications.py::record_and_queue`, `models/audit.py::NotificationLog` | Outbox pattern + Celery delivery |
| `BR-PSM-007` | Allow indent modify/withdraw/cancel only in policy-designated permissible states; version modifications and re-enter review | `domain/` + `services/` | `domain/policy.py::is_state_permissible`, `services/indents.py::modify_indent` | Creates `IndentVersion` snapshot |
| `BR-PSM-008` | Determine external procurement method (`direct` vs `tender`) from configured value threshold | `domain/` + `services/` | `domain/policy.py::resolve_procurement_method`, `services/procurement.py` | Policy-driven, never hard-coded |
| `BR-PSM-009` | Require delivery confirmation and no unresolved discrepancy before final stock posting or vendor payment release | `domain/` + `services/` | `domain/rules.py::can_finalize_receipt`, `services/receipts.py`, `services/payments.py` | Blocks posting/payment on open case |
| `BR-PSM-010` | Route high-value procurements from PS Admin recommendation to Director/Registrar; return approved indent to PS Admin for execution | `domain/` + `services/` | `domain/state_machine.py`, `services/approvals.py::final_review` | Rejection closes with justification |
| `BR-PSM-012` | Require verified vendor master (GST, bank details, compliance documents) before PO issuance or vendor payment | `domain/` + `services/` | `domain/rules.py::assert_vendor_verified`, `services/procurement.py`, `services/payments.py` | Blocks unverified vendors |
| `BR-PSM-013` | Exclude reserved quantities from allocable stock; hold reservation until dispatch/receipt consumes or releases it | `models/` + `services/` | `selectors/stock.py::allocable_quantity`, `services/stock.py` (`select_for_update`) | DB check prevents negative stock |
| `BR-PSM-014` | Monitor pending approvals against configured SLA rules; emit reminders/escalations and queue-prioritize higher criticality | `domain/` + `tasks.py` | `domain/policy.py::evaluate_sla`, `tasks.py::check_sla_reminders` | Celery beat task; audited |
| `BR-PSM-015` | Detect potential duplicate indents using configured comparison criteria and flag for Department Admin review without auto-cancelling | `domain/` + `services/` | `domain/rules.py::detect_duplicate_indents`, `services/indents.py::submit_indent` | Sets `is_potential_duplicate=True` |
| `BR-PSM-017` | Release vendor payment only when PO exists, GRN accepted, invoice verified, delivery confirmed, and vendor verified | `domain/` + `services/` | `domain/rules.py::check_payment_eligibility`, `services/payments.py` | Otherwise places on hold |
| `BR-PSM-018` | Hold invoice and block payment on PO–GRN–Invoice three-way mismatch; record reason and notify stakeholders | `domain/` + `services/` | `domain/rules.py::evaluate_three_way_match`, `services/payments.py::verify_invoice` | Hold clears only after resolution |
| `BR-PSM-019` | Apply required inventory and accounting adjustments upon resolved return, replacement, or warranty case with full traceability | `services/` | `services/discrepancies.py::resolve_case` | Posts ledger + accounting entries |
| `BR-PSM-020` | Enforce strict RBAC on all functions and data | `api/` + `selectors/` | `HasModuleGrant("psm")`, `HasPermission(...)`, `selectors/scoping.py` | Queryset narrowing yields 404 |
| `BR-PSM-021` | Maintain complete audit trail of material actions and version history for indents, vendors, and report runs | `models/` + `services/` | `models/audit.py::PsmAuditEvent`, `IndentVersion`, `VendorVersion`, `ReportRunLog` | Written atomically in service tx |
| `BR-PSM-022` | Support partial receipts and partial payments per configured policy, retaining open balance/quantities | `domain/` + `services/` | `domain/rules.py::validate_partial_payment`, `services/receipts.py`, `services/payments.py` | Tracks accepted vs ordered qty |
| `BR-PSM-023` | Evaluate tender bids against defined criteria and record Procurement Committee approval before PO proceeds | `services/` + `models/` | `services/tenders.py::evaluate_and_approve`, `models/procurement.py::Tender` | Blocks PO without committee approval |
| `BR-PSM-024` | Restrict reports, dashboards, filters, exports, and scheduled runs to authorized roles and log every generation event | `api/` + `services/` + `tasks.py` | `services/reports.py::generate_report`, `models/audit.py::ReportRunLog` | Logs both ad-hoc & scheduled runs |
| `BR-PSM-025` | Retain version history and audit records for every vendor master creation or change | `models/` + `services/` | `models/vendors.py::VendorVersion`, `services/vendors.py` | Sequential version number per vendor |
| `BR-PSM-026` | Post stock from external procurement only for accepted receipt quantities; never post rejected or discrepant quantities | `services/` | `services/receipts.py::confirm_delivery_receipt` | Appends `StockLedgerEntry` |
| `BR-PSM-027` | Update both source and destination stock ledgers atomically when inter-departmental transfer receipt is confirmed | `services/` | `services/transfers.py::confirm_transfer_receipt` | Paired debit/credit ledger rows |
| `BR-PSM-028` | Enforce configured procurement and financial policy constraints across all governed actions | `domain/` + `services/` | `services/policy.py::require_active_policy`, `domain/policy.py` | Returns clear 409 if no active policy |

### Active Use Cases (32: 31 Actor-Triggered + 1 Event-Triggered)

| Id | Use Case | Layer | Planned Enforcement Point |
|---|---|---|---|
| `PSM-UC-001` | Submit Indent | `services/` + `api/` | `services/indents.py::submit_indent`, `POST /api/v1/psm/indents/` |
| `PSM-UC-002` | Confirm Delivery Receipt | `services/` + `api/` | `services/receipts.py::confirm_delivery_receipt`, `POST /api/v1/psm/grns/{id}/confirm/` |
| `PSM-UC-003` | Track Procurement Status | `selectors/` + `api/` | `selectors/indents.py::get_indent_timeline`, `GET /api/v1/psm/indents/{id}/` |
| `PSM-UC-005` | Withdraw or Cancel Pending Indent | `services/` + `api/` | `services/indents.py::withdraw_or_cancel_indent`, `POST /api/v1/psm/indents/{id}/cancel/` |
| `PSM-UC-007` | Check and Reserve Stock | `services/` + `api/` | `services/stock.py::check_and_reserve_for_indent`, `POST /api/v1/psm/indents/{id}/stock-check/` |
| `PSM-UC-008` | Record Authorized Stock Adjustment | `services/` + `api/` | `services/stock.py::record_stock_adjustment`, `POST /api/v1/psm/stock/adjustments/` |
| `PSM-UC-009` | Process Internal Stock Issue | `services/` + `api/` | `services/stock.py::dispatch_internal_issue`, `POST /api/v1/psm/indents/{id}/internal-issue/` |
| `PSM-UC-010` | Generate Operational, Procurement & Stock Reports | `services/` + `api/` | `services/reports.py::generate_report`, `POST /api/v1/psm/reports/generate/` |
| `PSM-UC-011` | Review Indent (Dept Admin) | `services/` + `api/` | `services/approvals.py::dept_admin_review`, `POST /api/v1/psm/indents/{id}/dept-admin-review/` |
| `PSM-UC-012` | Final Review and Approval (Director/Registrar) | `services/` + `api/` | `services/approvals.py::final_review`, `POST /api/v1/psm/indents/{id}/final-review/` |
| `PSM-UC-013` | Verify Invoice (3-way match) | `services/` + `api/` | `services/payments.py::verify_invoice`, `POST /api/v1/psm/invoices/{id}/verify/` |
| `PSM-UC-014` | Audit Procurement and Financial Records | `selectors/` + `api/` | `selectors/audit.py::audit_events_for`, `GET /api/v1/psm/audit-events/` |
| `PSM-UC-015` | Generate Financial Reports | `services/` + `api/` | `services/reports.py::generate_report(category="financial")`, `POST /api/v1/psm/reports/generate/` |
| `PSM-UC-016` | Review and Recommend Indent (Dept Head) | `services/` + `api/` | `services/approvals.py::dept_head_review`, `POST /api/v1/psm/indents/{id}/dept-head-review/` |
| `PSM-UC-017` | Check Stock During Dept Head Review | `selectors/` + `api/` | `selectors/stock.py::stock_summary_for`, `GET /api/v1/psm/stock/` |
| `PSM-UC-019` | Vendor Onboarding & Master Data Management | `services/` + `api/` | `services/vendors.py`, `/api/v1/psm/vendors/` |
| `PSM-UC-020` | Report Goods Discrepancy & Initiate Return/Replacement | `services/` + `api/` | `services/discrepancies.py::open_case`, `POST /api/v1/psm/discrepancies/` |
| `PSM-UC-021` | Request Inter-Departmental Stock Transfer | `services/` + `api/` | `services/transfers.py::request_transfer`, `POST /api/v1/psm/transfers/` |
| `PSM-UC-022` | Tender / Competitive Procurement Management | `services/` + `api/` | `services/tenders.py`, `/api/v1/psm/tenders/` |
| `PSM-UC-023` | Modify Pending Indent | `services/` + `api/` | `services/indents.py::modify_indent`, `PATCH /api/v1/psm/indents/{id}/` |
| `PSM-UC-024` | Repeat Previous Indent | `services/` + `api/` | `services/indents.py::repeat_indent`, `POST /api/v1/psm/indents/{id}/repeat/` |
| `PSM-UC-025` | Review Procurement & Select Method (PS Admin) | `services/` + `api/` | `services/procurement.py::review_and_select_method`, `POST /api/v1/psm/indents/{id}/procurement-review/` |
| `PSM-UC-026` | Create and Issue Purchase Order | `services/` + `api/` | `services/procurement.py::issue_purchase_order`, `POST /api/v1/psm/purchase-orders/` |
| `PSM-UC-027` | Manage PO Status and Delivery Schedule | `services/` + `api/` | `services/procurement.py::update_po_delivery`, `PATCH /api/v1/psm/purchase-orders/{id}/` |
| `PSM-UC-028` | Inspect Delivery and Record GRN | `services/` + `api/` | `services/receipts.py::record_grn`, `POST /api/v1/psm/grns/` |
| `PSM-UC-029` | Process or Hold Vendor Payment | `services/` + `api/` | `services/payments.py::process_or_hold_payment`, `POST /api/v1/psm/invoices/{id}/payment/` |
| `PSM-UC-030` | View P&S Dashboard | `selectors/` + `api/` | `selectors/reports.py::dashboard_metrics`, `GET /api/v1/psm/dashboard/` |
| `PSM-UC-031` | Schedule Reports | `services/` + `api/` | `services/reports.py::create_report_schedule`, `POST /api/v1/psm/report-schedules/` |
| `PSM-UC-032` | Resolve Return, Replacement or Warranty Case | `services/` + `api/` | `services/discrepancies.py::resolve_case`, `POST /api/v1/psm/discrepancies/{id}/resolve/` |
| `PSM-UC-033` | Process and Dispatch Stock Transfer | `services/` + `api/` | `services/transfers.py::dispatch_transfer`, `POST /api/v1/psm/transfers/{id}/dispatch/` |
| `PSM-UC-034` | Confirm Stock Transfer Receipt | `services/` + `api/` | `services/transfers.py::confirm_transfer_receipt`, `POST /api/v1/psm/transfers/{id}/confirm/` |
| `PSM-UC-035` | Generate Scheduled Report (Event-triggered) | `tasks.py` + `services/` | `tasks.py::run_scheduled_reports` → `services/reports.py::execute_due_schedules` |

### Workflows (11: 9 Basis + 2 Composite) & Requirements (20 CFRs / 92 AFRs)

| Workflow / CFR Group | Covered IDs | Layer | Planned Enforcement Point |
|---|---|---|---|
| `BW-PSM-01` Internal Stock Fulfilment | `CFR-PSM-001`, `003`, `004` (`AFR-PSM-001`–`007`, `013`–`021`) | `domain/state_machine.py` + `services/stock.py`, `services/receipts.py` | Indent state transitions `draft` → `submitted` → `stock_reserved` → `internal_issue_approved` → `dispatched` → `grn_accepted` → `receipt_confirmed` |
| `BW-PSM-02` External Auth (Standard) | `CFR-PSM-005`, `006` (`AFR-PSM-022`–`031`) | `domain/state_machine.py` + `services/approvals.py`, `services/procurement.py` | `submitted` → `external_procurement_required` → `department_reviewed` → `dept_head_recommended` → `procurement_authorized` |
| `BW-PSM-03` External Auth (Final Authority) | `CFR-PSM-005`, `006` (`AFR-PSM-022`–`031`) | `domain/state_machine.py` + `services/approvals.py::final_review` | `dept_head_recommended` → `awaiting_final_approval` → `procurement_authorized` |
| `BW-PSM-04` Direct Procurement to Payment | `CFR-PSM-008`, `009`, `010`, `013` (`AFR-PSM-037`–`047`, `056`–`059`) | `services/procurement.py`, `services/receipts.py`, `services/payments.py` | `procurement_authorized` → `po_issued` → `delivered` → `grn_accepted` → `receipt_confirmed` → `invoice_verified` → `paid`/`partially_paid` |
| `BW-PSM-05` Tender Procurement to Payment | `CFR-PSM-007`–`010`, `013` (`AFR-PSM-032`–`047`, `056`–`059`) | `services/tenders.py`, `services/procurement.py`, `services/payments.py` | `procurement_authorized` → `tender_vendor_selected` → `po_issued` → … → `paid`/`partially_paid` |
| `BW-PSM-06` Discrepancy (Return/Adjustment) | `CFR-PSM-011`, `012` (`AFR-PSM-048`–`055`) | `domain/state_machine.py` + `services/discrepancies.py` | `discrepancy_identified` → `open` → `resolved_adjustment` → invoice/payment unblocked |
| `BW-PSM-10` Discrepancy (One Replacement) | `CFR-PSM-011`, `012` (`AFR-PSM-048`–`055`) | `domain/state_machine.py` + `services/discrepancies.py` | `open` → `replacement_awaited` → `replacement_grn_accepted` → `replacement_confirmed` (max 1 replacement) |
| `BW-PSM-07` Modify Pending Indent | `CFR-PSM-002` (`AFR-PSM-008`–`012`) | `services/indents.py::modify_indent` | Permissible state → `modified_re_review` → Dept Admin / Dept Head re-review |
| `BW-PSM-08` Inter-Dept Stock Transfer | `CFR-PSM-015` (`AFR-PSM-067`–`073`) | `services/transfers.py` | `requested` → `dispatched` → `completed` (atomic source/dest ledger postings) |
| `CW-PSM-01`, `CW-PSM-02` | Composite end-to-end orchestration | `domain/state_machine.py` | Composes `BW-PSM-01`..`05` and `BW-PSM-04`..`06`, `10` |
| Vendor, Reporting, Notifications, Audit | `CFR-PSM-014`, `016`–`020` (`AFR-PSM-060`–`066`, `074`–`092`) | `services/vendors.py`, `services/reports.py`, `services/notifications.py`, `selectors/audit.py` | Full coverage of vendor versioning, filtered/exported/scheduled reports, dashboards, notifications, RBAC, and audit |

---

## (b) Domain Model

All models live in `modules/psm/models/` (one file per aggregate), inherit `TimeStampedModel` (and `UserScopedModel` where owned by a person), and use plain integer `user_id` fields (never ForeignKeys to `auth_user` or other modules; ADR-0013).

1. **`models/policy.py` — `PsmPolicy`** (`BR-PSM-004`, `007`, `008`, `014`, `015`, `022`, `028`)
   - Effective-dated, append-only configuration (`version`, `effective_from`, `superseded_at`, `created_by_id`, `is_active`). Never edited in place; updates insert a new version.
   - Fields: `dept_head_threshold` (Decimal), `final_approval_threshold` (Decimal), `tender_threshold` (Decimal), `final_approver_role` (`director` / `registrar` / `either`), `modifiable_states` (JSON list), `cancellable_states` (JSON list), `sla_reminder_hours` (PositiveInteger), `sla_escalation_hours` (PositiveInteger), `duplicate_window_days` (PositiveInteger), `allow_partial_payment` (Boolean), `partial_payment_max_pct` (Decimal, nullable), `high_priority_direct_flow` (Boolean), `extra_required_indent_fields` (JSON list).
   - DB constraints: `UniqueConstraint(fields=["version"])`, `UniqueConstraint(fields=["is_active"], condition=Q(is_active=True), name="psm_one_active_policy")`, `CheckConstraint` ensuring thresholds are non-negative and `sla_escalation_hours >= sla_reminder_hours`.

2. **`models/indents.py` — `Indent`, `IndentItem`, `IndentVersion`, `ApprovalDecision`** (`BR-PSM-001`, `004`, `005`, `007`, `010`, `014`, `015`, `021`)
   - `Indent`: `indent_number` (unique generated code, e.g. `IND-2026-000001`), `user_id` (requestor), `department` (CharField), `status` (CharField choices), `priority` (`normal`/`high`/`critical`), `justification` (TextField), `estimated_cost` (Decimal 14,2), `submitted_at` (DateTimeField, nullable), `procurement_method` (`""`/`direct`/`tender`), `requires_final_approval` (Boolean), `is_potential_duplicate` (Boolean), `duplicate_of` (self FK, nullable), `repeated_from` (self FK, nullable), `current_version` (PositiveInteger), `sla_reminded_at` (DateTimeField, nullable), `sla_escalated_at` (DateTimeField, nullable).
   - `IndentItem`: FK `indent`, `item_code` (CharField), `item_name` (CharField), `specification` (TextField), `quantity` (Decimal 12,2), `unit` (CharField), `unit_estimated_cost` (Decimal 14,2).
   - `IndentVersion`: immutable snapshot per submit/modify (`indent`, `version_number`, `snapshot_json`, `changed_by_id`, `change_reason`). `UniqueConstraint(fields=["indent", "version_number"])`.
   - `ApprovalDecision`: append-only (`indent`, `stage`, `actor_user_id`, `actor_role`, `decision` (`approve`/`recommend`/`reject`/`request_changes`), `justification`, `decided_at`). `CheckConstraint` requiring non-empty `justification` when `decision="reject"`.

3. **`models/stock.py` — `StockItem`, `StockLedgerEntry`, `StockReservation`, `StockTransfer`** (`BR-PSM-003`, `013`, `026`, `027`)
   - `StockItem`: `item_code`, `item_name`, `location_type` (`central`/`department`), `department` (CharField, blank for central), `unit`. `UniqueConstraint(fields=["item_code", "location_type", "department"])`.
   - `StockLedgerEntry` (**append-only ledger**, Step 2.7): `stock_item` FK, `entry_type` (`opening`/`grn_receipt`/`internal_issue`/`transfer_out`/`transfer_in`/`discrepancy_adjustment`/`manual_adjustment`), `quantity_delta` (Decimal 12,2 — non-zero `CheckConstraint`), `reference_type`, `reference_id`, `actor_user_id`, `reason`. Balance is `SUM(quantity_delta)`; corrections are reversing entries, never updates.
   - `StockReservation`: `stock_item` FK, `indent` FK (nullable), `transfer` FK (nullable), `quantity` (Decimal 12,2 > 0), `status` (`active`/`consumed`/`released`), `reserved_by_id`. `CheckConstraint` enforcing XOR (`indent` vs `transfer`). Allocable stock = `SUM(ledger.quantity_delta) - SUM(active reservations)`.
   - `StockTransfer`: `transfer_number` (unique), `stock_item` FK, `source_department`, `destination_department`, `quantity` (> 0), `status` (`requested`/`dispatched`/`completed`/`cancelled`), `requested_by_id`, `dispatched_by_id`, `confirmed_by_id`, `dispatched_at`, `confirmed_at`. `CheckConstraint(source_department != destination_department)`.

4. **`models/vendors.py` — `Vendor`, `VendorVersion`** (`BR-PSM-012`, `025`)
   - `Vendor`: `vendor_code` (unique), `name`, `gst_number`, `bank_account_number`, `bank_ifsc`, `bank_name`, `compliance_doc_ref`, `is_verified` (Boolean), `verified_by_id` (nullable), `verified_at` (nullable), `is_active` (Boolean), `current_version` (PositiveInteger).
   - `VendorVersion`: immutable snapshot on every create/update (`vendor`, `version_number`, `snapshot_json`, `changed_by_id`). `UniqueConstraint(fields=["vendor", "version_number"])`.

5. **`models/procurement.py` — `Tender`, `TenderBid`, `PurchaseOrder`** (`BR-PSM-008`, `012`, `023`)
   - `Tender`: `tender_number` (unique), `indent` OneToOneField, `title`, `evaluation_criteria` (TextField), `status` (`draft`/`published`/`evaluated`/`awarded`/`cancelled`), `published_at`, `selected_vendor` FK (nullable), `committee_approved_by_id` (nullable), `committee_approved_at` (nullable), `committee_remarks` (TextField).
   - `TenderBid`: `tender` FK, `vendor` FK, `bid_amount` (Decimal 14,2), `technical_notes`, `evaluation_score` (Decimal 6,2, nullable), `evaluation_notes`, `is_selected` (Boolean). `UniqueConstraint(fields=["tender", "vendor"])`, partial `UniqueConstraint(fields=["tender"], condition=Q(is_selected=True), name="psm_one_winning_bid_per_tender")`.
   - `PurchaseOrder`: `po_number` (unique), `indent` FK, `vendor` FK, `tender` FK (nullable), `total_amount` (Decimal 14,2), `status` (`issued`/`partially_delivered`/`delivered`/`closed`/`cancelled`), `planned_delivery_date`, `actual_delivery_date` (nullable), `issued_by_id`, `issued_at`.

6. **`models/receipts.py` — `GoodsReceiptNote`, `DiscrepancyCase`, `Invoice`, `VendorPayment`** (`BR-PSM-009`, `017`, `018`, `019`, `022`, `026`)
   - `GoodsReceiptNote`: `grn_number` (unique), `indent` FK, `purchase_order` FK (nullable for internal issue), `discrepancy_replacement_for` FK to `DiscrepancyCase` (nullable), `inspected_by_id`, `received_quantity`, `accepted_quantity`, `rejected_quantity`, `status` (`accepted`/`partial`/`rejected`), `delivery_confirmed` (Boolean), `confirmed_by_id` (nullable), `confirmed_at` (nullable), `stock_posted` (Boolean). `CheckConstraint(accepted_quantity + rejected_quantity == received_quantity)`.
   - `DiscrepancyCase`: `case_number` (unique), `grn` FK, `indent` FK, `reported_by_id`, `description`, `evidence_ref` (TextField), `resolution_type` (`""`/`return_adjustment`/`replacement`/`warranty`), `status` (`open`/`replacement_awaited`/`replacement_grn_accepted`/`resolved`), `replacement_count` (PositiveSmallInteger, `CheckConstraint(replacement_count <= 1)` enforcing `BW-PSM-10`), `vendor_communication_log` (JSON list), `inventory_adjustment_entry` FK (nullable), `accounting_adjustment_amount` (Decimal 14,2, default 0), `resolved_by_id` (nullable), `resolved_at` (nullable).
   - `Invoice`: `invoice_number`, `purchase_order` FK, `grn` FK (nullable), `vendor` FK, `invoice_amount` (Decimal 14,2), `status` (`submitted`/`verified`/`on_hold`/`partially_paid`/`paid`), `hold_reason` (TextField), `verified_by_id` (nullable), `verified_at` (nullable). `UniqueConstraint(fields=["vendor", "invoice_number"])`.
   - `VendorPayment`: `payment_reference` (unique), `invoice` FK, `amount` (Decimal 14,2 > 0), `is_partial` (Boolean), `status` (`released`/`held`), `hold_reason`, `processed_by_id`, `processed_at`.

7. **`models/audit.py` — `PsmAuditEvent`, `NotificationLog`, `ReportSchedule`, `ReportRunLog`** (`BR-PSM-006`, `021`, `024`, `PSM-UC-031`, `035`)
   - `PsmAuditEvent`: append-only (`actor_user_id`, `actor_role`, `action`, `target_type`, `target_id`, `resulting_state`, `metadata_json`, `created_at`).
   - `NotificationLog`: `recipient_user_id`, `event_type`, `target_type`, `target_id`, `message`, `status` (`pending`/`delivered`), `delivered_at`.
   - `ReportSchedule`: `name`, `report_type` (`operational`/`procurement`/`stock`/`financial`), `filters_json`, `cadence` (`daily`/`weekly`/`monthly`), `created_by_id`, `created_by_role`, `next_run_at`, `is_active`.
   - `ReportRunLog`: `report_type`, `trigger` (`manual`/`scheduled`), `schedule` FK (nullable), `actor_user_id` (nullable for scheduled), `filters_json`, `row_count`, `export_format`, `generated_at`.

---

## (c) State Machines (`modules/psm/domain/state_machine.py`)

All state transitions are declared as immutable `Transition(frm, to, permission, actors, guards)` tuples indexed by `(frm, to)` with a single `resolve(frm, to, actor_kind)` entry point (matching `modules/placement/domain/state_machine.py`).

### 1. Indent Lifecycle (`BW-PSM-01`..`05`, `BW-PSM-07`, `CW-PSM-01`, `CW-PSM-02`)

| From State | To State | Permission | Actors | Guards |
|---|---|---|---|---|
| `draft` | `submitted` | `psm.indent.create` | `employee` | `indent_complete`, `active_policy` |
| `submitted` | `stock_reserved` | `psm.stock.update` | `dept_admin` | `sufficient_allocable_stock` |
| `submitted` | `external_procurement_required` | `psm.stock.update` | `dept_admin` | `insufficient_allocable_stock` |
| `stock_reserved` | `internal_issue_approved` | `psm.indent.review` | `dept_admin` | `reservation_active` |
| `stock_reserved` | `rejected` | `psm.indent.review` | `dept_admin` | `has_reason` |
| `internal_issue_approved` | `dispatched` | `psm.stock.update` | `dept_admin` | `reservation_active` |
| `external_procurement_required` | `department_reviewed` | `psm.indent.review` | `dept_admin` | `active_policy` |
| `external_procurement_required` | `rejected` | `psm.indent.review` | `dept_admin` | `has_reason` |
| `department_reviewed` | `dept_head_recommended` | `psm.indent.review` | `dept_head` | `dept_head_required` |
| `department_reviewed` | `rejected` | `psm.indent.review` | `dept_head` | `has_reason` |
| `department_reviewed` | `procurement_authorized` | `psm.procurement.review` | `ps_admin` | `direct_flow_allowed`, `no_final_approval` |
| `dept_head_recommended` | `procurement_authorized` | `psm.procurement.review` | `ps_admin` | `no_final_approval`, `method_selected` |
| `dept_head_recommended` | `awaiting_final_approval` | `psm.procurement.review` | `ps_admin` | `final_approval_required`, `method_selected` |
| `awaiting_final_approval` | `procurement_authorized` | `psm.indent.approve` | `final_approver` | `authorized_final_approver` |
| `awaiting_final_approval` | `rejected` | `psm.indent.approve` | `final_approver` | `has_reason` |
| `procurement_authorized` | `tender_vendor_selected` | `psm.tender.approve` | `procurement_committee`, `ps_admin` | `tender_method`, `committee_approved` |
| `procurement_authorized` | `po_issued` | `psm.purchase_order.create` | `ps_admin` | `direct_method`, `vendor_verified` |
| `tender_vendor_selected` | `po_issued` | `psm.purchase_order.create` | `ps_admin` | `vendor_verified` |
| `po_issued` | `delivered` | `psm.purchase_order.update` | `ps_admin` | `delivery_recorded` |
| `dispatched` / `delivered` | `grn_accepted` | `psm.grn.create` | `employee`, `dept_admin`, `dept_head` | `accepted_qty_positive` |
| `dispatched` / `delivered` | `discrepancy_open` | `psm.discrepancy.create` | `employee`, `dept_admin`, `dept_head` | `evidence_present` |
| `grn_accepted` | `receipt_confirmed` | `psm.grn.approve` | `employee` | `no_open_discrepancy` |
| `discrepancy_open` | `receipt_confirmed` | `psm.discrepancy.update` | `ps_admin` | `discrepancy_resolved` |
| `receipt_confirmed` | `invoice_verified` | `psm.invoice.review` | `accounts_admin` | `three_way_match_ok` |
| `invoice_verified` | `partially_paid` | `psm.payment.approve` | `accounts_admin` | `payment_eligible`, `partial_allowed` |
| `invoice_verified` / `partially_paid` | `paid` | `psm.payment.approve` | `accounts_admin` | `payment_eligible`, `full_amount_settled` |
| *permissible states* | `modified_re_review` | `psm.indent.update` | `employee` | `state_modifiable`, `indent_complete` |
| `modified_re_review` | `department_reviewed` | `psm.indent.review` | `dept_admin` | `active_policy` |
| *permissible states* | `withdrawn` / `cancelled` | `psm.indent.delete` | `employee` | `state_cancellable` |

### 2. Discrepancy Lifecycle (`BW-PSM-06`, `BW-PSM-10`)
- `open` → `resolved` (`psm.discrepancy.update`, `ps_admin`, guard `return_or_adjustment_posted`)
- `open` → `replacement_awaited` (`psm.discrepancy.update`, `ps_admin`, guard `replacement_count_zero`)
- `replacement_awaited` → `replacement_grn_accepted` (`psm.grn.create`, receiving actor, guard `accepted_qty_positive`)
- `replacement_grn_accepted` → `resolved` (`psm.grn.approve`, `employee`, guard `receipt_confirmed`)

### 3. Stock Transfer Lifecycle (`BW-PSM-08`)
- `requested` → `dispatched` (`psm.transfer.update`, `dept_admin`/`ps_admin`, guard `sufficient_source_stock`)
- `dispatched` → `completed` (`psm.transfer.approve`, `dept_admin`, guard `destination_actor_matches`)
- `requested` → `cancelled` (`psm.transfer.delete`, `dept_admin`, guard `not_dispatched`)

---

## (d) Permission List (`modules/psm/registry.py`)

Every permission uses the closed verb vocabulary in `docs/02-iam/rbac-model.md` (`view`, `create`, `update`, `delete`, `approve`, `publish`, `review`, `assign`, `revoke`, `export`, `import`, `restore`, `manage`). `manage` is avoided entirely in favor of granular verbs.

```python
MODULE = {
    "code": "psm",
    "label": "Purchase & Stores",
    "icon": "ShoppingCart",
    "base_path": "/psm",
    "nav_section": "Administration",
    "sort_order": 30,
    "status": "active",
}

PERMISSIONS = [
    ("psm.indent.view", "View purchase indents within authorized scope"),
    ("psm.indent.create", "Create, submit, and repeat purchase indents"),
    ("psm.indent.update", "Modify pending purchase indents in permissible states"),
    ("psm.indent.delete", "Withdraw or cancel pending purchase indents"),
    ("psm.indent.review", "Review indents (Department Admin / Department Head)"),
    ("psm.indent.approve", "Final approval of high-value indents (Director / Registrar)"),
    ("psm.stock.view", "View departmental and central stock balances and reservations"),
    ("psm.stock.update", "Reserve stock, process internal issue, and post authorized adjustments"),
    ("psm.transfer.view", "View inter-departmental stock transfers"),
    ("psm.transfer.create", "Request an inter-departmental stock transfer"),
    ("psm.transfer.update", "Process and dispatch a stock transfer"),
    ("psm.transfer.approve", "Confirm receipt of an incoming stock transfer"),
    ("psm.transfer.delete", "Cancel an undispatched stock transfer"),
    ("psm.vendor.view", "View vendor master records and version history"),
    ("psm.vendor.create", "Onboard new vendors"),
    ("psm.vendor.update", "Maintain and verify vendor master records"),
    ("psm.procurement.review", "Review external procurement and select procurement method"),
    ("psm.tender.view", "View tenders and submitted bids"),
    ("psm.tender.create", "Create tenders and record vendor bids"),
    ("psm.tender.publish", "Publish tender invitations"),
    ("psm.tender.review", "Evaluate tender bids against defined criteria"),
    ("psm.tender.approve", "Record Procurement Committee tender selection approval"),
    ("psm.purchase_order.view", "View purchase orders and delivery schedules"),
    ("psm.purchase_order.create", "Create and issue purchase orders"),
    ("psm.purchase_order.update", "Update purchase order status and delivery schedule"),
    ("psm.grn.view", "View Goods Receipt Notes"),
    ("psm.grn.create", "Inspect deliveries and record Goods Receipt Notes"),
    ("psm.grn.approve", "Confirm delivery receipt for accepted goods"),
    ("psm.discrepancy.view", "View delivery discrepancy, return, and warranty cases"),
    ("psm.discrepancy.create", "Report delivery discrepancies and initiate return/replacement"),
    ("psm.discrepancy.update", "Resolve return, replacement, or warranty cases"),
    ("psm.invoice.view", "View vendor invoices and three-way match status"),
    ("psm.invoice.create", "Record vendor invoices against purchase orders"),
    ("psm.invoice.review", "Verify invoices via three-way match or place on hold"),
    ("psm.payment.view", "View vendor payment records"),
    ("psm.payment.approve", "Release or hold vendor payments (full or partial)"),
    ("psm.report.view", "View dashboards and operational/procurement/stock/financial reports"),
    ("psm.report.export", "Export reports and configure report schedules"),
    ("psm.audit.view", "Inspect procurement and financial audit trails"),
    ("psm.policy.view", "View active and historical PSM policy versions"),
    ("psm.policy.create", "Publish new effective-dated PSM policy versions"),
    ("psm.sla.review", "System SLA reminder and escalation sweep"),
    ("psm.report.publish", "System execution of scheduled reports"),
]

SYSTEM_PERMISSIONS = [
    "psm.sla.review",
    "psm.report.publish",
]
```

### Role Grants (Exact `globals_designation` Spellings from `fusionlab`)

| Spec Actor | `globals_designation` / Basic Role Keys | Citation |
|---|---|---|
| Employee (Requestor) | `"faculty"`, `"staff"` | PS §2; `PSM-UC-001`..`003`, `005`, `020`, `023`, `024`, `028` |
| Department Admin | `"dept_admin"`, `"deptadmin_cse"`, `"deptadmin_design"`, `"deptadmin_ece"`, `"deptadmin_liberalarts"`, `"deptadmin_me"`, `"deptadmin_ns"`, `"deptadmin_sm"` | PS §2; `PSM-UC-007`..`011`, `020`, `021`, `028`, `033`, `034` |
| Department Head | `"HOD (CSE)"`, `"HOD (Design)"`, `"HOD (ECE)"`, `"HOD (Liberal Arts)"`, `"HOD (ME)"`, `"HOD (NS)"` | PS §2; `PSM-UC-016`, `017`, `020`, `028` |
| Procurement & Stores Admin | `"ps_admin"`, `"SectionHead_PS"` | PS §2; `PSM-UC-010`, `019`, `022`, `025`..`027`, `030`–`032` |
| Accounts Admin | `"Accounts Admin"` | PS §2; `PSM-UC-013`–`015`, `029`–`031` |
| Director / Registrar | `"Director"`, `"Registrar"` | PS §2; `PSM-UC-012`, `030` |
| Authorized Auditor | `"Auditor"` | PS §2; `PSM-UC-014`, `030` |
| Procurement Committee *(Open Question #2)* | `"Procurement Committee"` *(not yet in `globals_designation`; provisioned via `assign_role` once approved)* | PS §2; `PSM-UC-022`, `BR-PSM-023` |

*Scoping (`selectors/scoping.py`):* Employees see only their own indents/GRNs/discrepancies (`user_id == actor.user_id`); Department Admins and HODs see their own department's indents, stock, and transfers (involving their department as source or destination); PS Admin, Accounts Admin, Director, Registrar, Procurement Committee, and Auditor have institute-wide visibility for their respective resources. Out-of-scope IDs always return `404`.

---

## (e) Endpoint List, Client Routes & Sidebar Entry

All API routes are mounted under `/api/v1/psm/` behind `HasModuleGrant("psm")` + `HasPermission(...)`.

| Method & Path | Permission Gate | Purpose / Rules |
|---|---|---|
| `GET/POST /api/v1/psm/indents/` | `psm.indent.view` / `psm.indent.create` | List scoped indents; create/submit indent (`PSM-UC-001`, `BR-PSM-001`, `015`, `021`) |
| `GET/PATCH /api/v1/psm/indents/{id}/` | `psm.indent.view` / `psm.indent.update` | Detail + timeline (`PSM-UC-003`); modify pending indent (`PSM-UC-023`, `BR-PSM-007`) |
| `POST /api/v1/psm/indents/{id}/cancel/` | `psm.indent.delete` | Withdraw/cancel in permissible state (`PSM-UC-005`, `BR-PSM-007`) |
| `POST /api/v1/psm/indents/{id}/repeat/` | `psm.indent.create` | Repeat previous indent as new draft (`PSM-UC-024`) |
| `POST /api/v1/psm/indents/{id}/stock-check/` | `psm.stock.update` | Check dept/central stock & reserve (`PSM-UC-007`, `BR-PSM-003`, `013`) |
| `POST /api/v1/psm/indents/{id}/dept-admin-review/` | `psm.indent.review` | Dept Admin approve/reject & set priority (`PSM-UC-011`, `BR-PSM-004`, `005`, `014`) |
| `POST /api/v1/psm/indents/{id}/internal-issue/` | `psm.stock.update` | Schedule picking & dispatch internal issue (`PSM-UC-009`, `BR-PSM-013`) |
| `POST /api/v1/psm/indents/{id}/dept-head-review/` | `psm.indent.review` | Dept Head recommend/reject/request changes (`PSM-UC-016`, `BR-PSM-004`, `005`) |
| `POST /api/v1/psm/indents/{id}/procurement-review/` | `psm.procurement.review` | PS Admin select direct/tender & route high-value (`PSM-UC-025`, `BR-PSM-008`, `010`) |
| `POST /api/v1/psm/indents/{id}/final-review/` | `psm.indent.approve` | Director/Registrar final approve/reject (`PSM-UC-012`, `BR-PSM-005`, `010`) |
| `GET /api/v1/psm/stock/` & `POST /api/v1/psm/stock/adjustments/` | `psm.stock.view` / `psm.stock.update` | Stock balances/reservations (`PSM-UC-017`) & authorized adjustments (`PSM-UC-008`, `BR-PSM-026`) |
| `GET/POST /api/v1/psm/transfers/` + `/{id}/dispatch/`, `/{id}/confirm/`, `/{id}/cancel/` | `psm.transfer.*` | Inter-departmental transfer lifecycle (`PSM-UC-021`, `033`, `034`, `BR-PSM-013`, `027`) |
| `GET/POST/PATCH /api/v1/psm/vendors/` + `/{id}/verify/` | `psm.vendor.*` | Vendor onboarding, versioning, verification (`PSM-UC-019`, `BR-PSM-012`, `025`) |
| `GET/POST /api/v1/psm/tenders/` + `/{id}/publish/`, `/{id}/bids/`, `/{id}/evaluate/`, `/{id}/approve/` | `psm.tender.*` | Tender lifecycle & committee approval (`PSM-UC-022`, `BR-PSM-023`) |
| `GET/POST/PATCH /api/v1/psm/purchase-orders/` | `psm.purchase_order.*` | PO creation, status, delivery schedule (`PSM-UC-026`, `027`, `BR-PSM-012`) |
| `GET/POST /api/v1/psm/grns/` + `/{id}/confirm/` | `psm.grn.*` | Delivery inspection/GRN (`PSM-UC-028`) & receipt confirmation (`PSM-UC-002`, `BR-PSM-009`, `022`, `026`) |
| `GET/POST /api/v1/psm/discrepancies/` + `/{id}/resolve/` | `psm.discrepancy.*` | Report discrepancy (`PSM-UC-020`) & resolve return/replacement/warranty (`PSM-UC-032`, `BR-PSM-019`) |
| `GET/POST /api/v1/psm/invoices/` + `/{id}/verify/`, `/{id}/payment/` | `psm.invoice.*`, `psm.payment.approve` | 3-way match verification (`PSM-UC-013`, `BR-PSM-018`) & payment release/hold (`PSM-UC-029`, `BR-PSM-017`, `022`) |
| `GET /api/v1/psm/dashboard/`, `POST /api/v1/psm/reports/generate/`, `GET/POST /api/v1/psm/report-schedules/` | `psm.report.view` / `psm.report.export` | Dashboard (`PSM-UC-030`), filtered/exported reports (`PSM-UC-010`, `015`), schedules (`PSM-UC-031`, `BR-PSM-024`) |
| `GET /api/v1/psm/audit-events/` & `GET/POST /api/v1/psm/policies/` | `psm.audit.view` / `psm.policy.*` | Audit log (`PSM-UC-014`, `BR-PSM-021`) & effective-dated policy (`BR-PSM-028`) |

### Client Routes & `NAV_ITEMS` (1:1 Match)

| Route (`/psm/...`) | Nav Item Code | `RequirePermission` Guard |
|---|---|---|
| `indents` | `psm.indents` | `psm.indent.view` (all module roles with indent access) |
| `stock` | `psm.stock` | `psm.stock.view` |
| `transfers` | `psm.transfers` | `psm.transfer.view` |
| `procurement` | `psm.procurement` | `psm.purchase_order.view` (tenders + POs in tabs/drawers) |
| `vendors` | `psm.vendors` | `psm.vendor.view` |
| `receipts` | `psm.receipts` | `psm.grn.view` (GRNs + discrepancies in tabs/drawers) |
| `invoices` | `psm.invoices` | `psm.invoice.view` (3-way match + payments in drawers) |
| `reports` | `psm.reports` | `psm.report.view` (dashboard + reports + schedules) |
| `audit` | `psm.audit` | `psm.audit.view` |

### `Fusion-client` `INTEGRATED_MODULES` Entry (Handoff for `full-platform`)
```js
{
  id: "psm",
  label: "Purchase & Stores",
  icon: "ShoppingCart",
  to: "/psm",
  section: "Administration",
}
```

---

## (f) Contracts (`modules/psm/contracts.py`)

- **Exposed by `modules/psm/contracts.py`** (all plural getters returning `dict[int, DTO]`):
  - `get_indents(indent_ids: Sequence[int]) -> dict[int, IndentSummaryDTO]`
  - `get_purchase_orders(po_ids: Sequence[int]) -> dict[int, PurchaseOrderSummaryDTO]`
  - `get_vendors(vendor_ids: Sequence[int]) -> dict[int, VendorSummaryDTO]`
  - `get_stock_balances(stock_item_ids: Sequence[int]) -> dict[int, StockBalanceDTO]`
- **Consumed from `modules/directory/contracts.py`**: `get_users(user_ids)`, `search(q, kind, limit)`, `get_employees()`.
- **IAM**: No new `IamClient` endpoints required; uses existing session/principal and `modules/directory` projections. Never touches `fusionlab`.

---

## (g) Scheduled Work (`modules/psm/schedule.py`)

| Beat Entry | Task | Cadence | Queue | What breaks if stopped |
|---|---|---|---|---|
| `psm.deliver-notifications` | `psm.deliver_notifications` | Every 60s (`expires: 55`) | `notifications` | Lifecycle notifications (`BR-PSM-006`) remain queued and undelivered |
| `psm.check-sla-reminders` | `psm.check_sla_reminders` | Every 15 min (`expires: 800`) | `default` | Pending approvals never trigger SLA reminders or escalations (`BR-PSM-014`) |
| `psm.run-scheduled-reports` | `psm.run_scheduled_reports` | Every 15 min (`expires: 800`) | `reports` | Configured report schedules (`PSM-UC-031`, `PSM-UC-035`) never execute or log runs (`BR-PSM-024`) |

---

## (h) Open Questions & Known Gaps (Requires Student 2 Written Approval)

1. **Unspecified policy parameters (PS §4):** The spec intentionally leaves 6 parameters configurable (cost thresholds for Dept Head & Director/Registrar, tender value threshold, SLA reminder/escalation durations, permissible states for modify/withdraw/cancel, partial-payment rules, and Director vs. Registrar routing). **Proposed resolution:** Store all 6 in effective-dated `PsmPolicy` (no hard-coded thresholds); return `409 Conflict` with a clear missing-policy message if no active policy exists; seed a dev/demo policy version in `seed_demo` for local testing and E2E.
2. **`Procurement Committee` designation (Step 2.4 / Step 3.4):** `globals_designation` in `fusion-dev.dump` has exact matches for all other internal roles (`dept_admin`/`deptadmin_*`, `HOD (*)`, `ps_admin`/`SectionHead_PS`, `Accounts Admin`, `Director`, `Registrar`, `Auditor`), plus `faculty`/`staff` basic roles, but has **no `Procurement Committee` designation**. **Proposed resolution:** Declare `"Procurement Committee"` in `ROLE_GRANTS` (cited to PS §2, `PSM-UC-022`, `BR-PSM-023`) and provision it on a test account via `assign_role` for dev/E2E verification; flag creation in production ERP as an institute admin action.
3. **`Fusion-client` sidebar registration (`module-only` gap):** Adding the `INTEGRATED_MODULES` entry in `Fusion-client/src/ui/nav/navigation.js` is deferred to `full-platform` integration (exact snippet provided in §(e) above).
4. **External notification delivery & file storage:** In `module-only`, lifecycle notifications (`BR-PSM-006`) are persisted in `NotificationLog` and drained by Celery outbox; discrepancy evidence and vendor compliance documents store URL/reference strings (matching Placement's Google Drive link convention) rather than local binary uploads inside the repo.
