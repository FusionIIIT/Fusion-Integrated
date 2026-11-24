# PSM State Machines

Every lifecycle transition is declared in `modules/psm/domain/state_machine.py` and resolved through `sm.resolve(entity, from_state, to_state, actor_lane)`. No view or service mutates a managed `status` field directly.

## Indent Lifecycle

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> submitted : employee
    draft --> withdrawn : employee
    submitted --> stock_reserved : dept_admin / ps_admin
    submitted --> external_required : dept_admin / ps_admin
    submitted --> withdrawn : employee
    stock_reserved --> internal_approved : dept_admin
    stock_reserved --> rejected : dept_admin
    internal_approved --> dispatched : dept_admin / ps_admin
    dispatched --> grn_recorded : employee / dept_admin / ps_admin
    grn_recorded --> fulfilled : employee
    external_required --> department_reviewed : dept_admin
    external_required --> rejected : dept_admin
    department_reviewed --> hod_recommended : dept_head
    department_reviewed --> changes_requested : dept_head
    department_reviewed --> rejected : dept_head
    department_reviewed --> procurement_authorized : ps_admin (high priority direct)
    department_reviewed --> withdrawn : employee
    changes_requested --> submitted : employee
    changes_requested --> withdrawn : employee
    hod_recommended --> awaiting_final_approval : ps_admin
    hod_recommended --> procurement_authorized : ps_admin
    awaiting_final_approval --> procurement_authorized : final_authority
    awaiting_final_approval --> rejected : final_authority
    procurement_authorized --> tender_awarded : ps_admin
    procurement_authorized --> po_issued : ps_admin
    tender_awarded --> po_issued : ps_admin
    po_issued --> fulfilled : employee
```

## PurchaseOrder, Tender, Transfer, Discrepancy, and Invoice Lifecycles

| Entity | Declarative States | Legal Transitions | Terminal States |
| --- | --- | --- | --- |
| `PurchaseOrder` | `issued`, `in_transit`, `partially_delivered`, `delivered`, `closed`, `cancelled` | `issued -> in_transit / partially_delivered / delivered / cancelled`; `in_transit -> partially_delivered / delivered / cancelled`; `partially_delivered -> partially_delivered / delivered`; `delivered -> closed` | `closed`, `cancelled` |
| `Tender` | `draft`, `published`, `evaluated`, `awarded`, `cancelled` | `draft -> published / cancelled`; `published -> evaluated / cancelled`; `evaluated -> awarded` | `awarded`, `cancelled` |
| `StockTransfer` | `requested`, `dispatched`, `completed`, `cancelled` | `requested -> dispatched / cancelled`; `dispatched -> completed` | `completed`, `cancelled` |
| `DiscrepancyCase` | `open`, `replacement_awaited`, `resolved`, `closed` | `open -> replacement_awaited / resolved`; `replacement_awaited -> resolved`; `resolved -> closed` | `closed` |
| `Invoice` | `submitted`, `verified`, `on_hold`, `partially_paid`, `paid` | `submitted -> verified / on_hold`; `on_hold -> verified`; `verified -> on_hold / partially_paid / paid`; `partially_paid -> partially_paid / paid` | `paid` |
| `InternalIssue` | `approved`, `picking_scheduled`, `dispatched`, `grn_recorded`, `completed` | `approved -> picking_scheduled / dispatched`; `picking_scheduled -> dispatched`; `dispatched -> grn_recorded`; `grn_recorded -> completed` | `completed` |
| `GoodsReceiptNote` | `accepted`, `partial`, `rejected`, `confirmed` | `accepted / partial -> confirmed` | `confirmed`, `rejected` |
