# PSM State Machines

Every lifecycle transition is declared in `modules/psm/domain/state_machine.py` and resolved through `sm.resolve(entity, from_state, to_state, actor_lane)`. No view or service mutates a `status` field directly.

## Indent Lifecycle

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> submitted : employee
    draft --> withdrawn : employee
    submitted --> stock_checked : dept_admin / ps_admin
    submitted --> changes_requested : dept_admin / hod
    submitted --> withdrawn : employee
    stock_checked --> internal_issue_scheduled : dept_admin / ps_admin
    stock_checked --> department_reviewed : dept_admin
    stock_checked --> rejected : dept_admin
    department_reviewed --> hod_recommended : hod
    department_reviewed --> changes_requested : hod
    department_reviewed --> rejected : hod
    department_reviewed --> withdrawn : employee
    changes_requested --> submitted : employee
    changes_requested --> withdrawn : employee
    hod_recommended --> procurement_reviewed : ps_admin
    hod_recommended --> pending_final_approval : ps_admin
    pending_final_approval --> approved : director
    pending_final_approval --> rejected : director
    procurement_reviewed --> approved : ps_admin
    approved --> tender_open : ps_admin
    approved --> po_issued : ps_admin
    tender_open --> po_issued : ps_admin
    internal_issue_scheduled --> fulfilled : employee
    po_issued --> fulfilled : employee
```

## Procurement, Receipt, Finance, and Transfer Lifecycles

| Entity | States | Terminal States |
| --- | --- | --- |
| `InternalIssue` | `scheduled` -> `picking_scheduled` -> `dispatched` -> `completed` | `completed` |
| `StockTransfer` | `requested` -> `dispatched` -> `completed`; `requested` -> `cancelled` | `completed`, `cancelled` |
| `Tender` | `draft` -> `published` -> `evaluated` -> `awarded`; `draft`/`published` -> `cancelled` | `awarded`, `cancelled` |
| `PurchaseOrder` | `issued` -> `in_transit` / `partially_received` -> `received` -> `closed`; `issued` -> `cancelled` | `closed`, `cancelled` |
| `GoodsReceiptNote` | `accepted` / `partial` -> `confirmed`; `rejected` | `confirmed`, `rejected` |
| `DiscrepancyCase` | `open` -> `in_progress` -> `resolved` -> `closed` | `closed` |
| `VendorInvoice` | `submitted` -> `verified` / `on_hold`; `on_hold` -> `verified`; `verified` -> `partially_paid` / `paid`; `partially_paid` -> `paid` | `paid` |
