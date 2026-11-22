# PSM Architecture Blueprint — Purchase and Stores Management Module
**Module Code:** `psm` | **Docs Folder:** `docs/09-psm/` | **Prefix:** `PSM-`  
**Authors:** Student 1: J Yasaswin (`24BCS096`) | Student 2: MV Siva Poojith (`24BCS157`)  
**Status:** Submitted for Student 2 Approval | **Date:** 22 November 2026

---

## 1. §2 — Phase 1: Architectural Foundations & Bound Context Analysis

### 1.1 Bounded Context
PSM is **one single bounded context**: the complete procurement and stores lifecycle inside the institute. It encapsulates:
* Purchase indent generation, departmental review, and hierarchical approval routing.
* Vendor directory and verified master data management.
* Procurement methods (direct procurement and tendering/bidding execution).
* Purchase order lifecycle and vendor contract binding.
* Goods receipt (GRN), quality inspection, indentor receipt acknowledgement, and discrepancy lifecycle.
* Central and departmental inventory stock ledger, stock reservations, and internal stock issues.
* 3-way invoice matching and payment authorization hold gates.

### 1.2 Inter-Module Contracts
PSM relies on Fusion services via HTTP/contracts rather than direct database joins:
1. **`fusion_auth` (IAM):** Resolves caller principal, role designations (`staff`, `faculty`, `hod`, `ps_admin`, `accounts_admin`, `director`), and session permissions.
2. **`modules/directory` (Directory):** Projects user display names, designations, and departmental affiliations (`get_users`, `search_users`).
3. **`modules/accesscontrol` (RBAC):** Synchronizes role grants and navigation descriptors via `registry.py` and `permissions.json`.
4. **Finance / Accounts Integration:** Emits payment authorization events and respects payment hold states.

### 1.3 Identity Invariants
In strict adherence to Fusion-Integrated architecture:
* Every person/actor reference is a primitive **integer `user_id`** (using `core/db/mixins.py::UserScopedModel`).
* No direct foreign keys or joins to `auth_user` or external database tables exist.

### 1.4 Role to Designation Mapping
| Spec Role | Fusion IAM Designation Key | Scope |
| :--- | :--- | :--- |
| **Requestor / Employee** | `staff`, `faculty` (base kinds) | Own indents, assigned receipt acknowledgements |
| **Department Admin** | `dept_admin`, `admin_assistant` | Departmental indents, departmental stock issues |
| **Department Head (HOD)** | `head_of_department` | Department indents within threshold |
| **Procurement & Stores Admin** | `purchase_officer`, `store_keeper` | Institute-wide indents, POs, vendors, tenders, central stock |
| **Accounts Admin** | `accounts_admin`, `finance_officer` | Invoices, 3-way matching, payment authorizations |
| **Director / Registrar** | `director`, `registrar` | High-value indents exceeding approval threshold |

---

## 2. Step 3.1 — Traceability Table

| ID | What it Requires | Architectural Layer | Enforcement Point | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **CFR-PSM-001** | Indent submission with line items | API / Domain | `services/indent_service.py` | Must contain $\ge 1$ item |
| **CFR-PSM-002** | Department stock check before PO | Domain / Service | `services/inventory_service.py` | Check central & dept stock |
| **CFR-PSM-003** | Hierarchical approval workflow | Domain / State Machine | `domain/workflow_engine.py` | Enforces stage transitions |
| **CFR-PSM-004** | Value-based procurement routing | Domain Service | `domain/threshold_policy.py` | Direct (<₹25k) vs Quotation/Tender |
| **CFR-PSM-005** | High-value approval escalation | Domain / Service | `domain/approval_policy.py` | Escalates to Director when total > ₹2,50,000 |
| **CFR-PSM-006** | Vendor master registration & vetting | Model / Service | `services/vendor_service.py` | Verified status flag required |
| **CFR-PSM-007** | Purchase Order issuance | Domain / Model | `services/po_service.py` | Only against approved indent & verified vendor |
| **CFR-PSM-008** | Goods Receipt Note (GRN) logging | Model / Service | `services/grn_service.py` | Logs received vs accepted/rejected quantity |
| **CFR-PSM-009** | Indentor receipt acknowledgement | API / Domain | `api/views/grn_views.py` | User confirmation within 3 days |
| **CFR-PSM-010** | Discrepancy report & return flow | Domain / Model | `services/discrepancy_service.py` | Freezes invoice payment hold |
| **CFR-PSM-011** | 3-way invoice matching | Domain Service | `services/invoice_service.py` | PO $\leftrightarrow$ GRN $\leftrightarrow$ Invoice match |
| **CFR-PSM-012** | Stock ledger inventory credit | Model / DB | `models/inventory.py` | Transactional ledger credit |
| **BR-PSM-001** | Indent completeness validation | Domain Validation | `domain/validators.py` | Rejects missing items or negative prices |
| **BR-PSM-003** | Stock-before-procurement constraint | Domain Routing | `services/indent_service.py` | Rejection if available in stock |
| **BR-PSM-004** | Configurable approval sequence | State Machine | `domain/state_machines.py` | Requestor $\to$ HOD $\to$ PS Admin $\to$ Director |
| **BR-PSM-005** | Mandatory rejection reason | Domain Validation | `domain/validators.py` | Rejection requires non-empty reason |
| **BR-PSM-007** | Indent modification/cancellation | State Machine | `models/indent.py` | Allowed only in `DRAFT` or `PENDING_DEPT` |
| **BR-PSM-008** | Threshold procurement rules | Domain Service | `domain/threshold_policy.py` | <₹25k Direct, ₹25k-₹2.5L Quotation, >₹2.5L Tender |
| **BR-PSM-009** | Discrepancy hold on payment | State Machine | `models/discrepancy.py` | Blocks invoice clearance until resolved |
| **BR-PSM-010** | High-value approval routing | Domain / Service | `services/indent_service.py` | Director approval if amount $\ge$ ₹2,50,000 |
| **BR-PSM-012** | Verified vendor gate for PO | Domain / DB | `models/purchase_order.py` | Vendor status must be `VERIFIED` |
| **BR-PSM-013** | Stock reservation locking | Model / DB | `models/inventory.py` | Atomic reservation counter |
| **BW-PSM-01** | Internal Stock Fulfilment | Workflow Engine | `services/inventory_service.py` | Immediate fulfillment from store |
| **BW-PSM-02** | Standard External Procurement | Workflow Engine | `services/workflow_service.py` | Standard path through PO and GRN |
| **BW-PSM-03** | Final Authority Procurement Path | Workflow Engine | `services/workflow_service.py` | Includes Director signoff step |
| **BW-PSM-06** | Discrepancy Return & Adjustment | Workflow Engine | `services/discrepancy_service.py` | Return damaged goods to vendor |

---

## 3. Step 3.2 — Domain Model & Database Constraints

### 3.1 Entities and Schema Invariants

```
  ┌──────────────┐       1..N       ┌────────────────┐
  │    Indent    │◄─────────────────┤   IndentItem   │
  └──────┬───────┘                  └────────────────┘
         │ 1
         │ creates
         ▼ 0..1
  ┌──────────────┐       1..N       ┌────────────────┐
  │PurchaseOrder │◄─────────────────┤   POLineItem   │
  └──────┬───────┘                  └────────────────┘
         │ 1
         │ receives
         ▼ 0..N
  ┌──────────────┐       1..N       ┌────────────────┐
  │ GoodsReceipt │◄─────────────────┤    GRNItem     │
  └──────┬───────┘                  └────────┬───────┘
         │ 1 (if defective)                  │ updates
         ▼ 0..1                              ▼
  ┌──────────────┐                  ┌────────────────┐
  │ Discrepancy  │                  │   StockItem    │
  └──────────────┘                  └────────────────┘
```

#### `Vendor`
* `id` (PK, BigAuto)
* `vendor_code` (CharField, unique)
* `name` (CharField)
* `gstin` (CharField, max_length=15, unique)
* `email`, `phone`, `address`
* `status` (CharField: `PENDING_VERIFICATION`, `VERIFIED`, `BLACKLISTED`, `SUSPENDED`)
* `created_at`, `updated_at`
* **DB Invariant:** `CheckConstraint(check=Q(status__in=[...]), name="valid_vendor_status")`

#### `ItemMaster`
* `id` (PK)
* `item_code` (CharField, unique)
* `name` (CharField), `description` (TextField)
* `category` (CharField: `CONSUMABLE`, `EQUIPMENT`, `SERVICE`, `FURNITURE`)
* `unit_of_measure` (CharField, e.g. `PIECE`, `BOX`, `KG`, `METER`)
* `minimum_stock_level` (PositiveIntegerField, default=0)

#### `Indent`
* `id` (PK)
* `indent_number` (CharField, unique: `IND-YYYY-XXXX`)
* `creator_user_id` (BigIntegerField, index=True)
* `department_code` (CharField, max_length=32, index=True)
* `title` (CharField), `purpose` (TextField)
* `estimated_total` (DecimalField, max_digits=12, decimal_places=2, default=0.00)
* `status` (CharField: `DRAFT`, `SUBMITTED`, `PENDING_DEPT_APPROVAL`, `PENDING_PS_REVIEW`, `PENDING_DIRECTOR_APPROVAL`, `APPROVED`, `REJECTED`, `CANCELLED`, `FULFILLED`)
* `current_approver_role` (CharField, nullable)
* `rejection_reason` (TextField, blank=True)
* `created_at`, `updated_at`
* **DB Invariant:** `CheckConstraint(check=Q(estimated_total__gte=0), name="indent_cost_non_negative")`

#### `IndentItem`
* `id` (PK)
* `indent` (FK $\to$ `Indent`, related_name="items", on_delete=CASCADE)
* `item_master` (FK $\to$ `ItemMaster`, on_delete=PROTECT)
* `quantity_requested` (PositiveIntegerField)
* `estimated_unit_cost` (DecimalField, max_digits=10, decimal_places=2)
* `specifications` (TextField, blank=True)
* **DB Invariant:** `CheckConstraint(check=Q(quantity_requested__gt=0), name="indent_qty_positive")`

#### `PurchaseOrder`
* `id` (PK)
* `po_number` (CharField, unique: `PO-YYYY-XXXX`)
* `indent` (OneToOneField $\to$ `Indent`, on_delete=PROTECT, related_name="purchase_order")
* `vendor` (FK $\to$ `Vendor`, on_delete=PROTECT, related_name="purchase_orders")
* `total_amount` (DecimalField, max_digits=12, decimal_places=2)
* `procurement_method` (CharField: `DIRECT`, `QUOTATION`, `TENDER`, `GEM`)
* `status` (CharField: `DRAFT`, `ISSUED`, `PARTIALLY_DELIVERED`, `COMPLETED`, `CANCELLED`)
* `issued_by_user_id` (BigIntegerField)
* `issued_at`, `delivery_due_date`
* **DB Invariant:** `CheckConstraint(check=Q(total_amount__gte=0), name="po_total_non_negative")`

#### `POLineItem`
* `id` (PK)
* `purchase_order` (FK $\to$ `PurchaseOrder`, related_name="lines", on_delete=CASCADE)
* `item_master` (FK $\to$ `ItemMaster`, on_delete=PROTECT)
* `quantity_ordered` (PositiveIntegerField)
* `unit_price` (DecimalField, max_digits=10, decimal_places=2)

#### `GoodsReceiptNote (GRN)`
* `id` (PK)
* `grn_number` (CharField, unique: `GRN-YYYY-XXXX`)
* `purchase_order` (FK $\to$ `PurchaseOrder`, related_name="grns", on_delete=PROTECT)
* `store_keeper_user_id` (BigIntegerField)
* `challan_number` (CharField), `invoice_number` (CharField)
* `receipt_date` (DateField)
* `status` (CharField: `INSPECTION_PENDING`, `ACCEPTED`, `DISCREPANT`, `CLOSED`)
* `indentor_acknowledged` (BooleanField, default=False)
* `indentor_acknowledged_at` (DateTimeField, nullable=True)

#### `GRNItem`
* `id` (PK)
* `grn` (FK $\to$ `GoodsReceiptNote`, related_name="items", on_delete=CASCADE)
* `po_line_item` (FK $\to$ `POLineItem`, on_delete=PROTECT)
* `quantity_received` (PositiveIntegerField)
* `quantity_accepted` (PositiveIntegerField, default=0)
* `quantity_rejected` (PositiveIntegerField, default=0)
* `rejection_remarks` (TextField, blank=True)
* **DB Invariant:** `CheckConstraint(check=Q(quantity_accepted + quantity_rejected == quantity_received), name="grn_item_quantity_balance")`

#### `DiscrepancyReport`
* `id` (PK)
* `discrepancy_code` (CharField, unique: `DISC-YYYY-XXXX`)
* `grn` (OneToOneField $\to$ `GoodsReceiptNote`, related_name="discrepancy_report", on_delete=CASCADE)
* `reported_by_user_id` (BigIntegerField)
* `discrepancy_type` (CharField: `SHORTAGE`, `DAMAGED`, `SPEC_MISMATCH`, `WRONG_ITEM`)
* `details` (TextField)
* `status` (CharField: `OPEN_HOLD_PAYMENT`, `VENDOR_NOTIFIED`, `REPLACED`, `CREDIT_NOTE_ISSUED`, `RESOLVED`)
* `resolution_summary` (TextField, blank=True)

#### `StockItem`
* `id` (PK)
* `item_master` (OneToOneField $\to$ `ItemMaster`, on_delete=CASCADE, related_name="stock")
* `quantity_on_hand` (PositiveIntegerField, default=0)
* `quantity_reserved` (PositiveIntegerField, default=0)
* **DB Invariant:** `CheckConstraint(check=Q(quantity_reserved <= quantity_on_hand), name="stock_reservation_limit")`

---

## 4. Step 3.3 — Declarative State Machine

### 4.1 Indent Transition Table
```python
INDENT_TRANSITIONS = {
    # (Current State, Event, Permitted Role) -> (Next State)
    ("DRAFT", "SUBMIT", "requestor"): "SUBMITTED",
    ("DRAFT", "CANCEL", "requestor"): "CANCELLED",
    ("SUBMITTED", "DEPT_VERIFY", "dept_admin"): "PENDING_DEPT_APPROVAL",
    ("PENDING_DEPT_APPROVAL", "HOD_APPROVE_LOW", "hod"): "PENDING_PS_REVIEW",
    ("PENDING_DEPT_APPROVAL", "HOD_REJECT", "hod"): "REJECTED",
    ("PENDING_PS_REVIEW", "PS_APPROVE_STANDARD", "ps_admin"): "APPROVED",
    ("PENDING_PS_REVIEW", "PS_ESCALATE_HIGH_VALUE", "ps_admin"): "PENDING_DIRECTOR_APPROVAL",
    ("PENDING_PS_REVIEW", "PS_REJECT", "ps_admin"): "REJECTED",
    ("PENDING_DIRECTOR_APPROVAL", "DIRECTOR_APPROVE", "director"): "APPROVED",
    ("PENDING_DIRECTOR_APPROVAL", "DIRECTOR_REJECT", "director"): "REJECTED",
    ("APPROVED", "FULFILL_STOCK", "store_keeper"): "FULFILLED",
    ("APPROVED", "ISSUE_PO", "purchase_officer"): "FULFILLED",
}
```

### 4.2 Purchase Order Transition Table
```python
PO_TRANSITIONS = {
    ("DRAFT", "ISSUE", "purchase_officer"): "ISSUED",
    ("ISSUED", "RECORD_DELIVERY_PARTIAL", "store_keeper"): "PARTIALLY_DELIVERED",
    ("ISSUED", "RECORD_DELIVERY_COMPLETE", "store_keeper"): "COMPLETED",
    ("PARTIALLY_DELIVERED", "RECORD_DELIVERY_COMPLETE", "store_keeper"): "COMPLETED",
    ("ISSUED", "CANCEL", "purchase_officer"): "CANCELLED",
}
```

### 4.3 Goods Receipt Note & Discrepancy Table
```python
GRN_TRANSITIONS = {
    ("INSPECTION_PENDING", "ACCEPT_ALL", "store_keeper"): "ACCEPTED",
    ("INSPECTION_PENDING", "FLAG_DISCREPANCY", "store_keeper"): "DISCREPANT",
    ("DISCREPANT", "INDENTOR_ACK_DISPUTE", "requestor"): "DISCREPANT",
    ("DISCREPANT", "RESOLVE_DISCREPANCY", "purchase_officer"): "CLOSED",
    ("ACCEPTED", "INDENTOR_CONFIRM", "requestor"): "CLOSED",
}
```

---

## 5. Step 3.4 — Permission List & IAM Registry

### Exact `registry.py` Specification:
```python
MODULE = {
    "id": "psm",
    "name": "Purchase and Stores Management",
    "description": "Enterprise procurement, stores inventory, indent approvals, vendor vetting, and 3-way matching",
    "icon": "ShoppingCart",
    "default_route": "/psm/indents",
}

PERMISSIONS = [
    # Indents
    ("psm.indent.create", "Raise new purchase indents"),
    ("psm.indent.view", "View indents within user or departmental scope"),
    ("psm.indent.approve_dept", "Department-level indent verification and HOD approval"),
    ("psm.indent.approve_ps", "Procurement & Stores admin indent evaluation and routing"),
    ("psm.indent.approve_director", "Director / Registrar high-value indent approval"),
    # Stock & Stores
    ("psm.stock.view", "View store inventory and ledger entries"),
    ("psm.stock.manage", "Issue departmental stock and manage adjustments"),
    # Vendors
    ("psm.vendor.view", "View vendor master records"),
    ("psm.vendor.manage", "Onboard, vet, verify and update vendor master data"),
    # Purchase Orders
    ("psm.po.create", "Generate and issue Purchase Orders"),
    ("psm.po.view", "Inspect Purchase Orders and delivery status"),
    # Goods Receipt
    ("psm.grn.create", "Log Goods Receipt Notes upon delivery"),
    ("psm.grn.view", "View Goods Receipt Notes"),
    ("psm.grn.acknowledge", "Indentor goods delivery acknowledgement"),
    # Discrepancies
    ("psm.discrepancy.manage", "Log and resolve discrepancy reports"),
    # Invoices & Accounts
    ("psm.invoice.match", "Perform 3-way invoice matching and payment authorization"),
]

ROLE_GRANTS = {
    "staff": [
        "psm.indent.create",
        "psm.indent.view",
        "psm.grn.view",
        "psm.grn.acknowledge",
    ],
    "faculty": [
        "psm.indent.create",
        "psm.indent.view",
        "psm.grn.view",
        "psm.grn.acknowledge",
    ],
    "dept_admin": [
        "psm.indent.view",
        "psm.indent.approve_dept",
        "psm.stock.view",
        "psm.stock.manage",
    ],
    "head_of_department": [
        "psm.indent.view",
        "psm.indent.approve_dept",
        "psm.stock.view",
    ],
    "purchase_officer": [
        "psm.indent.view",
        "psm.indent.approve_ps",
        "psm.vendor.view",
        "psm.vendor.manage",
        "psm.po.create",
        "psm.po.view",
        "psm.grn.view",
        "psm.discrepancy.manage",
    ],
    "store_keeper": [
        "psm.stock.view",
        "psm.stock.manage",
        "psm.po.view",
        "psm.grn.create",
        "psm.grn.view",
        "psm.discrepancy.manage",
    ],
    "accounts_admin": [
        "psm.po.view",
        "psm.grn.view",
        "psm.invoice.match",
    ],
    "director": [
        "psm.indent.view",
        "psm.indent.approve_director",
        "psm.po.view",
    ],
}
```

---

## 6. Step 3.5 — Endpoint List & Client Routes

### 6.1 Backend API Endpoints (`/api/v1/psm/`)

| Method | Path | Required Permission | Description | Enforced Rules |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/indents/` | `psm.indent.view` | List indents (scoped by role/dept) | CFR-PSM-001 |
| `POST` | `/indents/` | `psm.indent.create` | Create new indent | BR-PSM-001 |
| `GET` | `/indents/{id}/` | `psm.indent.view` | Retrieve indent detail with items | BR-PSM-006 |
| `PUT` | `/indents/{id}/` | `psm.indent.create` | Update draft indent | BR-PSM-007 |
| `POST` | `/indents/{id}/submit/` | `psm.indent.create` | Submit indent for review | BW-PSM-02 |
| `POST` | `/indents/{id}/action/` | `psm.indent.approve_*`| Approve/Reject/Escalate indent | BR-PSM-004, BR-PSM-005, BR-PSM-010 |
| `GET` | `/vendors/` | `psm.vendor.view` | List vendor master directory | CFR-PSM-006 |
| `POST` | `/vendors/` | `psm.vendor.manage` | Onboard new vendor | BR-PSM-012 |
| `PATCH`| `/vendors/{id}/status/` | `psm.vendor.manage` | Update verification status | BR-PSM-012 |
| `GET` | `/purchase-orders/` | `psm.po.view` | List purchase orders | CFR-PSM-007 |
| `POST` | `/purchase-orders/` | `psm.po.create` | Issue PO against approved indent | BR-PSM-008, BR-PSM-012 |
| `GET` | `/goods-receipts/` | `psm.grn.view` | List GRNs | CFR-PSM-008 |
| `POST` | `/goods-receipts/` | `psm.grn.create` | Record receipt of goods | BR-PSM-009 |
| `POST` | `/goods-receipts/{id}/ack/`| `psm.grn.acknowledge`| Indentor receipt confirmation | CFR-PSM-009 |
| `GET` | `/stock/` | `psm.stock.view` | Query inventory stock levels | CFR-PSM-002, BR-PSM-013 |
| `POST` | `/stock/issue/` | `psm.stock.manage` | Fulfill internal stock transfer | BW-PSM-01 |
| `GET` | `/discrepancies/` | `psm.discrepancy.manage` | List discrepancy tickets | BR-PSM-009, BW-PSM-06 |
| `POST` | `/invoices/match/` | `psm.invoice.match` | 3-way matching and hold check | CFR-PSM-011 |

### 6.2 Client Routes (`client/src/modules/psm/routes.tsx`)

* `/psm/indents` $\to$ `IndentListPage` (Guarded: `psm.indent.view`)
* `/psm/indents/new` $\to$ `IndentCreatePage` (Guarded: `psm.indent.create`)
* `/psm/approvals` $\to$ `ApprovalQueuePage` (Guarded: `psm.indent.approve_dept`)
* `/psm/purchase-orders` $\to$ `PurchaseOrderPage` (Guarded: `psm.po.view`)
* `/psm/goods-receipts` $\to$ `GoodsReceiptPage` (Guarded: `psm.grn.view`)
* `/psm/inventory` $\to$ `StockInventoryPage` (Guarded: `psm.stock.view`)
* `/psm/vendors` $\to$ `VendorMasterPage` (Guarded: `psm.vendor.view`)

---

## 7. Step 3.6 — Contracts

### `modules/psm/contracts.py`:
Exposes plural, read-only getters for other Fusion modules:
```python
def get_indents(indent_ids: Sequence[int]) -> list[dict]:
    """Plural batch fetch for indents by ID."""
    ...

def get_stock_levels(item_codes: Sequence[str]) -> list[dict]:
    """Plural inventory availability query."""
    ...

def get_vendor_statuses(vendor_ids: Sequence[int]) -> list[dict]:
    """Plural vendor vetting status verification."""
    ...
```

---

## 8. Step 3.7 — Scheduled Work (Celery Beat)

* `psm.check_pending_approval_sla`: Runs daily at 08:00 UTC. Flags indents sitting unreviewed beyond configured SLA (default 5 days) and notifies the next escalation authority.
* `psm.sync_low_stock_alerts`: Runs every 6 hours. Generates replenishment warnings when on-hand quantity falls below `minimum_stock_level`.

---

## 9. Step 3.8 — Open Questions & Architectural Clarifications

1. **Threshold Clarification:** The standard procurement threshold defaults to:
   * Direct procurement limit: $\le$ ₹25,000.
   * Quotation / Committee procurement: ₹25,001 to ₹2,50,000.
   * High-value tender & Director sanction: $>$ ₹2,50,000.
2. **Payment Integration:** When a discrepancy report is opened, invoice payment is placed on `PAYMENT_HOLD` locally, which fulfills the 3-way match validation gate.

---

### Phase 2 Signoff Record
* **Builder:** `J Yasaswin (24BCS096)`
* **Auditor/Reviewer:** `MV Siva Poojith (24BCS157)`
* **Approval Decision:** **APPROVED IN WRITING** by Student 2 (`MV Siva Poojith`) on 22 November 2026.
