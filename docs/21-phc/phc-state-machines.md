# PHC state machines

## Reimbursement claim

The transition table lives in `modules/phc/domain/reimbursements.py`. `transition_claim()` is the single transactional write path and locks the claim before it validates the transition.

| Current state | Event | Acting designation | Next state |
|---|---|---|---|
| absent | submit | employee directory member | pending PHC review |
| pending PHC review | review | Compounder | pending accounts verification |
| pending accounts verification | verify | Accounts Admin | pending sanction |
| pending sanction | approve | Registrar | approved for payment |
| pending sanction | reject | Registrar | rejected |
| approved for payment | pay | Accounts Admin | reimbursed |

Rejected and reimbursed are terminal. No amendment, reopen, return, or payment reversal is part of the approved workflow. A claimant can reapply as a new claim.

## Inventory requisition

The table lives in `modules/phc/domain/requisitions.py`; one locked service path performs each transition.

| Current state | Event | Acting designation | Next state |
|---|---|---|---|
| absent | submit lines | Compounder | pending approval |
| pending approval | approve | Registrar | approved |
| pending approval | reject | Registrar | rejected |
| approved | fulfill delivered goods | Compounder | fulfilled |

Rejected and fulfilled are terminal. Lines are immutable after submission. The workflow does not change inventory stock; stock is recorded through the separate append-only movement service.
